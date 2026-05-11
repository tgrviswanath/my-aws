# Project 4.5 — SNS/SQS Microservices

## What This Does
Builds an async, decoupled microservices system using SNS (pub/sub) and SQS (message queues). Services communicate via messages — no direct API calls between them.

## Architecture
```
Order Service → SNS Topic (order-events)
                    ├── SQS Queue → Inventory Lambda (update stock)
                    ├── SQS Queue → Email Lambda (send confirmation)
                    └── SQS Queue → Analytics Lambda (record metrics)
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| SNS | Pub/Sub — one message → many subscribers |
| SQS Standard | At-least-once delivery, best-effort ordering |
| SQS FIFO | Exactly-once, strict ordering (higher cost) |
| DLQ | Dead Letter Queue — failed messages go here |
| Visibility timeout | Message hidden while being processed |
| Retry policy | Automatic retries on Lambda failure |

## Services Used
- SNS (Simple Notification Service)
- SQS (Simple Queue Service)
- Lambda (3 consumer functions)
- DLQ (Dead Letter Queue for failed messages)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output sns_topic_arn
```

## Lessons Learned
- SNS fan-out: one publish → multiple SQS queues simultaneously
- SQS visibility timeout must be > Lambda timeout to prevent duplicate processing
- DLQ is essential — always configure it so failed messages aren't silently lost
- Lambda SQS trigger: Lambda polls SQS automatically — no need to write polling code
- Batch size: Lambda can process up to 10 SQS messages per invocation
- Idempotency: design consumers to handle duplicate messages safely
