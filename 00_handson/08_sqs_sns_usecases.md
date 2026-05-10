# SQS & SNS — Real-World Use Cases

## Use Case 1: Order Processing Pipeline (SQS)

**Business Problem**: E-commerce checkout must respond in < 200ms, but order processing (inventory, payment, email) takes 5 seconds. Decouple them.

```
Checkout API → SQS → Order Processor Lambda → DynamoDB + Email
     ↓                                              ↓ (on failure)
  200ms response                              Dead Letter Queue
```

```bash
# 1. Create DLQ first
DLQ_URL=$(aws sqs create-queue \
  --queue-name "orders-dlq" \
  --attributes '{
    "MessageRetentionPeriod": "1209600",
    "ReceiveMessageWaitTimeSeconds": "20"
  }' \
  --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

# 2. Create main queue with DLQ and long polling
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "orders" \
  --attributes "{
    \"VisibilityTimeout\": \"300\",
    \"MessageRetentionPeriod\": \"86400\",
    \"ReceiveMessageWaitTimeSeconds\": \"20\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"${DLQ_ARN}\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --query 'QueueUrl' --output text)

# 3. Checkout API sends to queue (fast, non-blocking)
aws sqs send-message \
  --queue-url $QUEUE_URL \
  --message-body '{
    "orderId": "ord-123",
    "userId": "usr-456",
    "items": [{"productId": "p1", "qty": 2, "price": 29.99}],
    "total": 59.98
  }' \
  --message-attributes '{
    "eventType": {"DataType": "String", "StringValue": "OrderCreated"},
    "priority":  {"DataType": "String", "StringValue": "normal"}
  }'

# 4. Monitor queue depth (alert if > 1000 messages)
aws cloudwatch put-metric-alarm \
  --alarm-name "orders-queue-depth" \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --dimensions Name=QueueName,Value=orders \
  --statistic Average \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:ops-alerts

# 5. Check DLQ for failed orders
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages

# Inspect failed message
aws sqs receive-message \
  --queue-url $DLQ_URL \
  --attribute-names All \
  --message-attribute-names All
```

**What you learn**: DLQ pattern, visibility timeout, long polling, queue depth monitoring.

---

## Use Case 2: Fan-Out with SNS → Multiple SQS Queues

**Business Problem**: When a new user registers, you need to: send a welcome email, create a Stripe customer, add to analytics, and send to CRM — all independently.

```
User Registration API
        ↓
   SNS Topic: "user-registered"
        ↓ fan-out
   ┌────┴────┬────────┬──────────┐
   ▼         ▼        ▼          ▼
Email SQS  Stripe SQS  Analytics SQS  CRM SQS
   ↓         ↓        ↓          ↓
Email     Stripe   Analytics    CRM
Lambda    Lambda   Lambda       Lambda
```

```bash
# 1. Create SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name "user-registered" \
  --query 'TopicArn' --output text)

# 2. Create SQS queues for each consumer
for SERVICE in email stripe analytics crm; do
  QUEUE_URL=$(aws sqs create-queue \
    --queue-name "user-registered-${SERVICE}" \
    --query 'QueueUrl' --output text)

  QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

  # Allow SNS to send to this queue
  aws sqs set-queue-attributes \
    --queue-url $QUEUE_URL \
    --attributes "{
      \"Policy\": \"{\\\"Version\\\":\\\"2012-10-17\\\",\\\"Statement\\\":[{\\\"Effect\\\":\\\"Allow\\\",\\\"Principal\\\":{\\\"Service\\\":\\\"sns.amazonaws.com\\\"},\\\"Action\\\":\\\"sqs:SendMessage\\\",\\\"Resource\\\":\\\"${QUEUE_ARN}\\\",\\\"Condition\\\":{\\\"ArnEquals\\\":{\\\"aws:SourceArn\\\":\\\"${TOPIC_ARN}\\\"}}}]}\"
    }"

  # Subscribe queue to SNS topic
  aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_ARN

  echo "Created and subscribed: user-registered-${SERVICE}"
done

# 3. Add filter policy (CRM only gets premium users)
CRM_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn $TOPIC_ARN \
  --query "Subscriptions[?contains(Endpoint,'crm')].SubscriptionArn" \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $CRM_SUB_ARN \
  --attribute-name FilterPolicy \
  --attribute-value '{"userTier": ["premium", "enterprise"]}'

# 4. Publish user registration event
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --message '{
    "userId": "usr-789",
    "email": "alice@example.com",
    "name": "Alice",
    "userTier": "premium",
    "registeredAt": "2024-01-15T10:30:00Z"
  }' \
  --message-attributes '{
    "userTier": {"DataType": "String", "StringValue": "premium"},
    "country":  {"DataType": "String", "StringValue": "US"}
  }'
# Result: all 4 queues receive the message (CRM only for premium)
```

**What you learn**: SNS fan-out, SQS subscription, filter policies, message attributes.

---

## Use Case 3: FIFO Queue for Financial Transactions

**Business Problem**: Bank transfers must be processed in exact order. Duplicate messages must be rejected.

```bash
# 1. Create FIFO queue (exactly-once, ordered)
FIFO_URL=$(aws sqs create-queue \
  --queue-name "bank-transfers.fifo" \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "false",
    "VisibilityTimeout": "60",
    "MessageRetentionPeriod": "86400"
  }' \
  --query 'QueueUrl' --output text)

# 2. Send transfer (with deduplication ID to prevent duplicates)
TRANSFER_ID="txn-$(uuidgen)"
aws sqs send-message \
  --queue-url $FIFO_URL \
  --message-body '{
    "transferId": "'$TRANSFER_ID'",
    "fromAccount": "ACC-001",
    "toAccount": "ACC-002",
    "amount": 500.00,
    "currency": "USD"
  }' \
  --message-group-id "ACC-001" \
  --message-deduplication-id $TRANSFER_ID

# Sending same message again within 5 minutes → silently ignored (dedup)
aws sqs send-message \
  --queue-url $FIFO_URL \
  --message-body '{"transferId": "'$TRANSFER_ID'", ...}' \
  --message-group-id "ACC-001" \
  --message-deduplication-id $TRANSFER_ID  # Same ID = duplicate, ignored

# 3. Process in order (Python consumer)
import boto3
import json

sqs = boto3.client('sqs')

def process_transfers():
    while True:
        response = sqs.receive_message(
            QueueUrl=FIFO_URL,
            MaxNumberOfMessages=1,  # FIFO: process one at a time per group
            WaitTimeSeconds=20
        )
        messages = response.get('Messages', [])
        if not messages:
            break

        msg = messages[0]
        transfer = json.loads(msg['Body'])

        try:
            execute_transfer(transfer)
            sqs.delete_message(
                QueueUrl=FIFO_URL,
                ReceiptHandle=msg['ReceiptHandle']
            )
            print(f"Processed: {transfer['transferId']}")
        except Exception as e:
            print(f"Failed: {e}")
            # Don't delete — will retry after visibility timeout
```

**What you learn**: FIFO queues, message groups for ordering, deduplication IDs, exactly-once processing.

---

## Use Case 4: Dead Letter Queue Investigation

**Business Problem**: 50 orders failed processing. Investigate why without losing the messages.

```bash
# 1. Check DLQ message count
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages,CreatedTimestamp

# 2. Peek at failed messages (without deleting)
aws sqs receive-message \
  --queue-url $DLQ_URL \
  --max-number-of-messages 10 \
  --visibility-timeout 30 \
  --attribute-names All \
  --message-attribute-names All \
  --query 'Messages[*].{Body:Body,Attributes:Attributes}'

# 3. Redrive DLQ messages back to main queue (after fixing the bug)
# First, set up redrive allow policy on main queue
aws sqs set-queue-attributes \
  --queue-url $QUEUE_URL \
  --attributes "{
    \"RedriveAllowPolicy\": \"{\\\"redrivePermission\\\":\\\"byQueue\\\",\\\"sourceQueueArns\\\":[\\\"${DLQ_ARN}\\\"]}\"
  }"

# Start redrive (moves messages from DLQ back to main queue)
aws sqs start-message-move-task \
  --source-arn $DLQ_ARN \
  --destination-arn $(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text) \
  --max-number-of-messages-per-second 10

# Monitor redrive progress
aws sqs list-message-move-tasks --source-arn $DLQ_ARN
```

**What you learn**: DLQ investigation, message redrive, visibility timeout for safe peeking.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No DLQ configured | Failed messages lost forever | Always configure DLQ |
| Short visibility timeout | Message processed twice | Set timeout > max processing time |
| Not using long polling | Wasted API calls + cost | Set `WaitTimeSeconds=20` |
| Deleting message before processing | Data loss on failure | Delete only after successful processing |
| Using standard queue for ordered processing | Out-of-order messages | Use FIFO queue |
| Not monitoring queue depth | Silent backlog buildup | Alert on `ApproximateNumberOfMessages` |
