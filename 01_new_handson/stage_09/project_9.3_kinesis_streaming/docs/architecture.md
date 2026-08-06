# Architecture — Project 9.3 Real-Time Streaming Pipeline

## Resources Deployed (from terraform/main.tf)

| Resource | Terraform Name | AWS Name |
|----------|---------------|----------|
| Kinesis Data Stream | `aws_kinesis_stream.events` | `handson-events` |
| Lambda Function | `aws_lambda_function.consumer` | `handson-kinesis-consumer` |
| Lambda Trigger | `aws_lambda_event_source_mapping.kinesis` | Event source mapping |
| DynamoDB Table | `aws_dynamodb_table.aggregates` | `handson-stream-aggregates` |
| SQS Dead Letter Queue | `aws_sqs_queue.dlq` | `handson-kinesis-dlq` |
| IAM Role | `aws_iam_role.lambda` | `handson-kinesis-consumer-role` |

---

## Stream Architecture

```
Producer (src/producer.py — runs locally or from any app)
    │
    │  kinesis.put_record(
    │    StreamName="handson-events",
    │    Data=json.dumps(event),          # ~200 bytes per event
    │    PartitionKey=event["customer_id"] # routes to shard by hash
    │  )
    ▼
Kinesis Data Stream: handson-events
    │  Mode: PROVISIONED | Shards: 1 | Retention: 24 hours
    │  Shard 0 → handles all records (1 shard = all CUST-001..CUST-020)
    │
    │  Lambda Event Source Mapping polls shard every 1s
    │  batch_size=100, starting_position=LATEST
    │  bisect_batch_on_function_error=true
    ▼
Lambda: handson-kinesis-consumer (src/consumer_lambda.py)
    │  Runtime: Python 3.11 | Timeout: 60s
    │  Env: TABLE_NAME=handson-stream-aggregates
    │
    │  For each record in batch:
    │    1. base64.b64decode(record["kinesis"]["data"])
    │    2. json.loads(bytes) → event dict
    │    3. aggregate product → {count++, revenue+=amount}
    │
    │  After all records aggregated:
    │    4. dynamodb.update_item(ADD order_count, ADD total_revenue)
    │       → one write per product per batch (not per record)
    │
    ├── SUCCESS → DynamoDB updated, checkpoint advanced, next batch fetched
    │
    └── FAILURE → bisect batch → retry halves → after 3 retries → SQS DLQ
    ▼
DynamoDB: handson-stream-aggregates
    pk="PRODUCT#Widget A"  sk="HOUR#2024-01-15T10:00:00Z"
    order_count=42          total_revenue=125958   ← integer CENTS (not float)
    (divide total_revenue by 100 to get dollars: $1,259.58)

SQS DLQ: handson-kinesis-dlq
    Receives permanently failed records (Lambda exceeded max_retry_attempts=3)
    Inspect failed records here for debugging / manual replay
```

---

## Shard Capacity Math

```
This project uses 1 shard (shard_count=1 in terraform.tfvars)

1 shard limits:
  Inbound:  1,000 records/second  OR  1 MB/second  (whichever hits first)
  Outbound: 2 MB/second (shared across all consumers of this shard)

Our workload (producer.py sends 50 events):
  50 events × ~200 bytes each = ~10 KB total
  Rate: ~50 events over ~2.5 seconds = ~20 events/s
  Data rate: ~10 KB / 2.5s = ~4 KB/s

Capacity utilisation:
  Records: 20/s ÷ 1,000/s = ~2%   (far below limit)
  Bytes:   4 KB/s ÷ 1,024 KB/s = ~0.4%   (far below limit)

→ 1 shard is more than sufficient for this project.

Scale shards when:
  IncomingRecords  > 800/s      (80% of 1,000/s safety threshold)
  IncomingBytes    > 800 KB/s   (80% of 1 MB/s safety threshold)

Scale up command:
  aws kinesis update-shard-count \
    --stream-name handson-events \
    --target-shard-count 2 \
    --scaling-type UNIFORM_SCALING
```

---

## Partition Key Strategy

```python
# producer.py uses customer_id as partition key
PartitionKey=event["customer_id"]   # e.g. "CUST-007"

# Kinesis hashes the key:
# MD5("CUST-007") → 128-bit hash → mapped to shard range

# Effect:
# - All events from CUST-007 → same shard → same Lambda invocation order
# - Customer's orders are processed IN ORDER (critical for fraud detection)
# - With 1 shard: all customers land on the same shard (fine for learning)
# - With 2+ shards: some customers go to shard 0, others to shard 1

# Anti-pattern to AVOID:
# PartitionKey="ORDER_PLACED"   ← all records hit 1 shard (hot shard)
# PartitionKey="static"         ← same problem

# Good partition keys (high cardinality, business-meaningful):
# customer_id, order_id, device_id, session_id
```

---

## Lambda Batch Processing Flow

```
Kinesis shard has 50 new records
    │
    │ Lambda polls every 1 second
    ▼
Lambda receives event["Records"] = list of 50 items
    │
    │ handler(event, context) called ONCE for the whole batch
    ▼
For each of 50 records:
    base64.b64decode(record["kinesis"]["data"]) → decode
    json.loads(...) → parse
    product_totals[product]["count"]   += 1     ← aggregate in memory
    product_totals[product]["revenue"] += amount

After loop (5 products from 50 records):
    DynamoDB update_item × 5 calls (one per product)
    ADD order_count :c, total_revenue :r

Return: {"statusCode": 200, "processed": 50}
    │
    ▼
Lambda checkpoint advances → shard offset moves forward
Next 1-second poll → finds 0 new records → waits
```

---

## Error Handling Flow

```
Lambda handler throws exception on record 37 of 100
    │
    │ bisect_batch_on_function_error = true
    ▼
Lambda splits batch: records 1-50 | records 51-100
    │
    ├── Retry records 1-50  → succeeds → checkpoint at record 50
    │
    └── Retry records 51-100
          │
          ├── If succeeds → checkpoint at record 100
          │
          └── If still fails → split again: 51-75 | 76-100
                  │
                  └── After max_retry_attempts=3 exhausted:
                        → batchItemFailures returned to Kinesis
                        → permanently failed records → SQS DLQ
                        → stream processing CONTINUES (not blocked)

Without bisect_batch_on_function_error:
    Bad record → entire batch retried → bad record retried forever
    → IteratorAge grows → stream processing STALLS
```

---

## Terraform Resource Dependency Graph

```
data.archive_file.lambda          (zips consumer_lambda.py locally)
    └──▶ aws_lambda_function.consumer
              │
              ├── depends on: aws_iam_role.lambda
              │       ├── aws_iam_role_policy_attachment.lambda_basic
              │       └── aws_iam_role_policy.lambda_kinesis_dynamo
              │               ├── references: aws_kinesis_stream.events.arn
              │               └── references: aws_dynamodb_table.aggregates.arn
              │
              └── env var: aws_dynamodb_table.aggregates.name

aws_lambda_event_source_mapping.kinesis
    ├── depends on: aws_lambda_function.consumer.arn
    ├── depends on: aws_kinesis_stream.events.arn
    └── on_failure: aws_sqs_queue.dlq.arn
```

---

## DynamoDB Key Design

```
Table: handson-stream-aggregates
  Billing: PAY_PER_REQUEST (no capacity planning)

Primary Key:
  pk (String) — Partition Key  →  "PRODUCT#Widget A"
  sk (String) — Sort Key       →  "HOUR#2024-01-15T14:00:00Z"

Example items after running producer.py twice:
  pk="PRODUCT#Widget A"  sk="HOUR#2024-01-15T14:00:00Z"  order_count=15  total_revenue=67845
  pk="PRODUCT#Widget B"  sk="HOUR#2024-01-15T14:00:00Z"  order_count=12  total_revenue=59400
  pk="PRODUCT#Widget C"  sk="HOUR#2024-01-15T14:00:00Z"  order_count=9   total_revenue=26991
  pk="PRODUCT#Gadget X"  sk="HOUR#2024-01-15T14:00:00Z"  order_count=8   total_revenue=48800
  pk="PRODUCT#Gadget Y"  sk="HOUR#2024-01-15T14:00:00Z"  order_count=6   total_revenue=34194

Note: total_revenue is stored as INTEGER CENTS.
  $678.45 → stored as 67845
  To display: total_revenue / 100

Why integer cents?
  DynamoDB Number type is exact for integers.
  Float 45.23 might become 45.2299999... in Python float arithmetic.
  int(45.23 * 100) = 4523 — exact, safe for ADD atomic operations.

Key pattern "PRODUCT#" prefix:
  Follows DynamoDB single-table design best practice.
  Prefix allows multiple entity types in one table without collision.
  e.g. future: "CUSTOMER#CUST-001" sk="HOUR#..." for per-customer aggregates
```

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
