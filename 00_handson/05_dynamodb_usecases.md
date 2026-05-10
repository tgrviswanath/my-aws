# DynamoDB — Real-World Use Cases

## Use Case 1: E-Commerce Shopping Cart

**Business Problem**: Store shopping carts for millions of users. Carts must load in < 10ms, survive server restarts, and expire after 7 days of inactivity.

```bash
# 1. Create cart table
aws dynamodb create-table \
  --table-name "shopping-carts" \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=itemId,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=itemId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# 2. Enable TTL (auto-expire carts after 7 days)
aws dynamodb update-time-to-live \
  --table-name "shopping-carts" \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt
```

```python
import boto3
import time
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table('shopping-carts')

def add_to_cart(user_id: str, item_id: str, product: dict, quantity: int):
    """Add or update item in cart."""
    expires_at = int(time.time()) + (7 * 24 * 3600)  # 7 days from now

    table.put_item(Item={
        'userId':    user_id,
        'itemId':    item_id,
        'name':      product['name'],
        'price':     Decimal(str(product['price'])),
        'quantity':  quantity,
        'imageUrl':  product.get('imageUrl', ''),
        'expiresAt': expires_at,  # TTL field
        'addedAt':   int(time.time()),
    })

def get_cart(user_id: str) -> dict:
    """Get all items in user's cart with total."""
    result = table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    items = result['Items']
    total = sum(float(i['price']) * i['quantity'] for i in items)
    return {'items': items, 'total': round(total, 2), 'count': len(items)}

def update_quantity(user_id: str, item_id: str, quantity: int):
    """Update quantity or remove if quantity = 0."""
    if quantity <= 0:
        table.delete_item(Key={'userId': user_id, 'itemId': item_id})
    else:
        table.update_item(
            Key={'userId': user_id, 'itemId': item_id},
            UpdateExpression='SET quantity = :q, expiresAt = :e',
            ExpressionAttributeValues={
                ':q': quantity,
                ':e': int(time.time()) + (7 * 24 * 3600)  # Reset TTL on activity
            }
        )

def checkout(user_id: str) -> list:
    """Get cart items and clear cart atomically."""
    cart = get_cart(user_id)

    # Delete all cart items in batch
    with table.batch_writer() as batch:
        for item in cart['items']:
            batch.delete_item(Key={'userId': user_id, 'itemId': item['itemId']})

    return cart['items']

# Test
add_to_cart('user-123', 'prod-456', {'name': 'Laptop', 'price': 999.99}, 1)
add_to_cart('user-123', 'prod-789', {'name': 'Mouse', 'price': 29.99}, 2)
print(get_cart('user-123'))
```

**What you learn**: Composite key design, TTL for auto-expiry, batch writes, cart checkout pattern.

---

## Use Case 2: Real-Time Leaderboard

**Business Problem**: Gaming app needs a global leaderboard showing top 100 players, updated in real-time.

```python
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table('game-leaderboard')

# Table design:
# PK: gameId (partition key)
# SK: score#userId (sort key — allows range queries by score)
# GSI: userId-index (to look up a specific user's rank)

def update_score(game_id: str, user_id: str, new_score: int, username: str):
    """Update player score. Uses conditional write to only update if score improved."""
    # Pad score for lexicographic sorting (10 digits)
    score_key = f"{new_score:010d}#{user_id}"

    try:
        table.put_item(
            Item={
                'gameId':   game_id,
                'scoreKey': score_key,
                'userId':   user_id,
                'username': username,
                'score':    Decimal(str(new_score)),
                'updatedAt': int(time.time()),
            },
            # Only update if new score is higher than existing
            ConditionExpression='attribute_not_exists(gameId) OR score < :new_score',
            ExpressionAttributeValues={':new_score': Decimal(str(new_score))}
        )
        return True
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return False  # Score not improved

def get_top_players(game_id: str, limit: int = 100) -> list:
    """Get top N players sorted by score descending."""
    result = table.query(
        KeyConditionExpression=Key('gameId').eq(game_id),
        ScanIndexForward=False,  # Descending order
        Limit=limit
    )
    return [
        {
            'rank':     i + 1,
            'username': item['username'],
            'score':    int(item['score']),
        }
        for i, item in enumerate(result['Items'])
    ]

def get_player_rank(game_id: str, user_id: str) -> dict:
    """Get a specific player's rank and score."""
    # Query GSI to find player's current score
    result = table.query(
        IndexName='userId-index',
        KeyConditionExpression=Key('userId').eq(user_id) & Key('gameId').eq(game_id)
    )
    if not result['Items']:
        return {'rank': None, 'score': 0}

    player = result['Items'][0]
    player_score = int(player['score'])

    # Count players with higher score
    higher_count = table.query(
        KeyConditionExpression=Key('gameId').eq(game_id),
        FilterExpression='score > :s',
        ExpressionAttributeValues={':s': Decimal(str(player_score))},
        Select='COUNT'
    )['Count']

    return {'rank': higher_count + 1, 'score': player_score, 'username': player['username']}

# Test
update_score('game-001', 'user-1', 9500, 'Alice')
update_score('game-001', 'user-2', 8200, 'Bob')
update_score('game-001', 'user-3', 9800, 'Charlie')
print(get_top_players('game-001', limit=10))
print(get_player_rank('game-001', 'user-1'))
```

**What you learn**: Sort key design for range queries, conditional writes, GSI for alternate access patterns.

---

## Use Case 3: Session Store

**Business Problem**: Store user sessions for a web app. Sessions must expire automatically, support millions of concurrent users.

```python
import boto3
import json
import uuid
import time
import hashlib

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table('user-sessions')

# Table: PK=sessionId, TTL=expiresAt

def create_session(user_id: str, user_data: dict, ttl_seconds: int = 3600) -> str:
    """Create a new session and return session ID."""
    session_id = str(uuid.uuid4())
    expires_at = int(time.time()) + ttl_seconds

    table.put_item(Item={
        'sessionId': session_id,
        'userId':    user_id,
        'data':      json.dumps(user_data),
        'createdAt': int(time.time()),
        'expiresAt': expires_at,  # TTL
        'ipAddress': user_data.get('ip', ''),
    })
    return session_id

def get_session(session_id: str) -> dict | None:
    """Get session data. Returns None if expired or not found."""
    result = table.get_item(
        Key={'sessionId': session_id},
        ConsistentRead=True  # Always get latest (important for auth)
    )
    item = result.get('Item')
    if not item:
        return None

    # Check if expired (TTL may not have deleted it yet)
    if item['expiresAt'] < int(time.time()):
        delete_session(session_id)
        return None

    return {'userId': item['userId'], 'data': json.loads(item['data'])}

def refresh_session(session_id: str, ttl_seconds: int = 3600):
    """Extend session TTL on activity."""
    table.update_item(
        Key={'sessionId': session_id},
        UpdateExpression='SET expiresAt = :e',
        ExpressionAttributeValues={':e': int(time.time()) + ttl_seconds}
    )

def delete_session(session_id: str):
    """Logout — delete session immediately."""
    table.delete_item(Key={'sessionId': session_id})

def delete_all_user_sessions(user_id: str):
    """Force logout from all devices."""
    # Query GSI on userId
    result = table.query(
        IndexName='userId-index',
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    with table.batch_writer() as batch:
        for item in result['Items']:
            batch.delete_item(Key={'sessionId': item['sessionId']})
```

**What you learn**: TTL for session expiry, consistent reads for auth, batch delete for logout-all.

---

## Use Case 4: DynamoDB Streams → Real-Time Notifications

**Business Problem**: When an order status changes to "SHIPPED", automatically send a push notification to the customer.

```python
# Lambda triggered by DynamoDB Streams
import boto3
import json

sns = boto3.client('sns')

def handler(event, context):
    for record in event['Records']:
        if record['eventName'] not in ('MODIFY', 'INSERT'):
            continue

        new_image = record['dynamodb'].get('NewImage', {})
        old_image = record['dynamodb'].get('OldImage', {})

        new_status = new_image.get('status', {}).get('S')
        old_status = old_image.get('status', {}).get('S')

        # Only act on status change to SHIPPED
        if new_status == 'SHIPPED' and old_status != 'SHIPPED':
            order_id  = new_image['orderId']['S']
            user_id   = new_image['userId']['S']
            tracking  = new_image.get('trackingNumber', {}).get('S', 'N/A')

            # Send push notification via SNS
            sns.publish(
                TopicArn=f"arn:aws:sns:us-east-1:123456789:user-{user_id}-notifications",
                Message=json.dumps({
                    'default': f'Your order {order_id} has shipped! Tracking: {tracking}',
                    'GCM': json.dumps({
                        'notification': {
                            'title': 'Order Shipped! 📦',
                            'body': f'Tracking number: {tracking}'
                        }
                    })
                }),
                MessageStructure='json'
            )
            print(f"Notification sent for order {order_id}")
```

```bash
# Connect Lambda to DynamoDB Stream
STREAM_ARN=$(aws dynamodb describe-table \
  --table-name "orders" \
  --query 'Table.LatestStreamArn' --output text)

aws lambda create-event-source-mapping \
  --function-name "order-notification-sender" \
  --event-source-arn $STREAM_ARN \
  --starting-position LATEST \
  --batch-size 100 \
  --bisect-batch-on-function-error true \
  --destination-config '{
    "OnFailure": {
      "Destination": "arn:aws:sqs:us-east-1:123456789:stream-failures-dlq"
    }
  }'
```

**What you learn**: DynamoDB Streams, change data capture, event-driven notifications, bisect on error.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using Scan instead of Query | Full table scan = expensive + slow | Always Query with partition key |
| Hot partition key (e.g., `status`) | Throttling on one partition | Use high-cardinality keys (userId, orderId) |
| Not enabling TTL | Table grows forever | Enable TTL for session/cache tables |
| Storing large items (> 400KB) | Item too large error | Store large data in S3, reference in DynamoDB |
| Using strongly consistent reads everywhere | 2× cost | Use eventually consistent for non-critical reads |
| No GSI for alternate access patterns | Forced to Scan | Design GSIs upfront for all query patterns |
