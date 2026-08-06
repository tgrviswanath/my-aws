# Project 4.5 — SNS/SQS Async Microservices

**Stage:** 04 | **Level:** Intermediate | **Est. Time:** 2–3 hours | **Cost:** ~$0.60/month

This project implements an asynchronous order processing pipeline using SNS fan-out and SQS queues.
A Producer Lambda receives an order JSON payload via direct invocation or API Gateway and publishes
it to an SNS topic. SNS immediately fans the message out to two SQS queues: `orders-queue` for
transactional processing and `analytics-queue` for reporting and aggregation. A Consumer Lambda
polls `orders-queue` with long polling, processes each order, and writes the result to DynamoDB.
A Dead Letter Queue (`orders-dlq`) captures any message that fails processing three times, enabling
safe retry analysis without blocking the main queue. The design decouples producers from consumers
completely — the Producer Lambda does not know or care how many downstream services exist.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| SNS (Standard Topic) | Fan-out: publishes one message to both SQS queues simultaneously | ~$0.50/1M publishes |
| SQS `orders-queue` | Buffers orders for Consumer Lambda; triggers Lambda via event source mapping | ~$0.40/1M requests |
| SQS `analytics-queue` | Receives order copy for reporting; consumed separately by analytics service | ~$0.40/1M requests |
| SQS `orders-dlq` | Captures messages that exceed `maxReceiveCount` (3) on orders-queue | ~$0.40/1M requests |
| Lambda — Producer | Validates incoming order JSON, publishes to SNS topic | ~$0.20/1M requests |
| Lambda — Consumer | Polls orders-queue, processes order, writes to DynamoDB | ~$0.20/1M requests |
| DynamoDB | Stores processed orders; PK = `order_id` | Free tier / ~$0.25/WCU |
| IAM | Roles for Producer (SNS publish) and Consumer (SQS read, DynamoDB write) | Free |
| CloudWatch Logs | Execution logs for both Lambda functions | ~$0.50/GB ingested |

---

## Input / Output

### Input

| Field | Value | Notes |
|---|---|---|
| Trigger | Direct Lambda invocation or API Gateway POST | Producer Lambda entry point |
| Payload format | JSON | `{"order_id": "ORD-001", "customer_id": "C-42", "items": [...], "total": 59.99}` |
| SNS topic | `arn:aws:sns:us-east-1:123456789012:orders-topic` | Producer publishes here |
| Message attributes | `event_type: order.created` | Used for SNS subscription filter policies |

### Output

| Artifact | Location | Details |
|---|---|---|
| DynamoDB order record | Table `orders`, PK = `order_id` | Status, items, total, processed_at timestamp |
| analytics-queue message | `orders-analytics-queue` | Raw SNS envelope; consumed by analytics Lambda |
| DLQ message | `orders-dlq` | Original message body + failure metadata after 3 retries |
| CloudWatch log | `/aws/lambda/order-consumer` | Per-message processing result and any errors |

---

## Architecture

```
  Client / API Gateway
          |
          | JSON payload
          v
  +------------------+
  | Producer Lambda  |
  | order-producer   |
  +------------------+
          |
          | sns.publish()
          v
  +----------------------+
  |   SNS Standard Topic |
  |   orders-topic       |
  +----------------------+
         /          \
        /  fan-out   \
       v              v
 +---------------+  +---------------------+
 | orders-queue  |  | orders-analytics-   |
 | (SQS Standard)|  | queue (SQS Standard)|
 +---------------+  +---------------------+
        |                    |
        | event source       | polled by
        | mapping (Lambda    | analytics
        | polls with long    | service
        | polling)           | (separate)
        v
 +------------------+        +----------+
 | Consumer Lambda  |------->| DynamoDB |
 | order-consumer   | PUT    | orders   |
 +------------------+        +----------+
        |
        | after 3 failed
        | visibility cycles
        v
 +------------------+
 | orders-dlq       |
 | (Dead Letter Q)  |
 +------------------+
```

---

## Quick Start

```cmd
REM 1. Create the SNS topic
aws sns create-topic --name orders-topic --region us-east-1

REM 2. Create SQS queues (main, analytics, DLQ)
aws sqs create-queue --queue-name orders-dlq --region us-east-1

aws sqs create-queue ^
  --queue-name orders-queue ^
  --attributes VisibilityTimeout=180,RedrivePolicy="{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123456789012:orders-dlq\",\"maxReceiveCount\":\"3\"}" ^
  --region us-east-1

aws sqs create-queue --queue-name orders-analytics-queue --region us-east-1

REM 3. Subscribe both SQS queues to SNS topic
aws sns subscribe ^
  --topic-arn arn:aws:sns:us-east-1:123456789012:orders-topic ^
  --protocol sqs ^
  --notification-endpoint arn:aws:sqs:us-east-1:123456789012:orders-queue

aws sns subscribe ^
  --topic-arn arn:aws:sns:us-east-1:123456789012:orders-topic ^
  --protocol sqs ^
  --notification-endpoint arn:aws:sqs:us-east-1:123456789012:orders-analytics-queue

REM 4. Create DynamoDB orders table
aws dynamodb create-table ^
  --table-name orders ^
  --attribute-definitions AttributeName=order_id,AttributeType=S ^
  --key-schema AttributeName=order_id,KeyType=HASH ^
  --billing-mode PAY_PER_REQUEST ^
  --region us-east-1

REM 5. Deploy Producer Lambda (publishes to SNS)
aws lambda create-function ^
  --function-name order-producer ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/producer-role ^
  --handler producer.lambda_handler ^
  --zip-file fileb://producer.zip ^
  --timeout 30 ^
  --region us-east-1

REM 6. Deploy Consumer Lambda (reads from orders-queue, writes DynamoDB)
aws lambda create-function ^
  --function-name order-consumer ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/consumer-role ^
  --handler consumer.lambda_handler ^
  --zip-file fileb://consumer.zip ^
  --timeout 30 ^
  --memory-size 256 ^
  --region us-east-1

REM 7. Create SQS event source mapping so Lambda polls orders-queue
aws lambda create-event-source-mapping ^
  --function-name order-consumer ^
  --event-source-arn arn:aws:sqs:us-east-1:123456789012:orders-queue ^
  --batch-size 5 ^
  --region us-east-1

REM 8. Test — invoke Producer with a sample order
aws lambda invoke ^
  --function-name order-producer ^
  --payload "{\"order_id\":\"ORD-001\",\"customer_id\":\"C-42\",\"items\":[{\"sku\":\"WIDGET\",\"qty\":2}],\"total\":29.99}" ^
  --cli-binary-format raw-in-base64-out ^
  response.json
```

---

## Data Flow

1. A client POSTs an order JSON to the Producer Lambda (directly or via API Gateway).
2. Producer validates the payload and calls `sns.publish()` with the order body and `event_type=order.created` as a message attribute.
3. SNS immediately delivers a copy of the message to both `orders-queue` and `orders-analytics-queue` (fan-out, ~millisecond latency).
4. The Consumer Lambda's event source mapping polls `orders-queue` using long polling (20-second wait); it picks up batches of up to 5 messages.
5. Consumer deserializes the SNS envelope, extracts the original order JSON, and calls `dynamodb.put_item()` to write the order with `status=PROCESSED`.
6. Lambda deletes successfully processed messages from the queue by returning normally (SQS integration auto-deletes on success).
7. If the Consumer throws an exception, SQS makes the message visible again after the 180-second visibility timeout. After 3 such cycles (`maxReceiveCount=3`), SQS moves the message to `orders-dlq`.
8. The analytics queue retains its copy independently; a separate analytics Lambda or Glue job can consume it on its own schedule.

---

## Project Files

| File | Description |
|---|---|
| `producer.py` | Producer Lambda — validates order JSON, publishes to SNS with message attributes |
| `consumer.py` | Consumer Lambda — reads SQS batch, processes orders, writes to DynamoDB |
| `sqs-policy.json` | SQS queue resource policy allowing SNS to send messages (required for fan-out) |
| `trust-producer.json` | IAM trust policy for producer role (Lambda service principal) |
| `trust-consumer.json` | IAM trust policy for consumer role (Lambda service principal) |
| `sample-order.json` | Example order payload for manual invocation testing |
| `README.md` | This file |

---

## Lessons Learned

- **SNS is push, SQS polling is pull** — SNS pushes to SQS instantly on publish; Lambda then polls SQS via long polling. These are two distinct integration models in the same pipeline. Confusing them leads to misconfigured timeouts and missing messages.
- **Visibility timeout must be ≥ 6× Lambda timeout** — if Consumer Lambda has a 30-second timeout, set `VisibilityTimeout=180` on the queue. A shorter window causes SQS to make the message visible again before Lambda finishes, leading to duplicate processing.
- **DLQ triggers on visibility cycling, not Lambda errors** — messages move to the DLQ because they were received and returned to the queue `maxReceiveCount` times, not because Lambda threw an exception. Lambda errors cause retries only if visibility timeout expires first.
- **SQS Standard does not guarantee order** — for order processing where sequence matters (e.g., order created → order cancelled), use SQS FIFO. Standard is ~3× cheaper but delivers at-least-once in best-effort order.
- **SNS message attributes enable subscription filter policies** — by setting `event_type=order.created` on publish, each SQS subscriber can filter to only the message types it cares about. This avoids processing irrelevant messages in consumers.
- **SQS resource policy is required for SNS fan-out** — the queue must explicitly allow `sns:SendMessage` from the SNS topic ARN in its resource policy, otherwise SNS deliveries silently fail with no error on the SNS side.
- **Batch size tuning affects cost and latency** — a batch size of 1 maximizes isolation (one failure doesn't affect others) but increases Lambda invocation count and cost. Batch size of 10 reduces cost but means one bad message in a batch can cause all 10 to retry.
