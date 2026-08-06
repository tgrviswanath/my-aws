# Project 9.3 — Real-Time Streaming Pipeline

## What This Does

Builds a real-time event streaming pipeline: a Python producer sends order events
to Kinesis Data Streams, Lambda processes each batch and writes live aggregates
to DynamoDB. Failed records go to an SQS Dead Letter Queue for safe replay.

## Architecture

```
Producer (src/producer.py — runs locally)
  │  put_record(Data=json_event, PartitionKey=customer_id)
  ▼
Kinesis Data Stream: handson-events
  │  1 shard | 24h retention | PROVISIONED mode
  │  Lambda polls shard every 1s — batch of up to 100 records
  ▼
Lambda: handson-kinesis-consumer (src/consumer_lambda.py)
  │  decode base64 → parse JSON → aggregate by product/hour
  ├──▶ DynamoDB: handson-stream-aggregates  (real-time aggregates)
  └──▶ SQS DLQ: handson-kinesis-dlq         (permanently failed records)
```

## Resources Created by Terraform

| Resource | Name | Type |
|----------|------|------|
| Kinesis Data Stream | `handson-events` | 1 shard, provisioned |
| Lambda Function | `handson-kinesis-consumer` | Python 3.11, 60s timeout |
| Lambda Trigger | Event source mapping | batch=100, LATEST, bisect=true |
| DynamoDB Table | `handson-stream-aggregates` | pk+sk, PAY_PER_REQUEST |
| SQS Queue (DLQ) | `handson-kinesis-dlq` | Standard queue |
| IAM Role | `handson-kinesis-consumer-role` | Kinesis read + DynamoDB write |

## Key Concepts

| Concept | Description |
|---------|-------------|
| Shard | Unit of capacity: 1 MB/s in, 2 MB/s out, 1,000 records/s |
| Partition key | Routes records to a specific shard (hashed by Kinesis) |
| Sequence number | Monotonically increasing unique ID per record within a shard |
| Checkpoint | Lambda advances its position on success — no manual commit needed |
| bisect_batch_on_function_error | Splits failed batch in half to isolate bad records |
| DLQ | SQS queue that receives records Lambda permanently cannot process |

## How to Deploy

```powershell
cd terraform
terraform init
terraform apply -var-file="terraform.tfvars"
terraform output stream_name     # handson-events
terraform output lambda_name     # handson-kinesis-consumer
```

## How to Run

```powershell
# Install dependency
pip install boto3

# Send 50 order events to Kinesis
python src/producer.py

# Watch Lambda logs in real-time (run in a separate terminal)
aws logs tail /aws/lambda/handson-kinesis-consumer --follow

# Check DynamoDB aggregates
aws dynamodb scan `
  --table-name handson-stream-aggregates `
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" `
  --output table
```

## Source Files

| File | Purpose |
|------|---------|
| `src/producer.py` | Generates and sends ORDER_PLACED events to Kinesis via `put_record()` |
| `src/consumer_lambda.py` | Lambda handler: decodes base64, aggregates by product/hour, writes to DynamoDB |
| `terraform/main.tf` | All AWS resources: Kinesis, Lambda + trigger, DynamoDB, SQS DLQ, IAM |
| `terraform/variables.tf` | Configurable: shard_count, retention_hours, batch_size, lambda_timeout |
| `terraform/outputs.tf` | Exports: stream_name, lambda_name, table_name, dlq_url, tail_logs command |
| `terraform/terraform.tfvars` | Runtime values (region, project, shard_count=1, batch_size=100) |
| `docs/architecture.md` | Shard capacity math, error handling flow, dependency graph |

## Lessons Learned

- **Kinesis vs SQS:** Kinesis = ordered, replayable, multiple consumers; SQS = simpler, cheaper, no replay
- **Shard capacity:** 1 shard = 1,000 records/s OR 1 MB/s — scale shards for higher throughput
- **Lambda batch:** processes up to `batch_size=100` records per invocation (configured in terraform.tfvars)
- **bisect_batch_on_function_error:** Lambda splits a failing batch in half to quickly isolate the bad record
- **base64 decoding:** Kinesis always base64-encodes data in the Lambda event — must decode before JSON parsing
- **DLQ pattern:** failed records route to SQS after `max_retry_attempts=3` — stream processing continues unblocked
- **Revenue in cents:** store as `int(amount * 100)` to avoid float precision errors in DynamoDB

## Estimated Cost

| Activity | Cost |
|----------|------|
| 2-hour learning session | ~$0.03 |
| Full day (24h × 1 shard) | ~$0.36 |
| Monthly if left running | ~$10.80 |

> **Always run `terraform destroy` after the lab — Kinesis charges even with zero records.**

## Teardown

```powershell
cd terraform
terraform destroy -var-file="terraform.tfvars"
# Type: yes
```

## Full Guide

For the complete 10-section implementation guide covering Console UI, CLI, Terraform,
Code Deep Dive, Verification, Observations, Screenshots, and Cleanup:

**→ See [GUIDE.md](GUIDE.md)**

---

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription with required permissions | IAM user or role |
| Configuration | Resource settings | Region, names, sizes |
| Source Data | Files or code to deploy | Application source, data files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed and running services | AWS Console / CLI |
| Endpoints | Service URLs and connection strings | Resource overview page |
| Logs | Execution and audit logs | CloudWatch Logs |

## Quick Start
`ash
# Configure AWS CLI
aws configure

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Create resource group
aws ec2 describe-regions --output table
`

## Lessons Learned
- Always tag AWS resources for cost tracking and organization
- Use IAM roles instead of access keys wherever possible
- Delete resources after learning to avoid unexpected charges
- Enable CloudWatch logging for all services in production
- Use the free tier for all lab exercises to minimize cost
