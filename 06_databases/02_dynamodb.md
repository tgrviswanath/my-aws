# DynamoDB — NoSQL Deep Dive

## What is DynamoDB?
DynamoDB is a fully managed, serverless NoSQL key-value and document database. Single-digit millisecond performance at any scale.

---

## Core Concepts

```
Table
├── Items (rows) — up to 400KB each
│   ├── Partition Key (required) — determines partition
│   ├── Sort Key (optional) — enables range queries
│   └── Attributes (any additional fields)
└── Indexes
    ├── Local Secondary Index (LSI) — same partition key, different sort key
    └── Global Secondary Index (GSI) — different partition + sort key
```

### Key Design

```
Simple Primary Key:    Partition Key only
Composite Primary Key: Partition Key + Sort Key

Example — E-commerce:
Table: Orders
  PK: customerId
  SK: orderId#timestamp

Allows queries like:
  - Get all orders for customer
  - Get orders in date range for customer
  - Get specific order
```

---

## Capacity Modes

| Mode | Pricing | Use Case |
|------|---------|---------|
| On-Demand | Per request ($1.25/M writes, $0.25/M reads) | Unpredictable traffic |
| Provisioned | Per RCU/WCU/hour | Predictable traffic, cost optimization |
| Provisioned + Auto Scaling | Scales RCU/WCU automatically | Variable but predictable patterns |

```bash
# Create table (On-Demand)
aws dynamodb create-table \
  --table-name Orders \
  --attribute-definitions \
    AttributeName=customerId,AttributeType=S \
    AttributeName=orderId,AttributeType=S \
    AttributeName=status,AttributeType=S \
    AttributeName=createdAt,AttributeType=S \
  --key-schema \
    AttributeName=customerId,KeyType=HASH \
    AttributeName=orderId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[{
    "IndexName": "status-createdAt-index",
    "KeySchema": [
      {"AttributeName": "status", "KeyType": "HASH"},
      {"AttributeName": "createdAt", "KeyType": "RANGE"}
    ],
    "Projection": {"ProjectionType": "ALL"}
  }]' \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/aws/dynamodb \
  --tags Key=Environment,Value=production
```

---

## CRUD Operations

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Orders')

# PUT item
table.put_item(
    Item={
        'customerId': 'cust-123',
        'orderId': 'order-456#2024-01-15T10:30:00Z',
        'status': 'PENDING',
        'total': Decimal('99.99'),
        'items': [
            {'productId': 'prod-789', 'quantity': 2, 'price': Decimal('49.99')}
        ],
        'createdAt': '2024-01-15T10:30:00Z'
    },
    ConditionExpression='attribute_not_exists(customerId)'  # Prevent overwrite
)

# GET item
response = table.get_item(
    Key={
        'customerId': 'cust-123',
        'orderId': 'order-456#2024-01-15T10:30:00Z'
    },
    ConsistentRead=True  # Strong consistency
)
item = response.get('Item')

# QUERY (efficient — uses index)
response = table.query(
    KeyConditionExpression=Key('customerId').eq('cust-123') & 
                           Key('orderId').begins_with('order-'),
    FilterExpression=Attr('status').eq('PENDING'),
    ScanIndexForward=False,  # Descending order
    Limit=20
)

# QUERY GSI
response = table.query(
    IndexName='status-createdAt-index',
    KeyConditionExpression=Key('status').eq('PENDING') & 
                           Key('createdAt').between('2024-01-01', '2024-01-31')
)

# UPDATE item (atomic)
table.update_item(
    Key={'customerId': 'cust-123', 'orderId': 'order-456#2024-01-15T10:30:00Z'},
    UpdateExpression='SET #s = :new_status, updatedAt = :ts ADD version :inc',
    ExpressionAttributeNames={'#s': 'status'},
    ExpressionAttributeValues={
        ':new_status': 'SHIPPED',
        ':ts': '2024-01-16T08:00:00Z',
        ':inc': 1,
        ':expected': 'PENDING'
    },
    ConditionExpression='#s = :expected'  # Optimistic locking
)

# DELETE item
table.delete_item(
    Key={'customerId': 'cust-123', 'orderId': 'order-456#2024-01-15T10:30:00Z'},
    ConditionExpression='attribute_exists(customerId)'
)
```

---

## Batch Operations

```python
# Batch write (up to 25 items)
with table.batch_writer() as batch:
    for i in range(100):
        batch.put_item(Item={
            'customerId': f'cust-{i}',
            'orderId': f'order-{i}',
            'status': 'PENDING'
        })

# Batch get (up to 100 items)
response = dynamodb.batch_get_item(
    RequestItems={
        'Orders': {
            'Keys': [
                {'customerId': {'S': 'cust-1'}, 'orderId': {'S': 'order-1'}},
                {'customerId': {'S': 'cust-2'}, 'orderId': {'S': 'order-2'}}
            ],
            'ConsistentRead': True
        }
    }
)

# Transactions (up to 100 items, ACID)
dynamodb.transact_write_items(
    TransactItems=[
        {
            'Update': {
                'TableName': 'Inventory',
                'Key': {'productId': {'S': 'prod-789'}},
                'UpdateExpression': 'ADD quantity :dec',
                'ExpressionAttributeValues': {':dec': {'N': '-2'}, ':min': {'N': '0'}},
                'ConditionExpression': 'quantity >= :min'
            }
        },
        {
            'Put': {
                'TableName': 'Orders',
                'Item': {
                    'customerId': {'S': 'cust-123'},
                    'orderId': {'S': 'order-new'},
                    'status': {'S': 'CONFIRMED'}
                }
            }
        }
    ]
)
```

---

## DynamoDB Streams + Lambda

```python
# Lambda handler for DynamoDB Streams
def handler(event, context):
    for record in event['Records']:
        event_name = record['eventName']  # INSERT, MODIFY, REMOVE
        
        if event_name == 'INSERT':
            new_item = record['dynamodb']['NewImage']
            # Process new order
            
        elif event_name == 'MODIFY':
            old_item = record['dynamodb']['OldImage']
            new_item = record['dynamodb']['NewImage']
            # React to status change
            
        elif event_name == 'REMOVE':
            old_item = record['dynamodb']['OldImage']
            # Handle deletion
```

---

## DynamoDB Accelerator (DAX)

In-memory cache for DynamoDB. Microsecond read latency.

```bash
# Create DAX cluster
aws dax create-cluster \
  --cluster-name prod-dax \
  --node-type dax.r5.large \
  --replication-factor 3 \
  --iam-role-arn arn:aws:iam::123456789:role/dax-role \
  --subnet-group-name prod-dax-subnet-group \
  --security-group-ids sg-dax-12345678
```

```python
# Use DAX client (drop-in replacement)
import amazon.dax.client as dax

dax_client = dax.AmazonDaxClient(
    endpoints=['prod-dax.abc123.dax-clusters.us-east-1.amazonaws.com:8111']
)
table = dax_client.Table('Orders')
# Same API as regular DynamoDB
```

**When to use DAX**: Read-heavy workloads, same data read repeatedly, need microsecond latency. Not for: write-heavy, strongly consistent reads, rarely accessed data.

---

## Global Tables

Multi-region, multi-active replication.

```bash
# Create global table (table must exist in each region)
aws dynamodb create-global-table \
  --global-table-name Orders \
  --replication-group RegionName=us-east-1 RegionName=eu-west-1 RegionName=ap-southeast-1
```

**Conflict resolution**: Last writer wins (based on timestamp). Design to avoid conflicts.

---

## TTL (Time to Live)

Automatically delete expired items.

```bash
# Enable TTL
aws dynamodb update-time-to-live \
  --table-name Sessions \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt
```

```python
import time
# Set TTL when writing
table.put_item(Item={
    'sessionId': 'sess-abc',
    'userId': 'user-123',
    'data': '...',
    'expiresAt': int(time.time()) + 3600  # Expire in 1 hour
})
```

---

## Data Modeling Patterns

### Single Table Design

```
Entity     | PK              | SK
-----------|-----------------|------------------
Customer   | CUST#cust-123   | PROFILE
Order      | CUST#cust-123   | ORDER#order-456
OrderItem  | ORDER#order-456 | ITEM#prod-789
Product    | PROD#prod-789   | METADATA

Access patterns:
- Get customer profile: PK=CUST#cust-123, SK=PROFILE
- Get all orders for customer: PK=CUST#cust-123, SK begins_with ORDER#
- Get order items: PK=ORDER#order-456, SK begins_with ITEM#
```

---

## Interview Q&A

### Q1: When would you choose DynamoDB over RDS?
**DynamoDB**: Massive scale (millions of requests/sec), single-digit ms latency, serverless/no ops, flexible schema, key-value/document access patterns, global distribution needed.
**RDS**: Complex queries with JOINs, ACID transactions across many tables, existing SQL expertise, reporting/analytics, complex relationships between entities.

### Q2: What is the difference between a GSI and LSI?
**LSI (Local Secondary Index)**: Same partition key as table, different sort key. Must be created at table creation. Shares throughput with table. Strongly consistent reads possible. Max 5 per table.
**GSI (Global Secondary Index)**: Different partition key (and optional sort key). Can be added/removed anytime. Has its own throughput. Eventually consistent only. Max 20 per table. More flexible — use GSI for most cases.

### Q3: What is a hot partition and how do you avoid it?
Hot partition = one partition key receiving disproportionate traffic, causing throttling. Avoid by: (1) Choosing high-cardinality partition keys (userId, orderId, not status/country), (2) Adding random suffix to distribute writes (write sharding), (3) Using DAX for read-heavy hot keys, (4) Caching popular items, (5) Using On-Demand mode which handles spikes automatically.

### Q4: What is DynamoDB's consistency model?
**Eventually consistent reads** (default): May return stale data (milliseconds behind). Half the cost of strongly consistent.
**Strongly consistent reads**: Always returns latest data. Costs 2x RCUs. Not available on GSIs.
**Transactions**: ACID across multiple items/tables. Costs 2x the normal read/write cost.

### Q5: How do DynamoDB Streams work?
Streams capture a time-ordered sequence of item-level changes (INSERT, MODIFY, REMOVE) for up to 24 hours. Each stream record contains the changed item data (configurable: keys only, new image, old image, or both). Use with Lambda for: event-driven processing, cross-region replication, audit logging, search indexing (sync to Elasticsearch).
