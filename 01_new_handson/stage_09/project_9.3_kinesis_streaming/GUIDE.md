# Complete Implementation Guide — Project 9.3: Real-Time Streaming Pipeline
# AWS Kinesis Data Streams + Lambda + DynamoDB + SQS

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 3–4 hours
**Cost per session:** ~$0.50–1.00 | **Depends on:** Project 9.1 (S3 bucket)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Concepts](#2-architecture--concepts)
3. [Prerequisites](#3-prerequisites)
4. [Project Folder Structure](#4-project-folder-structure)
5. [Hands-on Implementation](#5-hands-on-implementation)
   - [A. AWS Console Method](#5a-aws-management-console-method)
   - [B. AWS CLI Method](#5b-aws-cli-method)
   - [C. Terraform Method](#5c-terraform-method)
6. [Code Deep Dive](#6-code-deep-dive)
7. [Verification & Validation](#7-verification--validation)
8. [Observations & Learning Notes](#8-observations--learning-notes)
9. [Screenshots Guidance](#9-screenshots-guidance)
10. [Cleanup Steps](#10-cleanup-steps)

---

## 1. Project Overview

### Project Title
**Real-Time Order Event Streaming with AWS Kinesis, Lambda, DynamoDB, and S3**

### Business / Problem Statement

Your e-commerce company processes thousands of orders per minute. The batch ETL from
Project 9.2 runs once per day — meaning business dashboards show yesterday's data.
The operations team cannot detect a payment fraud spike or inventory shortage in
real-time. By the time the daily report runs, thousands of fraudulent transactions
may have been processed.

**Goal:** Build a real-time streaming pipeline where every order event is processed
within seconds of being placed:
- Orders stream into Kinesis in real-time (sub-second ingestion)
- Lambda processes each record batch and writes live aggregates to DynamoDB
- Operations team sees live order metrics with < 5-second end-to-end latency
- Failed records route to SQS DLQ — pipeline never blocks on bad data

### Pipeline Input → Output (What Goes In, What Comes Out)

Understanding the data flow end-to-end is the most important thing for a beginner.
Here is the exact input and output at every stage of this pipeline:

```
═══════════════════════════════════════════════════════════════════════════════
 INPUT (What you feed into the pipeline)
═══════════════════════════════════════════════════════════════════════════════

SOURCE:  producer.py running on your local machine (or any application)

FORMAT:  JSON event — one per put_record() call

EXAMPLE INPUT EVENT:
{
  "event_id":   "a3f7c1d2-...",       ← unique UUID per event
  "event_type": "ORDER_PLACED",       ← event schema type
  "order_id":   "ORD-45678",          ← business order ID
  "customer_id":"CUST-007",           ← used as partition key (routing)
  "product":    "Widget A",           ← product name
  "quantity":   3,                    ← number of units
  "amount":     45.23,                ← order value in USD (float)
  "timestamp":  "2024-01-15T14:23:45+00:00"  ← UTC ISO-8601
}

VOLUME:   50 events per producer.py run  (~200 bytes each, ~10 KB total)
DELIVERY: kinesis.put_record() → acknowledged per-record with ShardId + SequenceNumber

═══════════════════════════════════════════════════════════════════════════════
 KINESIS STREAM (The buffer / transport layer)
═══════════════════════════════════════════════════════════════════════════════

STREAM NAME:       handson-events
ENCODING:          JSON string → UTF-8 bytes (stored as-is in shard)
PARTITION KEY:     customer_id → MD5 hash → shard assignment
RETENTION:         24 hours (records replayable up to 24h)
WHAT'S STORED:     Exact bytes of your JSON, plus metadata:
                   - SequenceNumber (monotonically increasing per shard)
                   - ApproximateArrivalTimestamp
                   - PartitionKey

═══════════════════════════════════════════════════════════════════════════════
 LAMBDA PROCESSING (The compute / transformation layer)
═══════════════════════════════════════════════════════════════════════════════

TRIGGER INPUT (what Lambda receives — AWS wraps your data automatically):
{
  "Records": [
    {
      "kinesis": {
        "sequenceNumber": "49537014...",
        "approximateArrivalTimestamp": 1705329825.123,
        "data": "eyJldmVudF9pZCI6ICJhM2Y3YzFkMi4uLiJ9",  ← base64 of your JSON
        "partitionKey": "CUST-007",
        "kinesisSchemaVersion": "1.0"
      },
      "eventSource": "aws:kinesis",
      "eventSourceARN": "arn:aws:kinesis:us-east-1:...:stream/handson-events"
    },
    ... (up to 100 records per invocation)
  ]
}

LAMBDA PROCESSING STEPS:
  1. base64.b64decode(record["kinesis"]["data"]) → bytes
  2. json.loads(bytes) → dict (your original event)
  3. Aggregate by product: count++ and revenue += amount
  4. Write to DynamoDB with atomic ADD

═══════════════════════════════════════════════════════════════════════════════
 OUTPUT (What the pipeline produces)
═══════════════════════════════════════════════════════════════════════════════

DESTINATION 1:  DynamoDB Table — handson-stream-aggregates
PURPOSE:        Real-time product revenue aggregates (live dashboard data)

OUTPUT RECORD STRUCTURE:
┌─────────────────────────────────────────────────────────────┐
│  pk  (Partition Key) :  "PRODUCT#Widget A"                  │
│  sk  (Sort Key)      :  "HOUR#2024-01-15T14:00:00Z"         │
│  order_count         :  15    (number of orders this hour)   │
│  total_revenue       :  67845 (CENTS — divide by 100 = $678.45) │
└─────────────────────────────────────────────────────────────┘

REAL-WORLD USE:  Dashboard query: "Show me revenue by product for the last hour"
                 → Scan/Query DynamoDB, convert cents to dollars, display

DESTINATION 2:  SQS DLQ — handson-kinesis-dlq  (only on failures)
PURPOSE:        Captures records that Lambda failed to process after max retries
CONTENT:        Failed Kinesis records for manual inspection / replay

═══════════════════════════════════════════════════════════════════════════════
 COMPLETE INPUT → OUTPUT TRACE (Single Event Example)
═══════════════════════════════════════════════════════════════════════════════

INPUT:
  producer.py puts:  {"product":"Widget A","amount":45.23,"customer_id":"CUST-007",...}
  PartitionKey:      "CUST-007"  → hashes to → Shard 0

KINESIS STORES:
  Shard 0 → SequenceNumber: 49537014..., Data: base64(your JSON)

LAMBDA RECEIVES:
  Batch of 50 records → handler() called once
  Decodes record → product="Widget A", amount=45.23

LAMBDA AGGREGATES (in memory, across all 50 records):
  Widget A: count=15, revenue=$678.45
  Widget B: count=12, revenue=$594.00
  Gadget X: count=8,  revenue=$488.00

LAMBDA WRITES to DynamoDB:
  UPDATE handson-stream-aggregates
  SET order_count += 15, total_revenue += 67845
  WHERE pk="PRODUCT#Widget A" AND sk="HOUR#2024-01-15T14:00:00Z"

OUTPUT in DynamoDB:
  pk="PRODUCT#Widget A"  sk="HOUR#2024-01-15T14:00:00Z"
  order_count=15  total_revenue=67845
```

---

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain the difference between batch ETL (Glue) and streaming (Kinesis)
- [ ] Create a Kinesis Data Stream with provisioned shards
- [ ] Write a Python producer that sends events using `put_record`
- [ ] Configure a Lambda function triggered by Kinesis with batch processing
- [ ] Understand Kinesis shards, partition keys, and sequence numbers
- [ ] Implement the Dead Letter Queue (DLQ) pattern for failed records
- [ ] Read records directly from a shard using the shard iterator API
- [ ] Monitor stream health with CloudWatch metrics (IteratorAge, IncomingRecords)
- [ ] Deploy the complete pipeline with Terraform IaC
- [ ] Calculate Kinesis shard capacity and cost

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME STREAMING PIPELINE                              │
│            (Resources deployed by terraform/main.tf)                        │
│                                                                              │
│  ┌──────────────────────┐                                                    │
│  │   PRODUCER           │                                                    │
│  │  src/producer.py     │  ← runs locally (not deployed to AWS)             │
│  │  generates 50 events │                                                    │
│  └──────────┬───────────┘                                                    │
│             │ put_record(Data=json_event, PartitionKey=customer_id)          │
│             ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐               │
│  │   KINESIS DATA STREAM: handson-events                     │               │
│  │                                                            │               │
│  │   Mode: PROVISIONED | Shards: 1 | Retention: 24 hours    │               │
│  │                                                            │               │
│  │   Shard 0: all CUST-001...CUST-020 (1 shard = all keys)  │               │
│  │   Each record: SequenceNumber + PartitionKey + base64Data │               │
│  │                                                            │               │
│  └───────────────────────────┬──────────────────────────────┘               │
│                              │                                               │
│              Lambda Event Source Mapping polls every 1s                      │
│              batch_size=100, bisect_batch_on_function_error=true             │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────┐                  │
│  │   LAMBDA CONSUMER: handson-kinesis-consumer            │                  │
│  │   src/consumer_lambda.py | Python 3.11 | timeout=60s  │                  │
│  │                                                         │                  │
│  │   handler(event, context):                             │                  │
│  │     for record in event["Records"]:                    │                  │
│  │       1. base64.b64decode(record["kinesis"]["data"])   │                  │
│  │       2. json.loads(bytes) → event dict                │                  │
│  │       3. aggregate: product_totals[product] += amount  │                  │
│  │     for product, totals in product_totals.items():     │                  │
│  │       4. dynamodb.update_item(ADD order_count,         │                  │
│  │                               ADD total_revenue)       │                  │
│  └──────────────────────┬────────────────────────────────┘                  │
│                         │                                                    │
│           ┌─────────────┴──────────────┐                                    │
│           │                            │                                     │
│           ▼ SUCCESS                    ▼ FAILURE (after 3 retries)           │
│  ┌──────────────────────┐    ┌──────────────────────────┐                   │
│  │  DYNAMODB TABLE      │    │  SQS DEAD LETTER QUEUE   │                   │
│  │  handson-stream-     │    │  handson-kinesis-dlq     │                   │
│  │  aggregates          │    │                           │                   │
│  │                      │    │  Permanently failed       │                   │
│  │  pk: PRODUCT#Widget A│    │  records stored here      │                   │
│  │  sk: HOUR#2024-01-.. │    │  for inspection/replay    │                   │
│  │  order_count: 15     │    └──────────────────────────┘                   │
│  │  total_revenue: 67845│      (integer CENTS, not float dollars)           │
│  └──────────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **Kinesis Data Streams** | Real-time event buffer — ordered, replayable, 24h retention | ❌ $0.015/shard-hour |
| **AWS Lambda** | Serverless consumer — triggered by Kinesis, processes batches | ✅ 1M invocations/month |
| **Amazon DynamoDB** | Real-time aggregates store — `pk+sk`, atomic ADD updates | ✅ 25 GB storage free |
| **Amazon SQS** | Dead Letter Queue — captures permanently failed records | ✅ 1M requests/month |
| **AWS IAM** | Role for Lambda — Kinesis read + DynamoDB write + CloudWatch Logs | ✅ Free |
| **CloudWatch Logs** | Lambda execution logs — auto-created at `/aws/lambda/handson-kinesis-consumer` | ✅ 5 GB free |

> **Note:** Kinesis Firehose and S3 are NOT part of this project's Terraform deployment.
> This project focuses on: Kinesis → Lambda → DynamoDB + SQS DLQ.
> See Project 9.1 for S3/data lake architecture.

### Key Concepts Explained

**Kinesis Shard:**
```
1 Shard capacity:
  Inbound:  1,000 records/second OR 1 MB/second (whichever hits first)
  Outbound: 2 MB/second (shared across all consumers)

Example: sending 500 order events/second × ~200 bytes each = ~100 KB/s
→ 1 shard is sufficient (well below 1 MB/s limit)

When to add shards:
  > 1,000 records/s  → add shards
  > 1 MB/s inbound   → add shards
  > 2 MB/s outbound  → add shards OR use Enhanced Fan-Out
```

**Partition Key:**
```python
# producer.py sends with partition_key = customer_id
kinesis.put_record(
    StreamName="handson-events",
    Data=json.dumps(event),
    PartitionKey=event["customer_id"],   # "CUST-001"
)
# Kinesis hashes "CUST-001" → routes to the same shard every time
# All orders for CUST-001 are delivered IN ORDER to Lambda
# This matters for: fraud detection, inventory, real-time customer profiles
```

**Lambda Trigger (Event Source Mapping):**
```
Kinesis → Lambda invocation flow:
  1. Kinesis polls shard every 1 second
  2. Collects up to batch_size=100 records
  3. Calls Lambda handler() with batch
  4. Lambda processes all 100 records in ONE invocation
  5. On success: checkpoint advances, next batch fetched
  6. On partial failure: bisect_batch_on_function_error splits batch
     → retries only the failed half
```

**Dead Letter Queue (DLQ):**
```
Without DLQ:
  Bad record arrives → Lambda fails → Kinesis retries FOREVER
  → Stream processing STOPS for that shard (records pile up)
  → IteratorAge grows → all consumers fall behind

With DLQ (SQS):
  Bad record arrives → Lambda fails → bisect splits batch
  → After max retries, failed record → SQS DLQ
  → Stream processing CONTINUES
  → Failed records available for manual inspection/replay
```

**Batch vs Real-Time Comparison:**

| Dimension | Glue ETL (Project 9.2) | Kinesis (This Project) |
|-----------|------------------------|------------------------|
| Latency | Minutes to hours (batch) | Seconds (streaming) |
| Use case | Daily reports, ML training | Fraud detection, live dashboards |
| Cost | $0.15/run | $10.80/month (1 shard always on) |
| Data size | GB to TB per run | Records/second |
| Replay | Re-run ETL job | 24-hour Kinesis retention |

### Best Practices Followed

- **Partition key = business key** (`customer_id`) — ordered delivery per customer
- **`bisect_batch_on_function_error = true`** — isolates bad records, doesn't block stream
- **DLQ attached** — failed records don't disappear silently
- **`LATEST` starting position** — only process new records (not historical backfill)
- **`batch_size = 100`** — balance between throughput and error isolation
- **DynamoDB PAY_PER_REQUEST** — no capacity planning needed for learning
- **Revenue stored as integer cents** — avoids float precision errors in DynamoDB

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia) — all commands and Terraform use this region
- No other project dependencies — this project is self-contained
- Billing alert recommended at $5 (the only real cost is Kinesis at $0.015/shard-hr)

### 3.2 IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:CreateStream", "kinesis:DeleteStream",
        "kinesis:PutRecord", "kinesis:PutRecords",
        "kinesis:GetRecords", "kinesis:GetShardIterator",
        "kinesis:DescribeStream", "kinesis:ListShards",
        "kinesis:DescribeStreamSummary"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:*:stream/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:*"],
      "Resource": "arn:aws:lambda:us-east-1:*:function:handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:*"],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:*"],
      "Resource": "arn:aws:sqs:us-east-1:*:handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:PassRole",
                 "iam:GetRole", "iam:DeleteRole", "iam:DetachRolePolicy",
                 "iam:PutRolePolicy", "iam:DeleteRolePolicy"],
      "Resource": "arn:aws:iam::*:role/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:*"],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/lambda/handson-*"
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install |
|------|---------|---------|
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |
| Terraform | >= 1.5 | `winget install Hashicorp.Terraform` |
| Python | >= 3.9 | `winget install Python.Python.3.11` |
| boto3 | latest | `pip install boto3` |
| Git | latest | `winget install Git.Git` |
| VS Code | latest | `winget install Microsoft.VisualStudioCode` |

### 3.4 Environment Variable Setup

```powershell
# PowerShell — set before running producer
$env:AWS_REGION         = "us-east-1"
$env:STREAM_NAME        = "handson-events"
$env:TABLE_NAME         = "handson-stream-aggregates"
$env:AWS_ACCOUNT_ID     = aws sts get-caller-identity --query Account --output text

# Verify
aws sts get-caller-identity
# Expected: Account, ARN of your IAM user
```

### 3.5 Estimated AWS Cost

| Scenario | Cost |
|----------|------|
| 2-hour learning session (1 shard) | ~$0.03 |
| Full day running (24h × $0.015/shard) | ~$0.36 |
| Monthly if left running | ~$10.80 |
| Lambda (free tier — 1M invocations) | $0.00 |
| DynamoDB (free tier — 25 GB) | $0.00 |

> **Important:** Kinesis is the ONLY cost. Delete the stream immediately after learning.
> `terraform destroy` takes < 30 seconds.

---

## 4. Project Folder Structure

```
project_9.3_kinesis_streaming/
│
├── GUIDE.md                      ← This comprehensive guide (you are here)
├── README.md                     ← Quick start and lessons learned
├── steps.md                      ← Condensed CLI commands reference
├── steps_awsconsoleui.md         ← Console UI steps (improved template format)
├── verify.md                     ← Verification checklist + CLI checks
├── cost_estimate.md              ← Kinesis shard pricing breakdown
│
├── src/
│   ├── producer.py               ← Python: generates + sends events to Kinesis
│   └── consumer_lambda.py        ← Lambda handler: processes batches, writes DynamoDB
│
├── terraform/
│   ├── main.tf                   ← All AWS resources
│   ├── variables.tf              ← Configurable parameters
│   ├── outputs.tf                ← Exported values after apply
│   └── terraform.tfvars          ← Your values (fill in before applying)
│
└── docs/
    └── architecture.md           ← Deep-dive architecture and shard capacity math
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `src/producer.py` | Standalone Python script — run locally to send events to Kinesis |
| `src/consumer_lambda.py` | Lambda handler — deployed as ZIP by Terraform, triggered by Kinesis |
| `terraform/main.tf` | Kinesis stream, Lambda function + trigger, DynamoDB table, SQS DLQ |
| `terraform/variables.tf` | Shard count, retention, batch size, Lambda timeout — all tunable |
| `terraform/outputs.tf` | Stream name/ARN, Lambda name, DynamoDB table, quick-run commands |
| `docs/architecture.md` | Shard capacity math, partition key strategy, batch vs streaming |

---

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> Region: us-east-1 (N. Virginia). All navigation paths below are for the current AWS Console UI.

---

### PHASE 0 — Prerequisites Check

**Prerequisites Check:**
- ✅ Required permissions: `kinesis:CreateStream`, `lambda:CreateFunction`, `dynamodb:CreateTable`, `iam:CreateRole`, `sqs:CreateQueue`
- ✅ Services enabled: Kinesis, Lambda, DynamoDB, SQS all available in us-east-1
- ✅ Region: us-east-1 selected in top-right of AWS Console
- ✅ `src/consumer_lambda.py` exists locally (needed for Lambda ZIP upload)

**Step 0.1: Verify Region**
1. Look at the top-right of the AWS Console
2. **Expected View:** `N. Virginia` or `us-east-1`
3. **If Different:** Click the region name → select **US East (N. Virginia) us-east-1**

**📸 Screenshot P0:** AWS Console top bar showing us-east-1 region selected

---

### STEP 1 — Create Kinesis Data Stream

**Prerequisites Check:**
- ✅ Required permissions: `kinesis:CreateStream`, `kinesis:DescribeStream`
- ✅ Services enabled: Amazon Kinesis available in us-east-1
- ✅ Understanding: 1 shard = 1 MB/s in, 2 MB/s out, costs $0.015/hr

**Step 1.1: Navigate to Kinesis Console**

1. In the search bar, type **Kinesis** → click **Amazon Kinesis**
2. **Expected View:** Kinesis dashboard with options for Data Streams, Firehose, Analytics
3. Click **Data Streams** in the left sidebar (or from the dashboard)
4. **Expected View:** Empty list of streams with **Create data stream** button

**📸 Screenshot 1a:** Kinesis Data Streams empty list before creation

**Step 1.2: Initiate Stream Creation**

1. Click **Create data stream** (orange button, top-right)
2. **Expected View:** Stream creation form

**Step 1.3: Configure Stream Properties**

**Decision Point 1:** Stream naming
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Generic name (e.g., `my-stream`) | Simple projects | ❌ Not descriptive |
| Project-prefixed name | Consistent naming | ✅ Use `handson-events` |
| Environment-prefixed (e.g., `prod-events`) | Multi-environment | ❌ Single env for learning |

| Field | Value | Explanation |
|-------|-------|-------------|
| Data stream name | `handson-events` | Matches Terraform naming |

**Step 1.4: Choose Capacity Mode**

**Decision Point 2:** Capacity mode
| Option | Use Case | Cost | For This Project |
|--------|----------|------|-----------------|
| **On-demand** | Unknown/variable throughput | Scales auto, $0.08/GB | ❌ More expensive for learning |
| **Provisioned** | Predictable load, cost-sensitive | $0.015/shard-hr | ✅ Use this — fixed cost |

1. Select **Provisioned**
2. **Shard count:** `1`
3. **Why 1 shard?**
   - Our producer sends ~50 events × ~200 bytes = ~10 KB total
   - 1 shard handles up to 1 MB/s — we use < 1% of capacity
   - Adding more shards = more cost, no benefit at this scale

**Expected throughput display:** `1 MB/s input | 2 MB/s output`

**📸 Screenshot 1b:** Stream creation form showing Provisioned mode, 1 shard

**Step 1.5: Create the Stream**

1. Click **Create data stream**
2. **Expected Outcome:** Stream status shows **Creating** → then **Active** (30–60 seconds)
3. **If Stuck on Creating:** Wait up to 2 minutes and refresh

**Troubleshooting:**
- "LimitExceededException": Account shard limit reached — delete unused streams first
- "AccessDenied": IAM user missing `kinesis:CreateStream` — add the permission

**📸 Screenshot 1c:** Stream `handson-events` with Status = **Active**

**Step 1.6: Verify Stream Details**

1. Click on `handson-events` stream name
2. **Expected View:** Stream details page with tabs: Details, Monitoring, Enhanced fan-out
3. Under **Details** tab, verify:

| Property | Expected Value |
|----------|---------------|
| Stream name | `handson-events` |
| Status | Active |
| Shard count | 1 |
| Retention period | 24 hours |
| Encryption | Disabled (fine for learning) |

**📸 Screenshot 1d:** Stream details showing shard count=1, retention=24h, Status=Active

---

### STEP 2 — Create DynamoDB Table for Aggregates

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`
- ✅ Understanding: Table stores real-time product revenue aggregates
- ✅ pk = partition key (PRODUCT#Widget A), sk = sort key (HOUR#2024-01-15T14:00)

**Step 2.1: Navigate to DynamoDB**

1. Search bar → **DynamoDB** → click it
2. Left sidebar → **Tables**
3. **Expected View:** Tables list (empty or existing tables)
4. Click **Create table** (orange button)

**Step 2.2: Configure Table Settings**

**Decision Point 1:** Table naming
| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-stream-aggregates` | Matches Terraform naming |

**Decision Point 2:** Primary key design
| Field | Value | Why |
|-------|-------|-----|
| Partition key | `pk` (String) | Composite: `PRODUCT#Widget A` |
| Sort key | `sk` (String) | Composite: `HOUR#2024-01-15T14:00` |

Why this key design? The `pk + sk` combination uniquely identifies
"Widget A orders in the 2pm hour on Jan 15". Lambda uses `update_item`
with ADD expression to increment order_count atomically.

**Decision Point 3:** Capacity settings
| Option | Use Case | Cost | For This Project |
|--------|----------|------|-----------------|
| **Provisioned** | Predictable load | Fixed RCU/WCU cost | ❌ Need capacity planning |
| **On-demand** | Variable/unknown load | Pay per request | ✅ No planning needed |

1. Select **On-demand** (Pay per request)

**Step 2.3: Leave Default Settings and Create**

1. Leave all other settings as default (no secondary indexes needed)
2. Click **Create table**
3. **Expected Outcome:** Table status: **Creating** → **Active** (30 seconds)

**📸 Screenshot 2a:** DynamoDB table `handson-stream-aggregates` with Status = Active

---

### STEP 3 — Create IAM Role for Lambda

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`
- ✅ Understanding: Lambda needs permission to read Kinesis, write DynamoDB, write CloudWatch Logs

**Step 3.1: Navigate to IAM**

1. Search bar → **IAM** → click it
2. Left sidebar → **Roles** → **Create role**

**Step 3.2: Select Trusted Entity**

**Decision Point 1:** Trusted entity type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | Service-to-service | ✅ Lambda assumes this role |
| AWS account | Cross-account | ❌ Not needed |
| Web identity | Federated/OIDC | ❌ Not needed |

1. Select **AWS service**
2. **Use case:** scroll down and select **Lambda**
3. Click **Next**

**Step 3.3: Attach Policies**

**Decision Point 2:** Policy strategy
| Approach | Security | For This Project |
|----------|----------|-----------------|
| Managed policies only | Basic | ❌ Missing Kinesis + DynamoDB |
| Managed + custom inline | Right-sized | ✅ Use this |

1. Search for and select: **AWSLambdaBasicExecutionRole** (CloudWatch Logs write access)
2. Click **Next**

**Step 3.4: Name the Role**

| Field | Value |
|-------|-------|
| Role name | `handson-kinesis-consumer-role` |
| Description | `Lambda role for Kinesis stream processing` |

3. Click **Create role**

**Step 3.5: Add Inline Policy for Kinesis + DynamoDB**

1. Click on role name `handson-kinesis-consumer-role`
2. Click **Add permissions** → **Create inline policy**
3. Click **JSON** tab
4. Paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:ListStreams",
        "kinesis:ListShards"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:YOUR_ACCOUNT_ID:stream/handson-events"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem",
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/handson-stream-aggregates"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:handson-kinesis-dlq"
    }
  ]
}
```

5. Click **Next** → Policy name: `kinesis-dynamo-access` → **Create policy**

**📸 Screenshot 3a:** IAM role with `AWSLambdaBasicExecutionRole` + `kinesis-dynamo-access` attached

---

### STEP 4 — Create Lambda Function

**Prerequisites Check:**
- ✅ IAM role `handson-kinesis-consumer-role` created
- ✅ `src/consumer_lambda.py` exists locally
- ✅ Required permissions: `lambda:CreateFunction`, `iam:PassRole`

**Step 4.1: Navigate to Lambda**

1. Search bar → **Lambda** → click it
2. **Expected View:** Lambda functions list
3. Click **Create function** (orange button)

**Step 4.2: Choose Function Creation Method**

**Decision Point 1:** Creation method
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Author from scratch | Write code in browser | ❌ Our code is pre-written |
| Use a blueprint | Template-based | ❌ Generic, not our logic |
| Container image | Docker container | ❌ Overkill for Python |
| Browse serverless app repository | Community apps | ❌ Not needed |

1. Select **Author from scratch**

**Step 4.3: Configure Basic Information**

| Field | Value | Explanation |
|-------|-------|-------------|
| Function name | `handson-kinesis-consumer` | Matches Terraform naming |
| Runtime | **Python 3.11** | Latest stable Python |
| Architecture | x86_64 | Standard, compatible with all libraries |

**Decision Point 2:** Permissions
| Option | For This Project |
|--------|-----------------|
| Create a new role with basic Lambda permissions | ❌ We already created the role |
| Use an existing role | ✅ Select `handson-kinesis-consumer-role` |

1. Under **Permissions** → **Execution role** → **Use an existing role**
2. Existing role: select `handson-kinesis-consumer-role`

3. Click **Create function**
4. **Expected View:** Lambda editor with Hello World code

**📸 Screenshot 4a:** Lambda function created — showing editor with default code

**Step 4.4: Upload the Lambda Code**

1. In the **Code** tab, click **Upload from** → **.zip file**
2. But first, create a ZIP of `consumer_lambda.py`:

```powershell
# Run in PowerShell in project directory
Compress-Archive -Path src\consumer_lambda.py -DestinationPath consumer.zip -Force
```

3. Click **Upload** → select `consumer.zip` → **Save**
4. **Expected View:** Code editor now shows `consumer_lambda.py`

**Step 4.5: Configure Environment Variables**

1. Click **Configuration** tab → **Environment variables** → **Edit**
2. Click **Add environment variable**:

| Key | Value |
|-----|-------|
| `TABLE_NAME` | `handson-stream-aggregates` |

3. Click **Save**

**Step 4.6: Configure Timeout**

1. Still in **Configuration** tab → **General configuration** → **Edit**
2. **Timeout:** 1 min 0 sec (60 seconds)
3. Click **Save**

**📸 Screenshot 4b:** Lambda Configuration showing env var TABLE_NAME and 60s timeout

---

### STEP 5 — Create SQS Dead Letter Queue

**Prerequisites Check:**
- ✅ Required permissions: `sqs:CreateQueue`
- ✅ Understanding: Receives failed Kinesis records after max retry exhaustion

**Step 5.1: Navigate to SQS**

1. Search bar → **SQS** → click **Simple Queue Service**
2. Click **Create queue**

**Step 5.2: Configure Queue**

**Decision Point 1:** Queue type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Standard | High throughput, at-least-once | ✅ Fine for DLQ |
| FIFO | Exactly-once, ordered | ❌ Not needed for dead letters |

| Field | Value |
|-------|-------|
| Type | Standard |
| Name | `handson-kinesis-dlq` |

1. Leave all other settings as defaults
2. Click **Create queue**

**📸 Screenshot 5a:** SQS queue `handson-kinesis-dlq` created

---

### STEP 6 — Add Kinesis Trigger to Lambda

**Prerequisites Check:**
- ✅ Kinesis stream `handson-events` Active
- ✅ Lambda function `handson-kinesis-consumer` created
- ✅ SQS DLQ `handson-kinesis-dlq` created
- ✅ IAM role has Kinesis read permissions

**Step 6.1: Navigate Back to Lambda**

1. Go to Lambda → click `handson-kinesis-consumer`
2. Click **Configuration** tab → **Triggers** → **Add trigger**
3. **Expected View:** Trigger configuration form

**Step 6.2: Configure the Trigger**

**Decision Point 1:** Trigger source
| Option | For This Project |
|--------|-----------------|
| Kinesis | ✅ Our stream source |
| SQS | ❌ Different pattern |
| S3 | ❌ File-based, not streaming |
| DynamoDB Streams | ❌ Different use case |

1. Source: **Kinesis**
2. **Kinesis stream:** select `handson-events`
3. **Batch size:** `100` (process up to 100 records per Lambda invocation)
4. **Starting position:** `Latest` (process new records only, not historical)
5. **Batch window:** `0` seconds (trigger immediately — don't wait to fill the batch)

**Decision Point 2:** Starting position
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Latest | Process only new records | ✅ Normal production use |
| Trim horizon | Process ALL records from beginning | ❌ Would replay old data |
| At timestamp | Start from specific time | ❌ Advanced use case |

**Step 6.3: Configure Error Handling**

Scroll down to **Additional settings** (expand if collapsed):

| Field | Value | Why |
|-------|-------|-----|
| Bisect batch on function error | ✅ Enable | Splits failed batch to isolate bad records |
| Retry attempts | `3` | Retry failed batches up to 3 times |
| Destination on failure | SQS → `handson-kinesis-dlq` | Capture permanently failed records |

**📸 Screenshot 6a:** Trigger configuration showing batch size, starting position, error handling

**Step 6.4: Save and Validate**

1. Click **Add**
2. **Expected View:** Trigger listed under Lambda Triggers tab with State: **Enabled**

**Troubleshooting:**
- "InvalidParameterValueException: Role missing Kinesis permissions": Go back to IAM role and verify the inline policy has `kinesis:GetRecords`
- Trigger shows **Disabled**: Usually an IAM permission issue — check role

**📸 Screenshot 6b:** Lambda Triggers tab showing Kinesis trigger with State = Enabled

---

### STEP 7 — Test with Producer (Send Events)

**Prerequisites Check:**
- ✅ All resources created and active
- ✅ Python + boto3 installed locally
- ✅ AWS CLI configured with correct credentials

**Step 7.1: Run Producer Script**

Open a terminal/PowerShell in the project directory:

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming

pip install boto3
python src/producer.py
```

**Expected Output:**
```
Sending 50 events to stream: handson-events
  [1/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537014...
  [2/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537015...
  ...
  [50/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537063...

Done. Sent 50 events.
```

**What's happening internally:**
1. `kinesis.put_record()` sends each event synchronously
2. Kinesis acknowledges with a `SequenceNumber` and `ShardId`
3. Lambda trigger detects new records within 1 second
4. Lambda invokes with a batch of up to 100 records
5. Lambda decodes base64, parses JSON, aggregates by product
6. Lambda writes increments to DynamoDB

**📸 Screenshot 7a:** Terminal showing producer output with 50 events sent

**Step 7.2: Watch Lambda Logs in Real-Time**

1. Go to Lambda → `handson-kinesis-consumer` → **Monitor** tab
2. Click **View CloudWatch logs**
3. Click on the most recent log stream
4. **Expected View:** Log entries showing batch processing:
```
Processing batch of 50 records
  Processed: ORDER_PLACED | Product: Widget A | Amount: $45.23
  Processed: ORDER_PLACED | Product: Widget B | Amount: $31.10
  ...
Batch complete: 50 records, 0 errors
```

**📸 Screenshot 7b:** CloudWatch logs showing Lambda processing the 50-record batch

**Step 7.3: Check DynamoDB Aggregates**

1. Go to DynamoDB → Tables → `handson-stream-aggregates`
2. Click **Explore table items** (orange button)
3. **Expected View:** Items like:

| pk | sk | order_count | total_revenue |
|----|----|----|---|
| PRODUCT#Widget A | HOUR#2024-01-15T14:00:00Z | 15 | 45300 |
| PRODUCT#Widget B | HOUR#2024-01-15T14:00:00Z | 12 | 37200 |
| PRODUCT#Gadget X | HOUR#2024-01-15T14:00:00Z | 8 | 48800 |

Note: `total_revenue` is stored in **cents** (integer) — divide by 100 for dollars.

**📸 Screenshot 7c:** DynamoDB table showing product aggregates with order_count and revenue

**Step 7.4: View Stream Metrics in CloudWatch**

1. Go to CloudWatch → **Metrics** → **All metrics**
2. Search: **Kinesis** → click namespace **AWS/Kinesis**
3. Click **Stream Metrics** → select `handson-events`
4. Select metrics to graph:
   - `IncomingRecords` — records put per minute
   - `GetRecords.IteratorAgeMilliseconds` — how far behind Lambda is (should be near 0)
   - `IncomingBytes` — data volume

**Expected observations:**
- `IncomingRecords`: spike to 50 when producer ran
- `IteratorAge`: briefly non-zero, then drops back to 0 (Lambda caught up)

**📸 Screenshot 7d:** CloudWatch showing IncomingRecords spike and IteratorAge near 0

---

---

## 5B. AWS CLI Method

> Run all commands in PowerShell from the project directory.
> Set variables once at the start, then copy-paste each block.

### Setup — Export Variables

```powershell
$STREAM    = "handson-events"
$TABLE     = "handson-stream-aggregates"
$FUNCTION  = "handson-kinesis-consumer"
$DLQ       = "handson-kinesis-dlq"
$ROLE      = "handson-kinesis-consumer-role"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$REGION    = "us-east-1"

Write-Host "Account: $ACCOUNT | Region: $REGION"
```

---

### CLI Step 1 — Create Kinesis Data Stream

```bash
# Create stream with 1 provisioned shard
aws kinesis create-stream \
  --stream-name $STREAM \
  --shard-count 1

# Wait for stream to become active (polls every 10s)
Write-Host "Waiting for stream to become active..."
aws kinesis wait stream-exists --stream-name $STREAM

# Verify stream is ACTIVE
aws kinesis describe-stream-summary \
  --stream-name $STREAM \
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount,Retention:RetentionPeriodHours}"

# Expected output:
# {
#     "Status": "ACTIVE",
#     "Shards": 1,
#     "Retention": 24
# }
```

**Command explanation:**
- `--shard-count 1` — 1 shard = 1 MB/s in, 2 MB/s out
- `wait stream-exists` — polls `DescribeStream` until status = ACTIVE (~30s)

---

### CLI Step 2 — Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name $TABLE \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# Wait for table to become active
aws dynamodb wait table-exists --table-name $TABLE

# Verify
aws dynamodb describe-table --table-name $TABLE \
  --query "Table.{Name:TableName,Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}"

# Expected:
# {
#     "Name": "handson-stream-aggregates",
#     "Status": "ACTIVE",
#     "BillingMode": "PAY_PER_REQUEST"
# }
```

---

### CLI Step 3 — Create IAM Role and Policies

```bash
# Create trust policy for Lambda
@"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
"@ | Out-File -FilePath /tmp/lambda-trust.json -Encoding utf8

# Create role
aws iam create-role `
  --role-name $ROLE `
  --assume-role-policy-document file:///tmp/lambda-trust.json

# Attach managed policy (CloudWatch Logs)
aws iam attach-role-policy `
  --role-name $ROLE `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create inline policy for Kinesis + DynamoDB
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["kinesis:GetRecords","kinesis:GetShardIterator",
                 "kinesis:DescribeStream","kinesis:DescribeStreamSummary",
                 "kinesis:ListStreams","kinesis:ListShards"],
      "Resource": "arn:aws:kinesis:${REGION}:${ACCOUNT}:stream/${STREAM}"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:UpdateItem","dynamodb:PutItem","dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:${REGION}:${ACCOUNT}:table/${TABLE}"
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage"],
      "Resource": "arn:aws:sqs:${REGION}:${ACCOUNT}:${DLQ}"
    }
  ]
}
"@ | Out-File -FilePath /tmp/kinesis-policy.json -Encoding utf8

aws iam put-role-policy `
  --role-name $ROLE `
  --policy-name kinesis-dynamo-access `
  --policy-document file:///tmp/kinesis-policy.json

# Get role ARN (needed for Lambda creation)
$ROLE_ARN = aws iam get-role --role-name $ROLE `
  --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"
```

---

### CLI Step 4 — Create SQS DLQ

```bash
$DLQ_URL = aws sqs create-queue --queue-name $DLQ `
  --query "QueueUrl" --output text

$DLQ_ARN = aws sqs get-queue-attributes `
  --queue-url $DLQ_URL `
  --attribute-names QueueArn `
  --query "Attributes.QueueArn" --output text

Write-Host "DLQ ARN: $DLQ_ARN"
```

---

### CLI Step 5 — Package and Deploy Lambda

```bash
# Create ZIP from consumer_lambda.py
Compress-Archive -Path src\consumer_lambda.py -DestinationPath consumer.zip -Force

# Wait a moment for IAM role to propagate (5-10s)
Start-Sleep -Seconds 10

# Create Lambda function
aws lambda create-function `
  --function-name $FUNCTION `
  --runtime python3.11 `
  --role $ROLE_ARN `
  --handler consumer_lambda.handler `
  --zip-file fileb://consumer.zip `
  --timeout 60 `
  --environment "Variables={TABLE_NAME=$TABLE}"

# Expected output:
# {
#     "FunctionName": "handson-kinesis-consumer",
#     "FunctionArn": "arn:aws:lambda:us-east-1:...",
#     "State": "Pending"
# }

# Wait for Lambda to be Active
aws lambda wait function-active --function-name $FUNCTION
Write-Host "Lambda is Active"

# Get stream ARN
$STREAM_ARN = aws kinesis describe-stream-summary `
  --stream-name $STREAM `
  --query "StreamDescriptionSummary.StreamARN" --output text

# Add Kinesis trigger to Lambda
aws lambda create-event-source-mapping `
  --function-name $FUNCTION `
  --event-source-arn $STREAM_ARN `
  --starting-position LATEST `
  --batch-size 100 `
  --bisect-batch-on-function-error `
  --destination-config "OnFailure={Destination=$DLQ_ARN}"

# Expected output:
# {
#     "UUID": "abc-123-...",
#     "EventSourceArn": "arn:aws:kinesis:...",
#     "FunctionArn": "arn:aws:lambda:...",
#     "State": "Creating"
# }

Write-Host "Trigger created. Waiting for it to become Enabled..."
Start-Sleep -Seconds 15

# Verify trigger state
aws lambda list-event-source-mappings `
  --function-name $FUNCTION `
  --query "EventSourceMappings[0].{State:State,BatchSize:BatchSize,Source:EventSourceArn}"
# Expected: State=Enabled
```

---

### CLI Step 6 — Send Events and Verify

```bash
# Send 50 events
python src/producer.py

# Expected: 50 events sent to handson-events

# Wait for Lambda to process (< 5 seconds)
Start-Sleep -Seconds 5

# Check Lambda invocations
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Invocations `
  --dimensions Name=FunctionName,Value=$FUNCTION `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 `
  --statistics Sum `
  --query "Datapoints[*].Sum"
# Expected: [1.0] or [2.0] (invocation count)

# Check DynamoDB for aggregates
aws dynamodb scan `
  --table-name $TABLE `
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" `
  --output table

# Expected output:
# -----------------------------------------------------------------------
# |                           Scan                                       |
# +----------------+------------------------+--------+-----------------+
# |  Product       |  Hour                  | Orders | Revenue (cents) |
# +----------------+------------------------+--------+-----------------+
# | PRODUCT#Gadget |  HOUR#2024-01-15T14:00 |  10    |  48500          |
# | PRODUCT#Widget |  HOUR#2024-01-15T14:00 |  15    |  44970          |
# +----------------+------------------------+--------+-----------------+

# Check DLQ for failed records (should be empty on success)
aws sqs get-queue-attributes `
  --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages"
# Expected: "0"
```

---

### CLI Step 7 — Read Directly from Shard (Manual Consumer)

```bash
# Get a shard iterator (TRIM_HORIZON = read from beginning)
$SHARD_ID = aws kinesis list-shards `
  --stream-name $STREAM `
  --query "Shards[0].ShardId" --output text

$ITERATOR = aws kinesis get-shard-iterator `
  --stream-name $STREAM `
  --shard-id $SHARD_ID `
  --shard-iterator-type TRIM_HORIZON `
  --query "ShardIterator" --output text

# Read up to 10 records
$RESPONSE = aws kinesis get-records `
  --shard-iterator $ITERATOR `
  --limit 10

# Decode and print the first record
$RECORD = ($RESPONSE | ConvertFrom-Json).Records[0]
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($RECORD.Data)) | ConvertFrom-Json

# Expected output:
# {
#   "event_id": "abc-123",
#   "event_type": "ORDER_PLACED",
#   "order_id": "ORD-45678",
#   "customer_id": "CUST-007",
#   "product": "Widget A",
#   "amount": 45.23,
#   "timestamp": "2024-01-15T14:23:45+00:00"
# }
```

**Why this matters:** Kinesis retains records for 24 hours. You can replay
any window of data from any shard. This is the "replayability" advantage over
SQS (which deletes messages after successful consumption).

---

## 5C. Terraform Method

### Complete Terraform Configuration

All four files are pre-written in `terraform/`. Below is a fully annotated walkthrough
of what each block does and why, cross-referenced to the actual file content.

---

**`terraform/terraform.tfvars`** — your runtime values (edit before applying)

```hcl
region  = "us-east-1"
project = "handson"

# Kinesis Stream
shard_count     = 1    # 1 shard = $0.015/hr. Minimum for learning.
retention_hours = 24   # 24h minimum. Records replayable for 24 hours.

# Lambda Consumer
lambda_runtime     = "python3.11"   # Must match runtime in main.tf
lambda_timeout     = 60             # seconds — Kinesis batches finish in < 5s
batch_size         = 100            # records per Lambda invocation (1–10000)
max_retry_attempts = 3              # retries before routing failed record to DLQ
```

---

**`terraform/variables.tf`** — declares and validates all parameters

Key variable descriptions from the actual file:

| Variable | Default | Validation | Notes |
|----------|---------|-----------|-------|
| `region` | `us-east-1` | none | All resources go here |
| `project` | `handson` | none | Prefix for all resource names |
| `shard_count` | `1` | 1–10 | Provisioned shards — each costs $0.015/hr |
| `retention_hours` | `24` | 24–8760 | Replay window — 24h = minimum, no extra cost |
| `lambda_runtime` | `python3.11` | python3.9–3.12 | Must match handler syntax |
| `lambda_timeout` | `60` | none | In seconds, max 900 |
| `batch_size` | `100` | 1–10000 | Records per Lambda invocation |
| `max_retry_attempts` | `3` | none | Retries before DLQ routing |

---

**`terraform/main.tf`** — all AWS resources with full annotations

```hcl
terraform {
  required_providers {
    aws     = { source = "hashicorp/aws",     version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
    # archive provider: creates ZIP files from local Python files
    # needed to package consumer_lambda.py → consumer.zip for Lambda
  }
}

provider "aws" { region = var.region }
# Single provider — all resources go in the same region

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
  # Tags applied to all resources for cost allocation and filtering
}

# ── Kinesis Data Stream ─────────────────────────────────────────────────────
resource "aws_kinesis_stream" "events" {
  name             = "${var.project}-events"    # → "handson-events"
  shard_count      = var.shard_count            # → 1 (from terraform.tfvars)
  retention_period = var.retention_hours        # → 24 (hours)

  stream_mode_details {
    stream_mode = "PROVISIONED"
    # PROVISIONED: you allocate shards, pay per shard-hour ($0.015/hr)
    # ON_DEMAND:   AWS auto-scales, pay per GB processed ($0.08/GB)
    # PROVISIONED is cheaper for predictable/low-volume learning workloads
  }
  tags = merge(local.common_tags, { Name = "${var.project}-events" })
}

# ── DynamoDB Table for Aggregates ───────────────────────────────────────────
resource "aws_dynamodb_table" "aggregates" {
  name         = "${var.project}-stream-aggregates"  # → "handson-stream-aggregates"
  billing_mode = "PAY_PER_REQUEST"
  # PAY_PER_REQUEST: no capacity planning, pay per operation
  # Free tier covers 1M writes/reads per month — plenty for this project

  hash_key  = "pk"   # Partition key — "PRODUCT#Widget A"
  range_key = "sk"   # Sort key      — "HOUR#2024-01-15T14:00:00Z"

  attribute { name = "pk" type = "S" }   # S = String
  attribute { name = "sk" type = "S" }   # S = String
  # Only indexed attributes need declaration — other fields (order_count,
  # total_revenue) are added dynamically by Lambda's update_item call

  tags = merge(local.common_tags, { Name = "${var.project}-stream-aggregates" })
}

# ── IAM Role for Lambda ─────────────────────────────────────────────────────
resource "aws_iam_role" "lambda" {
  name = "${var.project}-kinesis-consumer-role"   # → "handson-kinesis-consumer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
      # Lambda service can assume this role — this is the trust policy
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  # Grants: logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
  # Required for Lambda to write execution output to CloudWatch Logs
}

resource "aws_iam_role_policy" "lambda_kinesis_dynamo" {
  name = "kinesis-dynamo-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",           # read records from shard
          "kinesis:GetShardIterator",     # get cursor position in shard
          "kinesis:DescribeStream",       # describe stream metadata
          "kinesis:ListStreams",           # list available streams
          "kinesis:ListShards"            # list shards in stream
        ]
        Resource = aws_kinesis_stream.events.arn
        # Scoped to THIS stream only — not all Kinesis streams
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",   # atomic ADD for order_count and total_revenue
          "dynamodb:PutItem",      # fallback create if item doesn't exist
          "dynamodb:GetItem"       # read current value (used for validation)
        ]
        Resource = aws_dynamodb_table.aggregates.arn
        # Scoped to THIS table only — least privilege
      }
    ]
  })
  # Note: sqs:SendMessage for DLQ is handled by Lambda service automatically
  # when destination_config is set on the event source mapping
}

# ── Lambda ZIP from local source ────────────────────────────────────────────
data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/consumer_lambda.py"
  # path.module = terraform/ directory
  # ../src/consumer_lambda.py = the actual Lambda handler code
  output_path = "${path.module}/consumer.zip"
  # Creates terraform/consumer.zip at plan/apply time
}
# This is a DATA source (not resource) — runs locally, no AWS API calls
# If consumer_lambda.py changes → output_base64sha256 changes → Lambda redeploys

# ── Lambda Function ─────────────────────────────────────────────────────────
resource "aws_lambda_function" "consumer" {
  filename         = data.archive_file.lambda.output_path   # terraform/consumer.zip
  function_name    = "${var.project}-kinesis-consumer"      # → "handson-kinesis-consumer"
  role             = aws_iam_role.lambda.arn
  handler          = "consumer_lambda.handler"
  # handler = "filename_without_extension.function_name"
  # consumer_lambda.py contains def handler(event, context)
  runtime          = var.lambda_runtime    # → "python3.11"
  timeout          = var.lambda_timeout    # → 60 seconds
  source_code_hash = data.archive_file.lambda.output_base64sha256
  # Hash of ZIP content — Terraform uses this to detect code changes
  # If hash changes → Lambda function updates automatically on next apply

  environment {
    variables = { TABLE_NAME = aws_dynamodb_table.aggregates.name }
    # consumer_lambda.py reads: TABLE_NAME = os.environ.get("TABLE_NAME")
    # Injected at deploy time — no hardcoded table name in code
  }
  tags = local.common_tags
}

# ── Kinesis → Lambda Trigger (Event Source Mapping) ─────────────────────────
resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn = aws_kinesis_stream.events.arn
  function_name    = aws_lambda_function.consumer.arn
  starting_position             = "LATEST"
  # LATEST:       process only records written AFTER this trigger is created
  # TRIM_HORIZON: replay ALL records in the 24h retention window (dangerous)
  batch_size                    = var.batch_size   # → 100 records per invocation
  bisect_batch_on_function_error = true
  # true: if Lambda throws an exception, split batch in half and retry each half
  # Quickly isolates the bad record — stream processing is NOT blocked

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.dlq.arn
      # After max_retry_attempts exhausted → failed record → SQS DLQ
      # Stream processing CONTINUES — bad records don't block the pipeline
    }
  }
}

# ── SQS Dead Letter Queue ────────────────────────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  name = "${var.project}-kinesis-dlq"   # → "handson-kinesis-dlq"
  # Standard queue — best-effort ordering, at-least-once delivery
  # DLQ doesn't need FIFO — dead letters are inspected manually
  tags = local.common_tags
}
```

---

**`terraform/outputs.tf`** — values exported after `terraform apply`

All outputs from the actual file:

| Output | Value | Usage |
|--------|-------|-------|
| `stream_name` | `handson-events` | `$STREAM_NAME` in scripts |
| `stream_arn` | full ARN | IAM policies, event source mapping |
| `table_name` | `handson-stream-aggregates` | DynamoDB scan commands |
| `lambda_name` | `handson-kinesis-consumer` | CloudWatch logs, CLI commands |
| `lambda_arn` | full ARN | trigger configuration |
| `dlq_url` | SQS queue URL | `sqs delete-message`, inspect |
| `dlq_arn` | full ARN | destination_config reference |
| `cloudwatch_log_group` | `/aws/lambda/handson-kinesis-consumer` | `aws logs tail` |
| `run_producer` | `python src/producer.py` | quick copy-paste command |
| `tail_logs` | `aws logs tail ... --follow` | real-time log monitoring |
| `check_aggregates` | `aws dynamodb scan ...` | verify DynamoDB output |
| `cost_per_hour` | `$0.015/hr for 1 shard(s)` | cost awareness |

---

### Terraform Workflow — Step by Step

**Step T1 — Initialize**

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming\terraform
terraform init
```

**Expected output:**
```
Initializing provider plugins...
- Installing hashicorp/aws v5.x.x...
- Installing hashicorp/archive v2.x.x...

Terraform has been successfully initialized!
```

Two providers downloaded:
- `aws` — manages Kinesis, Lambda, DynamoDB, SQS, IAM
- `archive` — creates `consumer.zip` from `consumer_lambda.py` locally

---

**Step T2 — Plan**

```powershell
terraform plan -var-file="terraform.tfvars"
```

**Expected output (condensed):**
```
  # aws_kinesis_stream.events will be created
  + resource "aws_kinesis_stream" "events" {
      + name             = "handson-events"
      + shard_count      = 1
      + retention_period = 24
      + stream_mode      = "PROVISIONED"
    }

  # aws_dynamodb_table.aggregates will be created
  + resource "aws_dynamodb_table" "aggregates" {
      + name         = "handson-stream-aggregates"
      + billing_mode = "PAY_PER_REQUEST"
      + hash_key     = "pk"
      + range_key    = "sk"
    }

  # aws_lambda_function.consumer will be created
  + resource "aws_lambda_function" "consumer" {
      + function_name = "handson-kinesis-consumer"
      + handler       = "consumer_lambda.handler"
      + runtime       = "python3.11"
      + timeout       = 60
    }

  # aws_lambda_event_source_mapping.kinesis will be created
  + resource "aws_lambda_event_source_mapping" "kinesis" {
      + batch_size                     = 100
      + bisect_batch_on_function_error = true
      + starting_position              = "LATEST"
    }

  # aws_sqs_queue.dlq will be created        → "handson-kinesis-dlq"
  # aws_iam_role.lambda will be created       → "handson-kinesis-consumer-role"
  # aws_iam_role_policy.lambda_kinesis_dynamo → "kinesis-dynamo-access"
  # aws_iam_role_policy_attachment.lambda_basic → AWSLambdaBasicExecutionRole
  # data.archive_file.lambda                  → reads consumer_lambda.py → consumer.zip

Plan: 9 to add, 0 to change, 0 to destroy.
```

What to verify in the plan:
- `batch_size = 100` matches `terraform.tfvars`
- `bisect_batch_on_function_error = true` — error isolation enabled
- `starting_position = "LATEST"` — no history replay
- `handler = "consumer_lambda.handler"` — filename matches `src/consumer_lambda.py`

---

**Step T3 — Apply**

```powershell
terraform apply -var-file="terraform.tfvars"
# Type: yes when prompted
```

**Expected output:**
```
aws_sqs_queue.dlq: Creating...
aws_kinesis_stream.events: Creating...
aws_iam_role.lambda: Creating...
aws_dynamodb_table.aggregates: Creating...
aws_sqs_queue.dlq: Creation complete after 2s
aws_iam_role.lambda: Creation complete after 3s
aws_iam_role_policy_attachment.lambda_basic: Creating...
aws_iam_role_policy.lambda_kinesis_dynamo: Creating...
aws_kinesis_stream.events: Creation complete after 14s
aws_dynamodb_table.aggregates: Creation complete after 8s
aws_iam_role_policy_attachment.lambda_basic: Creation complete after 2s
aws_iam_role_policy.lambda_kinesis_dynamo: Creation complete after 2s
aws_lambda_function.consumer: Creating...
aws_lambda_function.consumer: Creation complete after 8s
aws_lambda_event_source_mapping.kinesis: Creating...
aws_lambda_event_source_mapping.kinesis: Creation complete after 16s

Apply complete! Resources: 9 added, 0 changed, 0 destroyed.

Outputs:
  check_aggregates     = "aws dynamodb scan --table-name handson-stream-aggregates ..."
  cloudwatch_log_group = "/aws/lambda/handson-kinesis-consumer"
  cost_per_hour        = "$0.015/hr for 1 shard(s)"
  dlq_arn              = "arn:aws:sqs:us-east-1:123456789012:handson-kinesis-dlq"
  dlq_url              = "https://sqs.us-east-1.amazonaws.com/123456789012/handson-kinesis-dlq"
  lambda_arn           = "arn:aws:lambda:us-east-1:123456789012:function:handson-kinesis-consumer"
  lambda_name          = "handson-kinesis-consumer"
  run_producer         = "python src/producer.py"
  stream_arn           = "arn:aws:kinesis:us-east-1:123456789012:stream/handson-events"
  stream_name          = "handson-events"
  table_name           = "handson-stream-aggregates"
  tail_logs            = "aws logs tail /aws/lambda/handson-kinesis-consumer --follow"
```

**📸 Screenshot T1:** `terraform apply` completion showing all 9 resources + 12 outputs

---

**Step T4 — State and Outputs**

```powershell
# List all managed resources (confirm 9)
terraform state list
# Expected:
# aws_dynamodb_table.aggregates
# aws_iam_role.lambda
# aws_iam_role_policy.lambda_kinesis_dynamo
# aws_iam_role_policy_attachment.lambda_basic
# aws_kinesis_stream.events
# aws_lambda_event_source_mapping.kinesis
# aws_lambda_function.consumer
# aws_sqs_queue.dlq
# data.archive_file.lambda

# Inspect the event source mapping
terraform state show aws_lambda_event_source_mapping.kinesis
# Look for: batch_size=100, bisect_batch_on_function_error=true, State=Enabled

# Get useful quick commands
terraform output run_producer     # python src/producer.py
terraform output tail_logs        # aws logs tail ... --follow
terraform output check_aggregates # aws dynamodb scan ...

# Confirm no config drift
terraform plan -var-file="terraform.tfvars"
# Expected: No changes. Your infrastructure matches the configuration.
```

---

## 6. Code Deep Dive

### `src/producer.py` — Line by Line

```python
STREAM_NAME = "handson-events"
kinesis = boto3.client("kinesis", region_name="us-east-1")
```
- `boto3.client("kinesis")` creates a Kinesis control-plane client
- `region_name` must match where your stream was created
- All `put_record` calls go to this client

```python
def generate_event() -> dict:
    return {
        "event_id":    str(uuid.uuid4()),     # globally unique ID — no collisions
        "event_type":  "ORDER_PLACED",        # event schema versioning starts here
        "customer_id": random.choice(CUSTOMERS),
        "amount":      round(random.uniform(9.99, 99.99), 2),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        # timezone.utc — always UTC, never local time, avoids DST bugs
    }
```

```python
response = kinesis.put_record(
    StreamName=STREAM_NAME,
    Data=json.dumps(event),          # Kinesis payload is raw bytes — JSON encode first
    PartitionKey=event["customer_id"], # CRITICAL: determines which shard receives record
)
```
- `Data` must be `bytes` or `str` — `json.dumps()` converts dict to string
- `PartitionKey` is hashed by Kinesis using MD5 → shard assignment
- Same `customer_id` → same hash → same shard → **ordered delivery per customer**
- `response["ShardId"]` — which shard accepted the record
- `response["SequenceNumber"]` — unique monotonically increasing ID within the shard

**Common mistake:** Using `PartitionKey="static_value"` for all records → all records
go to shard 0 → uneven load → "hot shard" bottleneck. Use a high-cardinality key.

---

### `src/consumer_lambda.py` — Line by Line

```python
def handler(event: dict, context) -> dict:
    records = event.get("Records", [])
```
- `event["Records"]` is a list of Kinesis records in this batch (up to `batch_size`)
- Each record is a dict with `kinesis` key containing the actual data
- `context` provides Lambda metadata (function name, remaining time, etc.)

```python
    payload = json.loads(base64.b64decode(record["kinesis"]["data"]))
```
- Kinesis data is **always base64-encoded** in the Lambda event — this is mandatory decoding
- `record["kinesis"]["data"]` is the base64 string
- `base64.b64decode(...)` → bytes → `json.loads(...)` → dict
- **Common mistake:** Forgetting `base64.b64decode` → `json.loads` fails on base64 string

```python
        product_totals[product]["count"]   += 1
        product_totals[product]["revenue"] += amount
```
- `defaultdict(lambda: {"count":0, "revenue":0.0})` — auto-creates entries for new products
- Aggregates the entire batch in memory BEFORE writing to DynamoDB
- One `update_item` per product per batch — not one per record (reduces DynamoDB cost)

```python
    table.update_item(
        Key={"pk": f"PRODUCT#{product}", "sk": f"HOUR#{hour_key}"},
        UpdateExpression="ADD order_count :c, total_revenue :r",
        ExpressionAttributeValues={":c": totals["count"], ":r": int(totals["revenue"] * 100)},
    )
```
- `ADD` expression is **atomic increment** — safe for concurrent Lambda invocations
- If two Lambda invocations run simultaneously for the same product, DynamoDB
  guarantees both increments are applied correctly (no lost updates)
- `int(totals["revenue"] * 100)` — converts dollars to cents as integer
  (DynamoDB Number type is exact for integers; floats can have precision errors)
- Key pattern `PRODUCT#Widget A` — the `#` separator is a best practice in DynamoDB
  single-table design (allows multiple entity types in one table)

```python
    if errors:
        return {
            "batchItemFailures": [
                {"itemIdentifier": seq} for seq in errors
            ]
        }
```
- Returning `batchItemFailures` tells Lambda which specific records failed
- Lambda retries ONLY those records, not the entire batch
- Without this: Lambda retries the whole batch → duplicates processed records
- With `bisect_batch_on_function_error=true` in Terraform: even without this return,
  Lambda splits the batch in half to narrow down bad records

---

### `terraform/main.tf` — Key Resource Explanations

```hcl
resource "aws_kinesis_stream" "events" {
  shard_count      = var.shard_count    # 1 shard = $0.015/hr
  retention_period = var.retention_hours # 24h = replay window
  stream_mode_details {
    stream_mode = "PROVISIONED"
    # PROVISIONED: pay per shard-hour (predictable cost)
    # ON_DEMAND: pay per GB processed (auto-scales)
  }
}
```

```hcl
resource "aws_lambda_event_source_mapping" "kinesis" {
  starting_position             = "LATEST"
  # LATEST: process only new records after trigger is created
  # TRIM_HORIZON: process ALL records from the beginning (dangerous for large streams)

  batch_size                    = 100
  # Process up to 100 records per Lambda invocation
  # Larger batch = fewer invocations = cheaper Lambda
  # Smaller batch = faster processing per invocation = lower latency

  bisect_batch_on_function_error = true
  # If Lambda throws an exception:
  #   Split batch in half → retry each half separately
  #   Quickly isolates the bad record without blocking the whole stream
}
```

```hcl
data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/consumer_lambda.py"
  output_path = "${path.module}/consumer.zip"
}
# archive_file is a DATA source (not resource) — runs locally
# Creates consumer.zip from consumer_lambda.py at plan/apply time
# If consumer_lambda.py changes → source_code_hash changes → Lambda re-deploys
```

---

### Common Mistakes and Fixes

| Mistake | Error / Symptom | Fix |
|---------|----------------|-----|
| Forgetting `base64.b64decode` | `json.JSONDecodeError` in Lambda logs | Always decode before `json.loads` |
| Using `"static"` as partition key | All records on shard 0, hot shard | Use high-cardinality key like `customer_id` |
| Not returning `batchItemFailures` | Entire batch retried on any error | Return partial failure list |
| Forgetting `job.commit()` equivalent | Lambda processes same records repeatedly | Kinesis checkpoints automatically on success |
| DynamoDB float for revenue | Precision errors: `45.9999999` | Store as integer cents: `int(amount * 100)` |
| `starting_position = "TRIM_HORIZON"` | Lambda replays all 24h of history | Use `LATEST` for production |
| Shard count = 0 | `InvalidArgumentException` | Minimum 1 shard for PROVISIONED mode |

---

## 7. Verification & Validation

### 7.1 AWS Console Verification

| Resource | Navigation Path | Expected State |
|----------|----------------|---------------|
| Kinesis Stream | Kinesis → Data Streams | `handson-events` Status = **Active** |
| Shard count | Stream → Details tab | Shard count = 1 |
| Lambda function | Lambda → Functions | `handson-kinesis-consumer` exists |
| Lambda trigger | Lambda → Configuration → Triggers | Kinesis trigger State = **Enabled** |
| DynamoDB table | DynamoDB → Tables | `handson-stream-aggregates` Status = **Active** |
| DynamoDB items | Table → Explore items | Items appear after running producer |
| SQS DLQ | SQS → Queues | `handson-kinesis-dlq` exists, 0 messages |
| CloudWatch Logs | CloudWatch → Log groups | `/aws/lambda/handson-kinesis-consumer` |

### 7.2 Full CLI Verification Script

```powershell
$STREAM   = "handson-events"
$TABLE    = "handson-stream-aggregates"
$FUNCTION = "handson-kinesis-consumer"
$DLQ      = "handson-kinesis-dlq"

Write-Host "=== VERIFICATION: Project 9.3 Kinesis Streaming ===" -ForegroundColor Cyan

# CHECK 1 — Kinesis stream active
Write-Host "`n[1] Kinesis stream status..."
aws kinesis describe-stream-summary --stream-name $STREAM `
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount,Retention:RetentionPeriodHours}" `
  --output table
# Expected: Status=ACTIVE, Shards=1, Retention=24

# CHECK 2 — Lambda function exists
Write-Host "`n[2] Lambda function state..."
aws lambda get-function --function-name $FUNCTION `
  --query "Configuration.{Name:FunctionName,State:State,Runtime:Runtime,Timeout:Timeout}"
# Expected: State=Active, Runtime=python3.11, Timeout=60

# CHECK 3 — Kinesis trigger on Lambda
Write-Host "`n[3] Lambda Kinesis trigger..."
aws lambda list-event-source-mappings --function-name $FUNCTION `
  --query "EventSourceMappings[0].{State:State,BatchSize:BatchSize,StartPos:StartingPosition}"
# Expected: State=Enabled, BatchSize=100, StartPos=LATEST

# CHECK 4 — DynamoDB table active
Write-Host "`n[4] DynamoDB table status..."
aws dynamodb describe-table --table-name $TABLE `
  --query "Table.{Name:TableName,Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}"
# Expected: Status=ACTIVE, BillingMode=PAY_PER_REQUEST

# CHECK 5 — DLQ exists with zero messages
Write-Host "`n[5] SQS DLQ..."
$DLQ_URL = aws sqs get-queue-url --queue-name $DLQ --query "QueueUrl" --output text
aws sqs get-queue-attributes --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages"
# Expected: "0"

# CHECK 6 — Send events and verify Lambda runs
Write-Host "`n[6] Sending test events..."
python src/producer.py
Start-Sleep -Seconds 10

Write-Host "`n[7] Lambda invocations (last 5 min)..."
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Invocations `
  --dimensions Name=FunctionName,Value=$FUNCTION `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Sum `
  --query "Datapoints[*].Sum"
# Expected: [1.0] or more

# CHECK 8 — DynamoDB has aggregates
Write-Host "`n[8] DynamoDB aggregates..."
aws dynamodb scan --table-name $TABLE `
  --query "Count"
# Expected: > 0

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

### 7.3 Terraform State Verification

```bash
cd terraform

terraform state list
# Expected (9 resources):
# aws_dynamodb_table.aggregates
# aws_iam_role.lambda
# aws_iam_role_policy.lambda_kinesis_dynamo
# aws_iam_role_policy_attachment.lambda_basic
# aws_kinesis_stream.events
# aws_lambda_event_source_mapping.kinesis
# aws_lambda_function.consumer
# aws_sqs_queue.dlq
# data.archive_file.lambda

terraform plan -var-file="terraform.tfvars"
# Expected: No changes. Your infrastructure matches the configuration.
```

### 7.4 End-to-End Health Check

```powershell
# Full pipeline test: produce → process → verify in DynamoDB
Write-Host "Starting end-to-end test..."

# 1. Produce events
python src/producer.py
Write-Host "✅ Step 1: Events produced"

# 2. Wait for Lambda processing
Start-Sleep -Seconds 10
Write-Host "✅ Step 2: Waited for Lambda processing"

# 3. Verify DynamoDB has records
$COUNT = aws dynamodb scan --table-name handson-stream-aggregates `
  --query "Count" --output text
Write-Host "✅ Step 3: DynamoDB has $COUNT aggregate records"

# 4. Check iterator age is 0 (caught up)
$AGE = aws cloudwatch get-metric-statistics `
  --namespace AWS/Kinesis `
  --metric-name "GetRecords.IteratorAgeMilliseconds" `
  --dimensions Name=StreamName,Value=handson-events `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Maximum `
  --query "Datapoints[0].Maximum" --output text
Write-Host "✅ Step 4: Iterator age = $AGE ms (should be near 0)"

# 5. Verify DLQ is empty (no failures)
$DLQ_URL = aws sqs get-queue-url --queue-name handson-kinesis-dlq `
  --query "QueueUrl" --output text
$DLQ_COUNT = aws sqs get-queue-attributes --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages" --output text
Write-Host "✅ Step 5: DLQ has $DLQ_COUNT messages (should be 0)"
```

### 7.5 Expected Successful Outputs

```
Kinesis stream:  Status=ACTIVE, Shards=1, Retention=24h
Lambda trigger:  State=Enabled, BatchSize=100
DynamoDB:        Status=ACTIVE, items > 0 after producing
DLQ:             ApproximateNumberOfMessages = 0
IteratorAge:     Near 0ms (Lambda keeping up)
Lambda errors:   0 (Errors metric = 0)
terraform plan:  No changes
```

### 7.6 Verification Checklist

- [ ] Kinesis stream `handson-events` Status = ACTIVE, 1 shard
- [ ] Lambda `handson-kinesis-consumer` State = Active
- [ ] Lambda trigger State = Enabled, BatchSize = 100
- [ ] DynamoDB `handson-stream-aggregates` Status = ACTIVE
- [ ] SQS DLQ `handson-kinesis-dlq` exists with 0 messages
- [ ] `producer.py` sends 50 events without error
- [ ] Lambda invocations metric > 0 after producing
- [ ] DynamoDB items appear after producing events
- [ ] Iterator age drops to ~0 (Lambda keeps up)
- [ ] `terraform plan` shows no changes

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During Execution

**When producer.py runs:**
- Each `put_record` response returns a `ShardId` and `SequenceNumber`
- All events with the same `customer_id` go to the **same shard** (same hash)
- Sequence numbers increase monotonically within each shard (ordered delivery)
- The response is synchronous — `put_record` confirms delivery before the next event

**When Lambda processes:**
- Lambda polls the shard every 1 second (when idle) or immediately (when records arrive)
- First invocation may show STARTING state for ~15 seconds
- Lambda gets a batch of up to 100 records, runs your `handler()` function once
- Watch CloudWatch: Lambda duration should be < 5 seconds for 50 records

**In DynamoDB after processing:**
- Each `pk+sk` combination is upserted (created or incremented)
- `order_count` and `total_revenue` grow with each producer run
- Revenue is stored as integer cents (multiply by 100) — you'll see `4523` not `45.23`

### 8.2 Internal AWS Behavior

```
producer.py → put_record() → Kinesis shard buffer
                              │
                              │ Lambda polls every 1s
                              ▼
                         Lambda service reads batch
                              │
                              │ Invokes your function
                              ▼
                         handler(event, context)
                              │
                         Processes records
                              │
                    ┌─────────┴──────────┐
                    │                    │
               Success              Failure (exception)
                    │                    │
          Checkpoint advanced       bisect_batch = true
          Next batch fetched        Retry half-batch
                                         │
                                    After max_retries
                                         │
                                    → SQS DLQ
                                    (stream continues)
```

**Key internal detail:** Lambda's Kinesis trigger maintains a **lease** on each shard.
Only one Lambda invocation processes a given shard at a time. If you have 2 shards,
you could have 2 concurrent Lambda invocations — one per shard.

### 8.3 Resource Dependencies

```
aws_kinesis_stream.events
    ↓ (ARN used by)
aws_lambda_event_source_mapping.kinesis
    ↑ (also depends on)
aws_lambda_function.consumer
    ↑ (depends on)
aws_iam_role.lambda
    ↑ (depends on)
aws_iam_role_policy.lambda_kinesis_dynamo
    (references both Kinesis stream ARN and DynamoDB table ARN)
aws_dynamodb_table.aggregates
    (referenced in IAM policy and Lambda env var)
```

Terraform resolves this dependency graph automatically from the `resource.attribute`
references in the code. `depends_on` is only needed when the dependency is implicit.

### 8.4 Billing Observations

- **Kinesis:** Billing starts the moment the stream is ACTIVE — even with zero records
- **Lambda:** Only billed when invoked — zero cost between producer runs
- **DynamoDB:** PAY_PER_REQUEST = charged per `update_item` call
- **SQS DLQ:** Only charged if Lambda actually fails and sends to DLQ

For a 2-hour lab with 50 events:
```
Kinesis:   2h × $0.015/shard-hr = $0.03
Lambda:    ~1 invocation × free tier = $0.00
DynamoDB:  ~5 update_item calls × $0.00000125 = $0.00
SQS:       0 messages (assuming no failures) = $0.00
Total:     ~$0.03
```

### 8.5 Performance Observations

- **Latency:** Event produced → Lambda processes → DynamoDB updated in ~2–3 seconds
- **Throughput:** 1 shard can handle 1,000 events/second — our 50 events/run is trivial
- **Iterator age:** Should be 0ms or < 1000ms — means Lambda is keeping up
- **Batch efficiency:** 100 records per invocation = 1 Lambda call instead of 100

### 8.6 Kinesis vs SQS — When to Use Which

| Dimension | Kinesis Data Streams | SQS |
|-----------|---------------------|-----|
| Ordering | Per shard, per partition key | FIFO only (with FIFO queue) |
| Replay | Yes — 24h to 7 days | No — messages deleted after consumption |
| Multiple consumers | Yes — each reads independently | No — each message consumed once |
| Cost | $0.015/shard-hr (always on) | $0.40/million messages |
| Use case | Event streaming, analytics | Task queues, decoupling |
| Best for | Time-series, ordered events, audit | Jobs, notifications, microservices |

---

## 9. Screenshots Guidance

### Before Implementation
| # | What to Capture | When |
|---|----------------|------|
| SS-01 | AWS Console with us-east-1 region selected | Before starting |
| SS-02 | Kinesis Data Streams — empty list | Before Step 1 |
| SS-03 | Lambda functions — empty list | Before Step 4 |
| SS-04 | DynamoDB tables — empty list | Before Step 2 |

### During Setup (Console)
| # | What to Capture | When |
|---|----------------|------|
| SS-05 | Kinesis stream creation form (Provisioned, 1 shard) | Step 1.3 |
| SS-06 | DynamoDB create table form (pk+sk, on-demand) | Step 2.2 |
| SS-07 | IAM role with both policies attached | Step 3.5 |
| SS-08 | Lambda function creation form (Python 3.11, existing role) | Step 4.3 |
| SS-09 | Lambda trigger configuration (batch 100, LATEST, bisect on) | Step 6.2 |

### After Deployment
| # | What to Capture | When |
|---|----------------|------|
| SS-10 | Kinesis stream `handson-events` Status = **Active** | After Step 1 |
| SS-11 | Lambda trigger tab showing Kinesis trigger = **Enabled** | After Step 6 |
| SS-12 | Terminal showing producer.py output — 50 events sent | After Step 7.1 |
| SS-13 | CloudWatch logs — Lambda batch processing output | After Step 7.2 |
| SS-14 | DynamoDB Explore items — product aggregates table | After Step 7.3 |
| SS-15 | CloudWatch — IncomingRecords spike metric | After Step 7.4 |
| SS-16 | CloudWatch — IteratorAge = near 0ms | After Step 7.4 |

### Terraform Deployment
| # | What to Capture | When |
|---|----------------|------|
| SS-17 | `terraform init` — two providers downloaded | During 5C |
| SS-18 | `terraform plan` — 9 resources to add | During 5C |
| SS-19 | `terraform apply` — all 9 resources created + outputs | During 5C |
| SS-20 | `terraform state list` — 9 resources managed | During 5C |

### Validation
| # | What to Capture | When |
|---|----------------|------|
| SS-21 | SQS DLQ showing 0 messages (clean run) | After verify |
| SS-22 | Lambda Monitoring tab — Invocations graph | After verify |

**Total: 22 screenshots** — complete documentation portfolio for this project.

---

## 10. Cleanup Steps

> **Important:** Kinesis charges $0.015/shard-hour continuously — even with no data.
> A stream left running for a month costs ~$10.80. Always destroy after learning.

### 10.1 Terraform Destroy (Recommended)

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming\terraform

terraform destroy -var-file="terraform.tfvars"
# Type: yes
```

**Expected output:**
```
aws_lambda_event_source_mapping.kinesis: Destroying...
aws_lambda_event_source_mapping.kinesis: Destruction complete after 15s
aws_lambda_function.consumer: Destroying...
aws_lambda_function.consumer: Destruction complete after 5s
aws_kinesis_stream.events: Destroying...
aws_kinesis_stream.events: Destruction complete after 12s
aws_dynamodb_table.aggregates: Destroying...
aws_dynamodb_table.aggregates: Destruction complete after 8s
aws_sqs_queue.dlq: Destroying...
aws_sqs_queue.dlq: Destruction complete after 3s
aws_iam_role_policy.lambda_kinesis_dynamo: Destroying...
aws_iam_role_policy_attachment.lambda_basic: Destroying...
aws_iam_role.lambda: Destroying...

Destroy complete! Resources: 9 destroyed.
```

**Order of destruction matters:**
1. Event source mapping (Kinesis→Lambda trigger) first — removes the connection
2. Lambda function — after trigger removed
3. Kinesis stream — after Lambda trigger removed
4. DynamoDB, SQS, IAM — after all consumers removed

Terraform handles this order automatically based on dependency graph.

### 10.2 AWS Console Cleanup (if deployed via Console)

1. **Lambda:** Lambda → Functions → select `handson-kinesis-consumer` → Actions → Delete
2. **Kinesis stream:** Kinesis → Data Streams → `handson-events` → Actions → Delete stream
   - Type `handson-events` to confirm → Delete
3. **DynamoDB:** DynamoDB → Tables → `handson-stream-aggregates` → Delete
4. **SQS:** SQS → Queues → `handson-kinesis-dlq` → Delete
5. **IAM Role:** IAM → Roles → `handson-kinesis-consumer-role` → Delete

### 10.3 AWS CLI Cleanup

```powershell
$STREAM   = "handson-events"
$TABLE    = "handson-stream-aggregates"
$FUNCTION = "handson-kinesis-consumer"
$DLQ      = "handson-kinesis-dlq"
$ROLE     = "handson-kinesis-consumer-role"

# 1. Remove Lambda trigger (must be done before deleting Lambda/Kinesis)
$MAPPING_UUID = aws lambda list-event-source-mappings `
  --function-name $FUNCTION `
  --query "EventSourceMappings[0].UUID" --output text
aws lambda delete-event-source-mapping --uuid $MAPPING_UUID
Start-Sleep -Seconds 15  # Wait for trigger to deactivate

# 2. Delete Lambda function
aws lambda delete-function --function-name $FUNCTION

# 3. Delete Kinesis stream
aws kinesis delete-stream --stream-name $STREAM

# 4. Delete DynamoDB table
aws dynamodb delete-table --table-name $TABLE

# 5. Delete SQS DLQ
$DLQ_URL = aws sqs get-queue-url --queue-name $DLQ --query "QueueUrl" --output text
aws sqs delete-queue --queue-url $DLQ_URL

# 6. Delete IAM role (detach policies first)
aws iam detach-role-policy --role-name $ROLE `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role-policy --role-name $ROLE --policy-name kinesis-dynamo-access
aws iam delete-role --role-name $ROLE

# 7. Clean up local ZIP file
Remove-Item -Path terraform\consumer.zip -ErrorAction SilentlyContinue

Write-Host "✅ All resources deleted"
```

### 10.4 Verify Cleanup

```powershell
# Confirm stream is deleted
aws kinesis describe-stream-summary --stream-name handson-events 2>&1 |
  Select-String "ResourceNotFoundException"
# Expected: ResourceNotFoundException

# Confirm Lambda is deleted
aws lambda get-function --function-name handson-kinesis-consumer 2>&1 |
  Select-String "ResourceNotFoundException"
# Expected: ResourceNotFoundException

# Confirm DynamoDB table is deleted
aws dynamodb describe-table --table-name handson-stream-aggregates 2>&1 |
  Select-String "ResourceNotFoundException"
# Expected: ResourceNotFoundException

Write-Host "✅ Cleanup verified — no remaining resources"
```

### 10.5 Cost Verification After Cleanup

```powershell
# Check for any remaining Kinesis charges
aws ce get-cost-and-usage `
  --time-period "Start=$(Get-Date -Format 'yyyy-MM-01'),End=$(Get-Date -Format 'yyyy-MM-dd')" `
  --granularity DAILY `
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Kinesis"]}}' `
  --metrics UnblendedCost `
  --query "ResultsByTime[-1].Total.UnblendedCost.Amount"
# Expected: after destroy, new daily charges stop accruing
```

---

## Quick Reference Card

```
DEPLOY:
  terraform apply -var-file="terraform.tfvars"

SEND EVENTS:
  python src/producer.py

MONITOR:
  aws logs tail /aws/lambda/handson-kinesis-consumer --follow

CHECK AGGREGATES:
  aws dynamodb scan --table-name handson-stream-aggregates --query "Items[*]"

READ SHARD DIRECTLY:
  # Get iterator then get-records (see CLI Step 7)

DESTROY:
  terraform destroy -var-file="terraform.tfvars"

COST:  $0.015/shard-hr = $0.03 for 2hr lab
       Always destroy — Kinesis charges even with no data
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming*
