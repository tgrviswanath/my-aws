# Lab 04 — DynamoDB: Create, Query & Optimize

## Objective
Create a DynamoDB table, design a data model with GSIs, perform CRUD operations using the Python SDK, and explore query patterns.

## Prerequisites
- AWS CLI configured
- Python 3.8+ with boto3: `pip install boto3`
- Estimated time: 45 minutes
- Estimated cost: ~$0.00 (DynamoDB free tier: 25GB + 25 WCU/RCU)

---

## Step 1: Create Table

```bash
RG_REGION="us-east-1"
TABLE_NAME="lab04-orders"

# Create table with composite key + GSI
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions \
    AttributeName=customerId,AttributeType=S \
    AttributeName=orderId,AttributeType=S \
    AttributeName=status,AttributeType=S \
    AttributeName=createdAt,AttributeType=S \
  --key-schema \
    AttributeName=customerId,KeyType=HASH \
    AttributeName=orderId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[
    {
      "IndexName": "status-createdAt-index",
      "KeySchema": [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "createdAt", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --sse-specification Enabled=true,SSEType=AES256 \
  --tags Key=Lab,Value=04 Key=Purpose,Value=Learning \
  --region $RG_REGION

# Wait for table to be active
aws dynamodb wait table-exists --table-name $TABLE_NAME
echo "Table created: $TABLE_NAME"

# Describe table
aws dynamodb describe-table \
  --table-name $TABLE_NAME \
  --query 'Table.{Status:TableStatus,Items:ItemCount,Size:TableSizeBytes}'
```

---

## Step 2: Python SDK — CRUD Operations

```python
# dynamodb_lab.py
import boto3
import json
import time
import uuid
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('lab04-orders')

# ── CREATE ────────────────────────────────────────────────────────────────────
def create_order(customer_id: str, items: list) -> dict:
    order_id = str(uuid.uuid4())
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    total = sum(Decimal(str(i['price'])) * i['quantity'] for i in items)

    order = {
        'customerId': customer_id,
        'orderId': order_id,
        'items': items,
        'total': total,
        'status': 'PENDING',
        'createdAt': now,
        'updatedAt': now,
        'version': 1
    }

    # Conditional write — prevent duplicate
    table.put_item(
        Item=order,
        ConditionExpression='attribute_not_exists(orderId)'
    )
    print(f"✅ Created order: {order_id}")
    return order

# ── READ (Point Read — most efficient, 1 RCU) ─────────────────────────────────
def get_order(order_id: str, customer_id: str) -> dict | None:
    response = table.get_item(
        Key={'customerId': customer_id, 'orderId': order_id},
        ConsistentRead=True
    )
    item = response.get('Item')
    if item:
        print(f"✅ Got order: {item['orderId']} (status: {item['status']})")
    return item

# ── QUERY (within partition — efficient) ──────────────────────────────────────
def get_customer_orders(customer_id: str, status: str = None) -> list:
    kwargs = {
        'KeyConditionExpression': Key('customerId').eq(customer_id),
        'ScanIndexForward': False,  # Newest first
        'Limit': 20
    }
    if status:
        kwargs['FilterExpression'] = Attr('status').eq(status)

    response = table.query(**kwargs)
    items = response['Items']
    print(f"✅ Found {len(items)} orders for {customer_id}")
    return items

# ── QUERY GSI (cross-partition) ───────────────────────────────────────────────
def get_orders_by_status(status: str, date_from: str = None) -> list:
    kwargs = {
        'IndexName': 'status-createdAt-index',
        'KeyConditionExpression': Key('status').eq(status)
    }
    if date_from:
        kwargs['KeyConditionExpression'] &= Key('createdAt').gte(date_from)

    response = table.query(**kwargs)
    print(f"✅ Found {len(response['Items'])} {status} orders")
    return response['Items']

# ── UPDATE (Patch — atomic, efficient) ────────────────────────────────────────
def update_order_status(order_id: str, customer_id: str,
                        new_status: str, expected_version: int) -> dict:
    try:
        response = table.update_item(
            Key={'customerId': customer_id, 'orderId': order_id},
            UpdateExpression='SET #s = :status, updatedAt = :ts, version = :new_ver',
            ConditionExpression='version = :expected_ver',  # Optimistic locking
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': new_status,
                ':ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                ':new_ver': expected_version + 1,
                ':expected_ver': expected_version
            },
            ReturnValues='ALL_NEW'
        )
        print(f"✅ Updated order {order_id} → {new_status}")
        return response['Attributes']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print(f"❌ Optimistic lock failed — order was modified by another process")
            raise
        raise

# ── DELETE ────────────────────────────────────────────────────────────────────
def delete_order(order_id: str, customer_id: str):
    table.delete_item(
        Key={'customerId': customer_id, 'orderId': order_id},
        ConditionExpression='attribute_exists(orderId)'
    )
    print(f"✅ Deleted order: {order_id}")

# ── BATCH WRITE ───────────────────────────────────────────────────────────────
def batch_create_orders(orders: list):
    with table.batch_writer() as batch:
        for order in orders:
            batch.put_item(Item=order)
    print(f"✅ Batch wrote {len(orders)} orders")

# ── TRANSACTIONS (ACID across items) ─────────────────────────────────────────
def confirm_order_with_inventory(order_id: str, customer_id: str,
                                  product_id: str, quantity: int):
    """Atomically confirm order AND decrement inventory"""
    dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')

    try:
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    'Update': {
                        'TableName': 'lab04-orders',
                        'Key': {
                            'customerId': {'S': customer_id},
                            'orderId': {'S': order_id}
                        },
                        'UpdateExpression': 'SET #s = :confirmed',
                        'ConditionExpression': '#s = :pending',
                        'ExpressionAttributeNames': {'#s': 'status'},
                        'ExpressionAttributeValues': {
                            ':confirmed': {'S': 'CONFIRMED'},
                            ':pending': {'S': 'PENDING'}
                        }
                    }
                },
                {
                    'Update': {
                        'TableName': 'lab04-inventory',
                        'Key': {'productId': {'S': product_id}},
                        'UpdateExpression': 'ADD quantity :dec',
                        'ConditionExpression': 'quantity >= :min',
                        'ExpressionAttributeValues': {
                            ':dec': {'N': str(-quantity)},
                            ':min': {'N': str(quantity)}
                        }
                    }
                }
            ]
        )
        print(f"✅ Transaction succeeded: order confirmed + inventory decremented")
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            print(f"❌ Transaction cancelled: {e.response['Error']['Message']}")
        raise

# ── DEMO ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== DynamoDB Lab ===\n")

    # Create orders
    o1 = create_order('cust-001', [
        {'productId': 'prod-1', 'name': 'Laptop', 'price': 999.99, 'quantity': 1}
    ])
    o2 = create_order('cust-001', [
        {'productId': 'prod-2', 'name': 'Mouse', 'price': 29.99, 'quantity': 2}
    ])
    o3 = create_order('cust-002', [
        {'productId': 'prod-1', 'name': 'Laptop', 'price': 999.99, 'quantity': 1}
    ])

    # Point read
    fetched = get_order(o1['orderId'], 'cust-001')

    # Query within partition
    orders = get_customer_orders('cust-001')

    # Update with optimistic locking
    updated = update_order_status(o1['orderId'], 'cust-001', 'SHIPPED', 1)

    # GSI query
    pending = get_orders_by_status('PENDING')

    print("\n=== Lab Complete ===")
```

```bash
# Run the lab
python dynamodb_lab.py
```

---

## Step 3: Explore Capacity and Metrics

```bash
# Check consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=$TABLE_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --region $RG_REGION

# Enable TTL
aws dynamodb update-time-to-live \
  --table-name $TABLE_NAME \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt \
  --region $RG_REGION

echo "TTL enabled on 'expiresAt' attribute"
```

---

## Step 4: Cleanup

```bash
aws dynamodb delete-table --table-name $TABLE_NAME --region $RG_REGION
echo "Table deleted"
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| ProvisionedThroughputExceededException | RCU/WCU exceeded | Switch to PAY_PER_REQUEST or increase capacity |
| ConditionalCheckFailedException | Condition not met | Check item exists and version matches |
| ResourceNotFoundException | Table doesn't exist | Verify table name and region |
| ValidationException | Invalid expression | Check attribute names (reserved words need `#`) |
| TransactionCanceledException | One item failed condition | Check all conditions in transaction |

## What You Learned

✅ Create DynamoDB table with GSI and streams
✅ Perform efficient point reads vs partition queries
✅ Use optimistic locking with version numbers
✅ Execute ACID transactions across multiple items
✅ Use batch operations for bulk writes
✅ Enable TTL for automatic item expiration
✅ Monitor consumed capacity with CloudWatch
