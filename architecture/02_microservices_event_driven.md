# Microservices & Event-Driven Architecture on AWS

## Microservices vs Monolith

```
Monolith:                    Microservices:
┌─────────────────┐          ┌──────┐ ┌──────┐ ┌──────┐
│  Single App     │          │ Auth │ │Order │ │Notif │
│  ├── Auth       │    →     │ Svc  │ │ Svc  │ │ Svc  │
│  ├── Orders     │          └──────┘ └──────┘ └──────┘
│  ├── Payments   │              ↕         ↕        ↕
│  └── Notify     │          ┌──────┐ ┌──────┐ ┌──────┐
└─────────────────┘          │ Pay  │ │Inven │ │ User │
                             │ Svc  │ │ Svc  │ │ Svc  │
                             └──────┘ └──────┘ └──────┘
```

### When to Use Microservices

✅ Large teams (Conway's Law — team per service)
✅ Independent scaling requirements
✅ Different technology stacks per service
✅ Frequent independent deployments
✅ Clear domain boundaries

❌ Small teams (operational overhead)
❌ Tightly coupled domains
❌ Early-stage products (premature optimization)

---

## Service Communication Patterns

### Synchronous (REST/gRPC)

```
Client → API Gateway → Service A → Service B → Response
```

Use for: Real-time responses, simple request/response, user-facing APIs.

### Asynchronous (Event-Driven)

```
Service A → SQS/SNS/EventBridge → Service B (processes later)
```

Use for: Decoupling, resilience, high throughput, long-running tasks.

---

## Amazon SQS — Simple Queue Service

SQS is a fully managed message queue for decoupling services.

### Queue Types

| Feature | Standard Queue | FIFO Queue |
|---------|---------------|-----------|
| Throughput | Unlimited | 3,000 msg/sec (batching) |
| Ordering | Best-effort | Strict FIFO |
| Delivery | At-least-once | Exactly-once |
| Deduplication | ❌ | ✅ |
| Use case | High throughput | Order-sensitive |

```bash
# Create standard queue
aws sqs create-queue \
  --queue-name order-processing \
  --attributes '{
    "VisibilityTimeout": "300",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123456789:order-processing-dlq\",\"maxReceiveCount\":\"3\"}"
  }'

# Create FIFO queue
aws sqs create-queue \
  --queue-name orders.fifo \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "true",
    "VisibilityTimeout": "300"
  }'

# Send message
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/order-processing \
  --message-body '{"orderId": "order-123", "userId": "user-456"}' \
  --message-attributes '{"eventType": {"DataType": "String", "StringValue": "OrderCreated"}}'

# Receive and process
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/order-processing \
  --max-number-of-messages 10 \
  --wait-time-seconds 20

# Delete after processing
aws sqs delete-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/order-processing \
  --receipt-handle "receipt-handle-here"
```

### SQS + Lambda Pattern

```python
def handler(event, context):
    """Process SQS messages in batch."""
    failed_message_ids = []
    
    for record in event['Records']:
        message_id = record['messageId']
        body = json.loads(record['body'])
        
        try:
            process_order(body)
        except Exception as e:
            logger.error(f"Failed to process {message_id}: {e}")
            failed_message_ids.append(message_id)
    
    # Report partial failures (only failed messages go back to queue)
    return {
        'batchItemFailures': [
            {'itemIdentifier': msg_id} 
            for msg_id in failed_message_ids
        ]
    }
```

---

## Amazon SNS — Simple Notification Service

SNS is a pub/sub messaging service. One publisher, many subscribers.

```
Publisher → SNS Topic → Fan-out to:
                        ├── SQS Queue (order service)
                        ├── SQS Queue (inventory service)
                        ├── Lambda (notification service)
                        ├── Email
                        └── HTTP endpoint
```

```bash
# Create topic
aws sns create-topic \
  --name order-events \
  --attributes '{
    "FifoTopic": "false",
    "ContentBasedDeduplication": "false"
  }'

# Subscribe SQS to SNS
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123456789:order-processing \
  --attributes '{"FilterPolicy": "{\"eventType\": [\"OrderCreated\", \"OrderUpdated\"]}"}'

# Subscribe Lambda
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789:function:send-notification

# Publish message
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789:order-events \
  --message '{"orderId": "order-123", "status": "CONFIRMED"}' \
  --message-attributes '{"eventType": {"DataType": "String", "StringValue": "OrderCreated"}}'
```

### SNS Message Filtering

```json
// Subscription filter policy — only receive relevant events
{
  "eventType": ["OrderCreated", "OrderShipped"],
  "amount": [{"numeric": [">=", 100]}],
  "region": ["us-east-1", "eu-west-1"]
}
```

---

## Amazon EventBridge

EventBridge is a serverless event bus. More powerful than SNS — supports event routing, transformation, and scheduling.

```
Event Sources:
├── AWS Services (EC2 state change, S3 upload, CodePipeline)
├── Custom Applications
├── SaaS Partners (Datadog, Zendesk, Stripe)
└── Scheduled events (cron)

EventBridge Bus → Rules → Targets:
                          ├── Lambda
                          ├── SQS
                          ├── SNS
                          ├── ECS Task
                          ├── Step Functions
                          ├── API Gateway
                          └── Another EventBridge bus
```

```bash
# Create custom event bus
aws events create-event-bus --name order-events

# Create rule
aws events put-rule \
  --name process-high-value-orders \
  --event-bus-name order-events \
  --event-pattern '{
    "source": ["com.myapp.orders"],
    "detail-type": ["OrderCreated"],
    "detail": {
      "amount": [{"numeric": [">=", 1000]}],
      "status": ["CONFIRMED"]
    }
  }' \
  --state ENABLED

# Add Lambda target
aws events put-targets \
  --rule process-high-value-orders \
  --event-bus-name order-events \
  --targets '[{
    "Id": "ProcessHighValueOrder",
    "Arn": "arn:aws:lambda:us-east-1:123456789:function:process-vip-order",
    "InputTransformer": {
      "InputPathsMap": {
        "orderId": "$.detail.orderId",
        "amount": "$.detail.amount"
      },
      "InputTemplate": "{\"orderId\": \"<orderId>\", \"amount\": <amount>, \"priority\": \"HIGH\"}"
    }
  }]'

# Publish event
aws events put-events \
  --entries '[{
    "Source": "com.myapp.orders",
    "DetailType": "OrderCreated",
    "Detail": "{\"orderId\": \"order-123\", \"amount\": 1500, \"status\": \"CONFIRMED\"}",
    "EventBusName": "order-events"
  }]'

# Scheduled rule (cron)
aws events put-rule \
  --name daily-report \
  --schedule-expression "cron(0 8 * * ? *)" \
  --state ENABLED
```

---

## AWS Step Functions

Orchestrate multi-step workflows with state machines.

```json
{
  "Comment": "Order processing workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:validate-order",
      "Next": "CheckInventory",
      "Catch": [{
        "ErrorEquals": ["ValidationError"],
        "Next": "OrderFailed"
      }],
      "Retry": [{
        "ErrorEquals": ["Lambda.ServiceException"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2
      }]
    },
    "CheckInventory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:check-inventory",
      "Next": "ProcessPayment"
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:process-payment",
      "Next": "ParallelFulfillment"
    },
    "ParallelFulfillment": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "UpdateInventory",
          "States": {
            "UpdateInventory": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789:function:update-inventory",
              "End": true
            }
          }
        },
        {
          "StartAt": "SendConfirmation",
          "States": {
            "SendConfirmation": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789:function:send-email",
              "End": true
            }
          }
        }
      ],
      "Next": "OrderComplete"
    },
    "OrderComplete": {
      "Type": "Succeed"
    },
    "OrderFailed": {
      "Type": "Fail",
      "Error": "OrderProcessingFailed",
      "Cause": "Order validation or processing failed"
    }
  }
}
```

---

## API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name my-api \
  --description "My application API" \
  --endpoint-configuration types=REGIONAL

# Create HTTP API (simpler, cheaper, faster)
aws apigatewayv2 create-api \
  --name my-http-api \
  --protocol-type HTTP \
  --cors-configuration \
    AllowOrigins='["https://myapp.com"]',\
    AllowMethods='["GET","POST","PUT","DELETE"]',\
    AllowHeaders='["Content-Type","Authorization"]'

# Create Lambda integration
aws apigatewayv2 create-integration \
  --api-id abc123 \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:123456789:function:my-function \
  --payload-format-version 2.0

# Add route
aws apigatewayv2 create-route \
  --api-id abc123 \
  --route-key "POST /orders" \
  --target integrations/integration-id

# Deploy
aws apigatewayv2 create-stage \
  --api-id abc123 \
  --stage-name production \
  --auto-deploy
```

---

## SQS vs SNS vs EventBridge

| Feature | SQS | SNS | EventBridge |
|---------|-----|-----|-------------|
| Pattern | Queue (pull) | Pub/Sub (push) | Event bus (push) |
| Consumers | One consumer per message | Multiple subscribers | Multiple targets |
| Filtering | ❌ | Basic | Advanced (content-based) |
| Scheduling | ❌ | ❌ | ✅ Cron |
| SaaS integration | ❌ | ❌ | ✅ |
| Retention | Up to 14 days | No retention | No retention |
| Use case | Work queues, decoupling | Fan-out notifications | Event routing, automation |

---

## Interview Q&A

### Q1: What is the difference between SQS and SNS?
**SQS**: Queue — messages are stored until a consumer pulls and processes them. One consumer per message (unless multiple queues). Good for work queues, decoupling, load leveling.
**SNS**: Pub/Sub — messages are pushed to all subscribers immediately. Multiple subscribers receive the same message. Good for fan-out, notifications, broadcasting events.
**Common pattern**: SNS → multiple SQS queues (fan-out to multiple consumers, each with their own queue).

### Q2: What is the difference between SNS and EventBridge?
Both are pub/sub, but EventBridge is more powerful: (1) Content-based filtering with complex rules, (2) SaaS partner integrations (Stripe, Datadog), (3) Event transformation before delivery, (4) Scheduled events (cron), (5) Event replay, (6) Schema registry. Use SNS for simple fan-out. Use EventBridge for complex event routing, automation, and SaaS integrations.

### Q3: What is the visibility timeout in SQS?
When a consumer receives a message, it becomes invisible to other consumers for the visibility timeout period. This prevents duplicate processing. If the consumer processes and deletes the message before timeout — success. If it fails and doesn't delete — message becomes visible again after timeout for another consumer to retry. Set visibility timeout to slightly longer than your processing time.

### Q4: How do you handle duplicate messages in SQS?
Standard queues deliver at-least-once — duplicates are possible. Handle with: (1) Idempotent processing — same message processed twice has same result, (2) Deduplication key in DynamoDB — check before processing, (3) FIFO queues — exactly-once delivery with deduplication ID, (4) Conditional writes in DynamoDB — only process if not already processed.

### Q5: When would you use Step Functions over Lambda chaining?
**Step Functions**: Long-running workflows (up to 1 year), complex branching/parallel logic, need visual workflow monitoring, error handling and retry logic, human approval steps, need audit trail of each step.
**Lambda chaining**: Simple sequential calls, low latency requirements, cost-sensitive (Step Functions charges per state transition). Step Functions is better for anything beyond simple sequential calls — it handles errors, retries, and state management that would be complex to implement in Lambda.
