# Complete Implementation Guide — Project 9.4: Spark Processing on EMR Serverless
# AWS EMR Serverless + PySpark + S3 + IAM

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 3–4 hours
**Cost per run:** ~$0.07 | **No Terraform required** — Console + CLI methods only

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Concepts](#2-architecture--concepts)
3. [Prerequisites](#3-prerequisites)
4. [Project Folder Structure](#4-project-folder-structure)
5. [Hands-on Implementation](#5-hands-on-implementation)
   - [A. AWS Management Console Method](#5a-aws-management-console-method)
   - [B. AWS CLI Method](#5b-aws-cli-method)
6. [Code Deep Dive](#6-code-deep-dive)
7. [Verification & Validation](#7-verification--validation)
8. [Observations & Learning Notes](#8-observations--learning-notes)
9. [Screenshots Guidance](#9-screenshots-guidance)
10. [Cleanup Steps](#10-cleanup-steps)

---

## 1. Project Overview

### Project Title
**Distributed Data Processing with Apache Spark on AWS EMR Serverless**

### Business / Problem Statement

Your e-commerce company has grown. The order dataset that was 10 MB last year is
now 50 GB. Running it through a single Python script on your laptop takes 6 hours
and crashes. The daily analytics pipeline is broken. Business decisions are delayed.

**Why this happens:** Single-machine processing is sequential. 50 GB of CSV data
processed row by row is slow. You need to split the data into chunks and process
multiple chunks simultaneously across many machines.

**Goal:** Use Apache Spark on AWS EMR Serverless to:
- Process large order CSV files in parallel across a distributed cluster
- Compute product revenue aggregates by month (for dashboards)
- Compute customer lifetime value (CLV) for the marketing team
- Write output as Parquet (10x faster to query in Athena than CSV)
- Pay only for compute time used — no idle cluster charges

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════
 INPUT
═══════════════════════════════════════════════════════════════════
Location:  s3://YOUR_BUCKET/raw/orders/
Format:    CSV files (one or many, all with same schema)
Schema:
  order_id     STRING   unique order identifier
  customer_id  STRING   customer identifier
  product      STRING   product name
  amount       DOUBLE   order value in USD
  order_date   DATE     in YYYY-MM-DD format

Example row:
  ORD-12345, CUST-007, Widget A, 45.23, 2024-01-15

═══════════════════════════════════════════════════════════════════
 SPARK PROCESSING (src/spark_job.py)
═══════════════════════════════════════════════════════════════════
Step 1: Read all CSV files in input path → distributed DataFrame
Step 2: Clean  → drop nulls, cast types, remove duplicate order_ids
Step 3: Enrich → add year + month columns from order_date
Step 4: Aggregate by product+month → order_count, revenue, CLV stats
Step 5: Aggregate by customer      → lifetime_value, order history
Step 6: Write Parquet output (partitioned by year/month)

═══════════════════════════════════════════════════════════════════
 OUTPUT 1 — Product Monthly Aggregates
═══════════════════════════════════════════════════════════════════
Location:  s3://YOUR_BUCKET/processed/spark/product_monthly/
Format:    Parquet, partitioned by year= / month=
Schema:
  year             INT     partition column
  month            INT     partition column
  product          STRING  product name
  order_count      LONG    number of orders in that month
  total_revenue    DOUBLE  sum of all amounts (rounded to 2dp)
  avg_order_value  DOUBLE  average order amount
  unique_customers LONG    distinct customers who ordered

Example item:
  year=2024, month=1, product=Widget A
  order_count=450, total_revenue=20353.50
  avg_order_value=45.23, unique_customers=312

═══════════════════════════════════════════════════════════════════
 OUTPUT 2 — Customer Lifetime Value
═══════════════════════════════════════════════════════════════════
Location:  s3://YOUR_BUCKET/processed/spark/customer_clv/
Format:    Parquet (flat, no partitioning)
Schema:
  customer_id     STRING  customer identifier
  total_orders    LONG    total orders ever placed
  lifetime_value  DOUBLE  total spend across all time (rounded)
  first_order     DATE    date of first purchase
  last_order      DATE    date of most recent purchase

Example item:
  customer_id=CUST-007, total_orders=12
  lifetime_value=542.76, first_order=2024-01-15, last_order=2024-03-22
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain the difference between single-machine Python and distributed Spark
- [ ] Create an EMR Serverless application via Console and CLI
- [ ] Create an IAM role with the correct trust policy for EMR Serverless
- [ ] Upload a PySpark script to S3 and submit it as a job
- [ ] Understand Spark concepts: Driver, Executor, Partition, Shuffle
- [ ] Read what Adaptive Query Execution (AQE) is and why it matters
- [ ] Interpret Spark job logs in CloudWatch / S3
- [ ] Verify Parquet output in S3 with Hive-style partitions
- [ ] Calculate EMR Serverless cost (vCPU-hours + GB-hours)
- [ ] Clean up all resources to avoid ongoing charges

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  SPARK ON EMR SERVERLESS PIPELINE                        │
│                                                                          │
│  ┌─────────────────────────────────┐                                    │
│  │  S3 INPUT                       │                                    │
│  │  s3://BUCKET/raw/orders/        │                                    │
│  │  *.csv  (any size — GB to TB)   │                                    │
│  └────────────────┬────────────────┘                                    │
│                   │  aws emr-serverless start-job-run                   │
│                   ▼                                                      │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │          EMR SERVERLESS APPLICATION: handson-spark             │    │
│  │          Release: emr-6.15.0 | Type: SPARK                    │    │
│  │                                                                 │    │
│  │   ┌──────────────────┐      ┌────────────────────────────┐    │    │
│  │   │  DRIVER (1 node) │      │  EXECUTORS (auto-scaled)   │    │    │
│  │   │  2 vCPU, 4 GB    │─────▶│  up to 20 vCPU, 40 GB     │    │    │
│  │   │                  │      │                             │    │    │
│  │   │  Reads job plan  │      │  Exec 1: processes part 1  │    │    │
│  │   │  Coordinates     │      │  Exec 2: processes part 2  │    │    │
│  │   │  Collects result │      │  Exec N: processes part N  │    │    │
│  │   └──────────────────┘      └────────────────────────────┘    │    │
│  │                                                                 │    │
│  │   src/spark_job.py runs on cluster:                            │    │
│  │     1. Read CSV partitions in parallel                         │    │
│  │     2. Clean + enrich (distributed map)                        │    │
│  │     3. groupBy + agg (shuffle → reduce)                        │    │
│  │     4. Write Parquet to S3 (parallel write)                    │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                   │                                                      │
│        ┌──────────┴──────────────────────────────┐                     │
│        ▼                                         ▼                     │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐   │
│  │  S3 OUTPUT 1                 │  │  S3 OUTPUT 2                 │   │
│  │  processed/spark/            │  │  processed/spark/            │   │
│  │  product_monthly/            │  │  customer_clv/               │   │
│  │  year=2024/month=1/          │  │  part-00000.snappy.parquet   │   │
│  │  part-00000.snappy.parquet   │  │                              │   │
│  └──────────────────────────────┘  └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **EMR Serverless** | Runs Spark jobs — no cluster to manage | ❌ ~$0.07/run |
| **Amazon S3** | Input data, Spark script, output Parquet, logs | ✅ 5 GB free |
| **AWS IAM** | Role for EMR Serverless to access S3 + Glue | ✅ Free |
| **AWS Glue Data Catalog** | Optional — register output tables for Athena | ✅ 1M objects free |
| **CloudWatch Logs** | Spark driver/executor logs | ✅ 5 GB free |

### Key Concepts Explained

**EMR Serverless vs EMR on EC2:**
```
EMR Serverless (this project):
  ✅ No cluster to create, manage, or SSH into
  ✅ Pay only per job run (vCPU-hours + GB-hours)
  ✅ Auto-scales workers for the job
  ✅ Auto-stops after 15 minutes idle → zero idle cost
  ❌ Cold start: ~30–60s to provision workers
  ❌ Less control over Spark internals

EMR on EC2 (for reference):
  ✅ Full Spark/YARN configuration control
  ✅ Persistent cluster — no cold start per job
  ✅ Spot instances = 60–90% cheaper worker cost
  ❌ You pay for the cluster 24/7 even with no jobs
  ❌ Must manage cluster lifecycle manually
  ❌ m5.xlarge × 3 nodes = ~$420/month always-on
```

**Spark Driver vs Executor:**
```
Driver (1 node — the coordinator):
  - Reads your Python script
  - Builds the execution plan (DAG of stages)
  - Sends tasks to executors
  - Collects and writes final results
  - Memory: 4 GB (defined in initial_capacity)

Executors (auto-scaled workers):
  - Each executor processes one or more data partitions
  - Run tasks in parallel
  - Communicate results back to Driver
  - EMR Serverless scales 0 → N executors based on data size
  - Max: 20 vCPU total (defined in maximum_capacity)
```

**Partition — the unit of parallelism:**
```
S3 file (100 MB CSV)
    │
    │ Spark splits into ~8 partitions (128 MB default split)
    │ Each partition sent to one executor task
    ▼
Executor 1: processes rows 1–12,500
Executor 2: processes rows 12,501–25,000
...
Executor 8: processes rows 87,501–100,000

All 8 tasks run IN PARALLEL → 8x faster than sequential
```

**Shuffle — the expensive operation:**
```
df.groupBy("product").agg(sum("amount"))

Step 1 (Map): Each executor groups its OWN partition rows by product
Step 2 (Shuffle): All rows for "Widget A" must move to the SAME executor
                  This cross-node data transfer = "shuffle"
                  Shuffle is slow — minimize it where possible
Step 3 (Reduce): Each executor now has all rows for its assigned products
                 Sums them up → final result
```

**Adaptive Query Execution (AQE):**
```
spark.sql.adaptive.enabled = true
spark.sql.adaptive.coalescePartitions.enabled = true

Without AQE:
  groupBy on 1M rows → 200 shuffle partitions (Spark default)
  Many partitions have only 10 rows each → 200 tiny tasks → overhead

With AQE (coalescePartitions):
  After shuffle, Spark looks at actual partition sizes
  Merges tiny partitions into fewer, larger ones
  200 partitions → coalesces to 5 → 5 tasks instead of 200
  → 10–40x faster for small/medium datasets
```

### Best Practices Followed

- **EMR Serverless over EC2** — no idle cluster cost for learning workloads
- **AQE enabled** — automatic performance optimization at runtime
- **Parquet output** — columnar format, ~10x cheaper to query in Athena vs CSV
- **Hive-style partitioning** (`year=YYYY/month=MM`) — Athena skips irrelevant partitions
- **`dropDuplicates(["order_id"])`** — idempotent processing, safe to re-run
- **`argparse`** — parameterized script, reusable for different input/output paths
- **Auto-stop after 15 min** — prevents forgotten applications from billing

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia) — all commands use this
- S3 bucket with `raw/orders/` prefix containing CSV order data
  - Can use `sample_orders.csv` from Project 9.1, or create your own
- Billing alert recommended at $5

### 3.2 IAM Permissions Required (for YOUR user)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["emr-serverless:*"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:DeleteRole", "iam:AttachRolePolicy",
                 "iam:DetachRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
                 "iam:GetRole", "iam:PassRole"],
      "Resource": "arn:aws:iam::*:role/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET", "arn:aws:s3:::YOUR_BUCKET/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:*"],
      "Resource": "*"
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) |
|------|---------|------------------|
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |
| Python | >= 3.9 | `winget install Python.Python.3.11` |
| PySpark (local testing only) | 3.x | `pip install pyspark` |
| Git | latest | `winget install Git.Git` |
| VS Code | latest | `winget install Microsoft.VisualStudioCode` |

> **Note:** Terraform is NOT required for this project.

### 3.4 Environment Variable Setup (PowerShell)

```powershell
$env:AWS_REGION   = "us-east-1"
$env:BUCKET       = "handson-data-lake-YOUR_ACCOUNT_ID"
$env:APP_NAME     = "handson-spark"
$env:ROLE_NAME    = "handson-emr-serverless-role"
$env:ACCOUNT      = aws sts get-caller-identity --query Account --output text

# Verify
aws sts get-caller-identity
# Expected: Account, UserId, ARN of your IAM user
```

### 3.5 Estimated AWS Cost

| Activity | Cost |
|----------|------|
| Single job run (~10 min) | ~$0.07 |
| 10 runs during learning | ~$0.70 |
| EMR Serverless idle (auto-stop 15 min) | ~$0.01 |
| S3 storage (< 100 MB output) | ~$0.00 |
| **Typical learning session total** | **~$0.50–$1.00** |

**Cost formula:**
```
vCPU cost  = vCPUs × hours × $0.052/vCPU-hr
Memory cost = GB   × hours × $0.0057/GB-hr

Driver  (2 vCPU, 4 GB, 5 min):  2×(5/60)×$0.052 + 4×(5/60)×$0.0057 = $0.009
Workers (6 vCPU,12 GB, 8 min):  6×(8/60)×$0.052 + 12×(8/60)×$0.0057 = $0.051
Total per run: ~$0.06–$0.08
```

> **Free tier:** EMR Serverless has no free tier. Delete the application after learning.

---

## 4. Project Folder Structure

```
project_9.4_spark_emr/
│
├── GUIDE.md                  ← This comprehensive guide (you are here)
├── README.md                 ← Quick start and lessons learned
├── steps.md                  ← Condensed CLI commands reference (PowerShell)
├── steps_awsconsoleui.md     ← Console UI steps (improved template format)
├── verify.md                 ← Verification checklist + CLI checks
├── cost_estimate.md          ← EMR Serverless pricing breakdown
│
├── src/
│   └── spark_job.py          ← PySpark job: reads CSV → cleans → aggregates → writes Parquet
│
├── terraform/
│   └── main.tf               ← IaC reference (not used in this guide)
│
└── docs/
    └── architecture.md       ← EMR architecture, Spark concepts, partitioning
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `src/spark_job.py` | The Spark job uploaded to S3 and run on EMR. Accepts `--input` and `--output` args. Produces two Parquet datasets. |
| `terraform/main.tf` | Reference only — shows resource names and IAM policy. Not run in this guide. |
| `docs/architecture.md` | EMR Serverless vs EC2 comparison, Spark internals, AQE explanation |
| `steps.md` | Quick-reference CLI commands for the whole pipeline |
| `steps_awsconsoleui.md` | Standalone Console UI steps file |
| `verify.md` | End-to-end verification checklist with CLI commands |
| `cost_estimate.md` | Detailed cost breakdown with formula |

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> Region: us-east-1 (N. Virginia). All navigation paths are for the current AWS Console.
> Estimated time for this method: ~45 minutes

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `emr-serverless:*`, `iam:CreateRole`, `iam:PassRole`, `s3:PutObject`
- ✅ Services enabled: EMR, IAM, S3 — all available in us-east-1
- ✅ Region: us-east-1 selected in top-right of AWS Console
- ✅ S3 bucket with data: `raw/orders/` prefix containing at least one CSV file

**Step 0.1: Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → choose **US East (N. Virginia) us-east-1**

**Step 0.2: Verify S3 Input Data**
1. Search bar → **S3** → click your data lake bucket
2. Navigate to `raw/orders/`
3. **Expected View:** At least one CSV file present
4. **If Missing:** Upload `data/sample_orders.csv` from Project 9.1, or create a sample:

```
order_id,customer_id,product,amount,order_date
ORD-001,CUST-101,Widget A,29.99,2024-01-15
ORD-002,CUST-102,Widget B,49.99,2024-01-15
ORD-003,CUST-101,Widget C,19.99,2024-01-16
```

Save as `orders.csv` and upload to `s3://YOUR_BUCKET/raw/orders/orders.csv`

**📸 Screenshot P0:** S3 bucket showing `raw/orders/` with CSV file

---

#### Step 1 — Create IAM Role for EMR Serverless

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:PutRolePolicy`
- ✅ Services enabled: IAM (global service)
- ✅ Region availability: IAM is global — region does not matter

**Step 1.1: Navigate and Verify**
1. Search bar → **IAM** → click it
2. Left sidebar → **Roles**
3. **Expected View:** Roles list
4. Click **Create role** (orange button)

**📸 Screenshot 1a:** IAM Roles list before creation

**Step 1.2: Make Selections — Trusted Entity**

**Decision Point 1:** Trusted entity type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service (from dropdown) | Common services like EC2, Lambda | ❌ EMR Serverless not listed |
| **Custom trust policy** | Paste your own JSON | ✅ Required for EMR Serverless |
| Web identity | OIDC / GitHub Actions | ❌ Not needed |

1. Select **Custom trust policy**
2. **Clear** the default JSON in the editor
3. **Paste** the following trust policy exactly:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "emr-serverless.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

4. **Why custom?** EMR Serverless (`emr-serverless.amazonaws.com`) is not in the
   dropdown service list. It requires a manually typed trust policy.
5. Click **Next**

**📸 Screenshot 1b:** Custom trust policy form with `emr-serverless.amazonaws.com`

**Step 1.3: Configure Permissions**

**Decision Point 2:** Attach managed policies at creation?
| Option | For This Project |
|--------|-----------------|
| Attach managed policies now | ❌ No suitable managed policy exists |
| Skip — add inline policies after | ✅ We will add 3 inline policies after creation |

1. Do NOT select any managed policies
2. Click **Next**

**Step 1.4: Configure Role Details**

| Field | Value |
|-------|-------|
| Role name | `handson-emr-serverless-role` |
| Description | `EMR Serverless execution role — S3 + Glue + CloudWatch access` |

3. Click **Create role**
4. **Expected Outcome:** Role created, redirected to role details page

**📸 Screenshot 1c:** Role `handson-emr-serverless-role` just created (no policies yet)

**Step 1.5: Add Inline Policy — S3 Access**

1. Click on role `handson-emr-serverless-role`
2. Click **Add permissions** → **Create inline policy**
3. Click **JSON** tab
4. Paste (replace `YOUR_BUCKET` with your actual bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataLakeAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET",
        "arn:aws:s3:::YOUR_BUCKET/*"
      ]
    }
  ]
}
```

5. Click **Next** → Policy name: `emr-s3-access` → **Create policy**

**Step 1.6: Add Inline Policy — Glue Catalog Access**

1. Click **Add permissions** → **Create inline policy** again
2. Click **JSON** tab, paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlueCatalogAccess",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions",
        "glue:CreateTable",
        "glue:UpdateTable"
      ],
      "Resource": "*"
    }
  ]
}
```

3. Policy name: `emr-glue-access` → **Create policy**

**Step 1.7: Add Inline Policy — CloudWatch Logs**

1. Click **Add permissions** → **Create inline policy** again
2. Click **JSON** tab, paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

3. Policy name: `emr-cloudwatch-access` → **Create policy**

**Step 1.8: Validate Result**

**Expected Outcome:** Role `handson-emr-serverless-role` has 3 inline policies:
- `emr-s3-access`
- `emr-glue-access`
- `emr-cloudwatch-access`

**Troubleshooting:**
- "Invalid JSON": Paste into jsonlint.com to validate — check for missing commas/brackets
- "Access Denied creating role": Your IAM user needs `iam:CreateRole` + `iam:PutRolePolicy`
- "Principal is invalid": The service must be `emr-serverless.amazonaws.com` — not `emr.amazonaws.com`

**📸 Screenshot 1d:** Role details showing all 3 inline policies attached

---

#### Step 2 — Upload Spark Script to S3

**Prerequisites Check:**
- ✅ Required permissions: `s3:PutObject`
- ✅ S3 bucket exists
- ✅ `src/spark_job.py` exists locally in the project folder

**Step 2.1: Navigate and Verify**
1. Search bar → **S3** → click your data lake bucket
2. **Expected View:** Bucket contents with existing folders

**Step 2.2: Create scripts/ Folder**
1. Click **Create folder**
2. Folder name: `scripts`
3. Leave encryption as default
4. Click **Create folder**

**Step 2.3: Upload the Spark Script**
1. Click on the `scripts/` folder
2. Click **Upload** (orange button)
3. Click **Add files**
4. Navigate to your project directory:
   `D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.4_spark_emr\src\`
5. Select `spark_job.py` → Click **Open**
6. Click **Upload**

**Step 2.4: Validate Result**

**Expected Outcome:**
- S3 path: `s3://YOUR_BUCKET/scripts/spark_job.py`
- File size: ~3 KB
- Status: Upload succeeded

**Troubleshooting:**
- "Access Denied": Your IAM user needs `s3:PutObject` on the bucket
- File not visible: Refresh the page

**📸 Screenshot 2a:** S3 showing `scripts/spark_job.py` uploaded successfully

---

#### Step 3 — Create EMR Serverless Application

**Prerequisites Check:**
- ✅ Required permissions: `emr-serverless:CreateApplication`
- ✅ Services enabled: Amazon EMR available in us-east-1
- ✅ Region: us-east-1 selected

**Step 3.1: Navigate and Verify**
1. Search bar → **EMR** → click **Amazon EMR**
2. Left sidebar → **EMR Serverless**
3. **Expected View:** EMR Serverless page with **Create application** button
4. **If Different:** Make sure you clicked EMR Serverless, not EMR on EC2 (Clusters)

**📸 Screenshot 3a:** EMR Serverless landing page before creating application

**Step 3.2: Make Selections — Application Type**

**Decision Point 1:** Application type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Spark** | Distributed data processing, ML, ETL | ✅ Our spark_job.py is PySpark |
| Hive | SQL-based batch processing | ❌ Not used |

1. Click **Create application**
2. Select **Spark**

**Step 3.3: Configure Application Details**

**Decision Point 2:** Setup option
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Default settings | Quick start, no customization | ❌ We need custom capacity |
| **Custom settings** | Control driver/executor resources | ✅ Set initial + max capacity |

1. Select **Use custom settings**

**Fill in the form:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Application name | `handson-spark` | Matches terraform/main.tf |
| EMR release | **emr-6.15.0** | Latest stable with Spark 3.4 |
| Application type | Spark | Already selected |

**📸 Screenshot 3b:** Application name and release filled in

**Step 3.4: Configure Initial Capacity**

Initial capacity pre-warms workers so the first job starts faster (optional but useful):

1. Click **Add worker type** or expand **Initial capacity** section
2. Worker type: **Driver**

| Field | Value | Why |
|-------|-------|-----|
| Worker count | `1` | 1 driver per job |
| CPU | `2 vCPU` | Matches IAM role + terraform config |
| Memory | `4 GB` | Sufficient for coordinating 50GB dataset |

**Decision Point 3:** Initial capacity — to set or not?
| Option | Behavior | For This Project |
|--------|----------|-----------------|
| Set initial capacity | Workers pre-warmed, faster first job | ✅ Reduces cold start |
| Skip | Workers provisioned on demand per job | ❌ Adds ~30s cold start |

**Step 3.5: Configure Maximum Capacity**

| Field | Value | Why |
|-------|-------|-----|
| CPU | `20 vCPU` | Max auto-scale ceiling |
| Memory | `40 GB` | 20 vCPU × 2 GB/vCPU ratio |

This is the hard cap — EMR Serverless will never exceed this even if data is larger.

**Step 3.6: Configure Auto-Stop**

1. Expand **Application auto-stop** section
2. Enable: ✅ **Automatically stop the application**
3. **Idle timeout:** `15` minutes

| Field | Value | Explanation |
|-------|-------|-------------|
| Auto-stop enabled | ✅ Yes | Stops billing after 15 min idle |
| Idle timeout | `15 minutes` | Application stops if no jobs run |

> **Important:** Auto-stop does NOT delete the application — it just stops it.
> A stopped application can be started again in seconds. You only pay when STARTED.

**Step 3.7: Tags**
1. Scroll to **Tags** section
2. Add: Key = `Project`, Value = `handson`

**Step 3.8: Create the Application**
1. Review all settings
2. Click **Create application**
3. **Expected Outcome:** Application created with Status = **Created** → **Started**
   (starts automatically after creation)

**Troubleshooting:**
- "Limit exceeded": Account has too many EMR Serverless applications — delete unused ones
- Status stays "Creating" > 2 min: Refresh. If still stuck, check CloudTrail for errors

**📸 Screenshot 3c:** Application `handson-spark` Status = **Started**

---

#### Step 4 — Submit Spark Job

**Prerequisites Check:**
- ✅ Application `handson-spark` Status = **Started**
- ✅ IAM role `handson-emr-serverless-role` created with all 3 inline policies
- ✅ `scripts/spark_job.py` uploaded to S3
- ✅ `raw/orders/` has CSV data in S3

**Step 4.1: Navigate to Submit Job**
1. Click on application name **handson-spark**
2. Click **Submit job** (orange button)
3. **Expected View:** Job submission form

**📸 Screenshot 4a:** Submit job form — empty before filling

**Step 4.2: Configure Job Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Job name | `handson-order-analysis` | Descriptive name |
| Runtime role | `handson-emr-serverless-role` | The IAM role we created |
| Script location | `s3://YOUR_BUCKET/scripts/spark_job.py` | Full S3 path to spark_job.py |

**Step 4.3: Configure Script Arguments**

In the **Script arguments** field, add these two arguments on separate lines
(or as a comma-separated list depending on console version):

```
--input
s3://YOUR_BUCKET/raw/orders/
--output
s3://YOUR_BUCKET/processed/spark/
```

**What these do:**
- `--input`: the path spark_job.py reads CSV files from
- `--output`: the path Parquet output will be written to

**Step 4.4: Configure Spark Properties (Optional)**

Expand **Spark properties** and add:

| Key | Value | Why |
|-----|-------|-----|
| `spark.executor.cores` | `2` | vCPUs per executor |
| `spark.executor.memory` | `4g` | RAM per executor |
| `spark.sql.adaptive.enabled` | `true` | Enable AQE (already in script but belt+suspenders) |

**Step 4.5: Configure Job Logs**

1. Expand **Job logs** section
2. Enable: ✅ **Publish logs to Amazon S3**
3. S3 log location: `s3://YOUR_BUCKET/logs/`

This lets you read Spark driver/executor logs after the job completes.

**Step 4.6: Submit the Job**
1. Review all settings
2. Click **Submit job**
3. **Expected Outcome:** Job appears in Job runs tab with status: **Pending** → **Running**

**📸 Screenshot 4b:** Job `handson-order-analysis` showing Status = **Running**

---

#### Step 5 — Monitor the Job

**Prerequisites Check:**
- ✅ Job submitted and in Running or Pending state

**Step 5.1: Watch Job Status**
1. You should be on the **Job runs** tab of application `handson-spark`
2. **Expected View:** Job `handson-order-analysis` with a status badge

| Status | Meaning | Action |
|--------|---------|--------|
| **Pending** | Waiting for workers to provision | Wait ~30–60s |
| **Running** | Spark job executing | Wait (typical: 3–10 min) |
| **Success** | ✅ Job completed | Proceed to verify output |
| **Failed** | ❌ Error occurred | Check logs (Step 5.3) |

**Step 5.2: View Job Metrics**
1. Click on the job run name `handson-order-analysis`
2. **Expected View:** Job details page with:
   - Duration
   - vCPU-hours used
   - Memory GB-hours used
   - State transition timeline

**📸 Screenshot 5a:** Job details showing vCPU-hours and Status = **Success**

**Step 5.3: View Spark Logs (if needed)**
1. On the job details page, scroll to **Logs** section
2. Click **Driver stdout** or **Driver stderr**
3. **Expected View (stdout):**
```
Spark version: 3.4.x
Reading from: s3://YOUR_BUCKET/raw/orders/
Total records: 1000
...
Output written to: s3://YOUR_BUCKET/processed/spark/
Product monthly records: 15
Customer CLV records: 200
```
4. **If Failed:** Check **Driver stderr** — look for Python tracebacks

**Troubleshooting:**
- "FileNotFoundException: s3://..." → Check your `--input` path has CSV files
- "Access Denied" in logs → IAM role missing `s3:GetObject` on input bucket
- "Python import error" → EMR 6.15.0 has PySpark 3.4 built in — no pip install needed
- Job stuck in Pending > 5 min → Application may need to be Started manually

**📸 Screenshot 5b:** Spark driver stdout showing successful completion output

---

#### Step 6 — Verify Output in S3

**Prerequisites Check:**
- ✅ Job status = **Success**

**Step 6.1: Navigate to S3 Output**
1. Search bar → **S3** → your data lake bucket
2. Navigate to `processed/spark/`
3. **Expected View:** Two folders:
   - `product_monthly/`
   - `customer_clv/`

**Step 6.2: Verify Product Monthly Output**
1. Click `product_monthly/`
2. **Expected View:** Hive-style partitioned structure:
```
product_monthly/
  year=2024/
    month=1/
      part-00000-abc.snappy.parquet
    month=2/
      part-00000-abc.snappy.parquet
```
3. Click on a `.parquet` file → note the file size (typically 10–100 KB per partition)

**Step 6.3: Verify Customer CLV Output**
1. Navigate to `customer_clv/`
2. **Expected View:** Flat Parquet files (no year/month partitioning):
```
customer_clv/
  part-00000-abc.snappy.parquet
  _SUCCESS
```

**Step 6.4: Validate Result**

**Expected Outcome:**
- `product_monthly/` contains Parquet files partitioned by year and month
- `customer_clv/` contains flat Parquet files
- Files have `.snappy.parquet` extension (Snappy compressed — default)
- Both folders have a `_SUCCESS` marker file

**Troubleshooting:**
- No output files: Job may have failed — check Step 5.3 logs
- Output in wrong path: Compare exact path in `--output` argument with what you see in S3
- Empty files: Input CSV may have had no valid rows after cleaning

**📸 Screenshot 6a:** S3 showing `product_monthly/year=2024/month=1/` with Parquet files
**📸 Screenshot 6b:** S3 showing `customer_clv/` with Parquet files

---

### Console Method Summary

| Step | Resource Created | Name |
|------|----------------|------|
| Step 1 | IAM Role + 3 inline policies | `handson-emr-serverless-role` |
| Step 2 | S3 object | `scripts/spark_job.py` |
| Step 3 | EMR Serverless Application | `handson-spark` |
| Step 4 | EMR Serverless Job Run | `handson-order-analysis` |
| Step 5 | (Monitor only) | — |
| Step 6 | S3 Parquet output | `processed/spark/` |

---

## 5B. AWS CLI Method

> All commands use PowerShell syntax (Windows).
> Run from the project root directory:
> `D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.4_spark_emr`

---

### Phase 0 — Set Variables

```powershell
$REGION   = "us-east-1"
$ACCOUNT  = aws sts get-caller-identity --query Account --output text
$BUCKET   = "handson-data-lake-$ACCOUNT"   # adjust to your actual bucket name
$APP_NAME = "handson-spark"
$ROLE_NAME = "handson-emr-serverless-role"

Write-Host "Account : $ACCOUNT"
Write-Host "Bucket  : $BUCKET"
Write-Host "Region  : $REGION"

# Verify credentials
aws sts get-caller-identity
# Expected: UserId, Account, Arn
```

---

### Phase 1 — Create IAM Role for EMR Serverless

```powershell
# Step 1.1 — Write trust policy to temp file
@'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "emr-serverless.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
'@ | Out-File -FilePath "$env:TEMP\emr-trust.json" -Encoding utf8

# Step 1.2 — Create the IAM role
aws iam create-role `
  --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\emr-trust.json" `
  --description "EMR Serverless execution role"

# Expected output:
# {
#   "Role": {
#     "RoleName": "handson-emr-serverless-role",
#     "Arn": "arn:aws:iam::123456789012:role/handson-emr-serverless-role",
#     "AssumeRolePolicyDocument": { ... }
#   }
# }

# Get role ARN for later use
$ROLE_ARN = aws iam get-role `
  --role-name $ROLE_NAME `
  --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"
```

```powershell
# Step 1.3 — Add S3 inline policy
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataLakeAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::$BUCKET",
        "arn:aws:s3:::$BUCKET/*"
      ]
    }
  ]
}
"@ | Out-File -FilePath "$env:TEMP\emr-s3-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name $ROLE_NAME `
  --policy-name "emr-s3-access" `
  --policy-document "file://$env:TEMP\emr-s3-policy.json"

# Step 1.4 — Add Glue inline policy
@'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlueCatalogAccess",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase","glue:GetTable","glue:GetPartitions",
        "glue:CreateTable","glue:UpdateTable"
      ],
      "Resource": "*"
    }
  ]
}
'@ | Out-File -FilePath "$env:TEMP\emr-glue-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name $ROLE_NAME `
  --policy-name "emr-glue-access" `
  --policy-document "file://$env:TEMP\emr-glue-policy.json"

# Step 1.5 — Add CloudWatch Logs inline policy
@'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup","logs:CreateLogStream",
        "logs:PutLogEvents","logs:DescribeLogGroups","logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
'@ | Out-File -FilePath "$env:TEMP\emr-logs-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name $ROLE_NAME `
  --policy-name "emr-cloudwatch-access" `
  --policy-document "file://$env:TEMP\emr-logs-policy.json"

# Step 1.6 — Verify all 3 inline policies attached
aws iam list-role-policies --role-name $ROLE_NAME
# Expected: {"PolicyNames": ["emr-s3-access","emr-glue-access","emr-cloudwatch-access"]}
```

---

### Phase 2 — Upload Spark Script to S3

```powershell
# Upload spark_job.py to scripts/ prefix
aws s3 cp src\spark_job.py "s3://$BUCKET/scripts/spark_job.py"
# Expected: upload: src\spark_job.py to s3://handson-data-lake-.../scripts/spark_job.py

# Verify upload
aws s3 ls "s3://$BUCKET/scripts/"
# Expected: spark_job.py listed with file size ~3 KB

$SCRIPT_S3 = "s3://$BUCKET/scripts/spark_job.py"
Write-Host "Script at: $SCRIPT_S3"
```

---

### Phase 3 — Create EMR Serverless Application

```powershell
# Create the EMR Serverless application
$APP_ID = aws emr-serverless create-application `
  --name $APP_NAME `
  --type "SPARK" `
  --release-label "emr-6.15.0" `
  --initial-capacity '{
    "Driver": {
      "workerCount": 1,
      "workerConfiguration": {
        "cpu": "2 vCPU",
        "memory": "4 GB"
      }
    }
  }' `
  --maximum-capacity '{
    "cpu": "20 vCPU",
    "memory": "40 GB"
  }' `
  --auto-stop-configuration '{
    "enabled": true,
    "idleTimeoutMinutes": 15
  }' `
  --tags "Project=handson" `
  --query "applicationId" --output text

Write-Host "Application ID: $APP_ID"
# Expected: app-XXXXXXXXXXXXXXXXXXXXXXXX

# Wait for application to reach CREATED state
Start-Sleep -Seconds 10
aws emr-serverless get-application `
  --application-id $APP_ID `
  --query "application.{Name:name,State:state,ReleaseLabel:releaseLabel}"
# Expected: {"Name":"handson-spark","State":"CREATED","ReleaseLabel":"emr-6.15.0"}
```

---

### Phase 4 — Start EMR Serverless Application

```powershell
# IMPORTANT: Application must be STARTED before submitting jobs
aws emr-serverless start-application --application-id $APP_ID

# Poll until STARTED
Write-Host "Waiting for application to start..."
for ($i = 0; $i -lt 20; $i++) {
  $STATE = aws emr-serverless get-application `
    --application-id $APP_ID `
    --query "application.state" --output text
  Write-Host "State: $STATE"
  if ($STATE -eq "STARTED") { break }
  if ($STATE -eq "STOPPED")  { Write-Host "ERROR: Start failed"; break }
  Start-Sleep -Seconds 10
}
# Expected final state: STARTED
```

---

### Phase 5 — Submit Spark Job

```powershell
$INPUT_PATH  = "s3://$BUCKET/raw/orders/"
$OUTPUT_PATH = "s3://$BUCKET/processed/spark/"
$LOG_PATH    = "s3://$BUCKET/logs/"

$JOB_RUN_ID = aws emr-serverless start-job-run `
  --application-id $APP_ID `
  --execution-role-arn $ROLE_ARN `
  --name "handson-order-analysis" `
  --job-driver "{
    `"sparkSubmit`": {
      `"entryPoint`": `"$SCRIPT_S3`",
      `"entryPointArguments`": [
        `"--input`", `"$INPUT_PATH`",
        `"--output`", `"$OUTPUT_PATH`"
      ],
      `"sparkSubmitParameters`": `"--conf spark.executor.cores=2 --conf spark.executor.memory=4g`"
    }
  }" `
  --configuration-overrides "{
    `"monitoringConfiguration`": {
      `"s3MonitoringConfiguration`": {
        `"logUri`": `"$LOG_PATH`"
      }
    }
  }" `
  --query "jobRunId" --output text

Write-Host "Job Run ID: $JOB_RUN_ID"
# Expected: jr-XXXXXXXXXXXXXXXXXXXXXXXX
```

---

### Phase 6 — Monitor Job Status

```powershell
# Poll job until SUCCESS or FAILED
Write-Host "Monitoring job $JOB_RUN_ID ..."
for ($i = 0; $i -lt 40; $i++) {
  $STATUS = aws emr-serverless get-job-run `
    --application-id $APP_ID `
    --job-run-id $JOB_RUN_ID `
    --query "jobRun.state" --output text
  Write-Host "[$i] Job state: $STATUS"

  if ($STATUS -eq "SUCCESS") {
    Write-Host "✅ Job completed successfully!"
    break
  }
  if ($STATUS -eq "FAILED") {
    Write-Host "❌ Job failed — check logs!"
    break
  }
  Start-Sleep -Seconds 15
}

# Get full job details after completion
aws emr-serverless get-job-run `
  --application-id $APP_ID `
  --job-run-id $JOB_RUN_ID `
  --query "jobRun.{State:state,CreatedAt:createdAt,UpdatedAt:updatedAt}"
# Expected: {"State": "SUCCESS", ...}
```

---

### Phase 7 — Read Spark Logs from S3

```powershell
# List log files for this job run
aws s3 ls "s3://$BUCKET/logs/applications/$APP_ID/jobs/$JOB_RUN_ID/" --recursive |
  Select-Object -Last 10
# Expected: stdout, stderr files under driver/ and executor/ folders

# Download and read driver stdout (shows print() output from spark_job.py)
aws s3 cp "s3://$BUCKET/logs/applications/$APP_ID/jobs/$JOB_RUN_ID/SPARK_DRIVER/stdout.gz" `
  "$env:TEMP\spark_stdout.gz"
# Decompress and read
Expand-Archive -Path "$env:TEMP\spark_stdout.gz" -DestinationPath "$env:TEMP\" -Force 2>$null
# Or use: (Get-Content "$env:TEMP\spark_stdout.gz" -Raw) — works for small files

# Expected stdout content:
# Spark version: 3.4.x
# Reading from: s3://YOUR_BUCKET/raw/orders/
# Total records: 1000
# root
#  |-- order_id: string (nullable = true)
#  |-- customer_id: string (nullable = true)
#  |-- product: string (nullable = true)
#  |-- amount: double (nullable = true)
#  |-- order_date: date (nullable = true)
# Output written to: s3://YOUR_BUCKET/processed/spark/
# Product monthly records: 15
# Customer CLV records: 200
```

---

### Phase 8 — Verify Output Files in S3

```powershell
# Check product_monthly output (should have year=/month= partitions)
aws s3 ls "s3://$BUCKET/processed/spark/product_monthly/" --recursive
# Expected:
# processed/spark/product_monthly/year=2024/month=1/part-00000-abc.snappy.parquet
# processed/spark/product_monthly/year=2024/month=2/part-00000-abc.snappy.parquet

# Check customer_clv output (flat parquet)
aws s3 ls "s3://$BUCKET/processed/spark/customer_clv/"
# Expected:
# part-00000-abc.snappy.parquet
# _SUCCESS

# Count total Parquet files
$PARQUET_COUNT = (aws s3 ls "s3://$BUCKET/processed/spark/" --recursive |
  Select-String ".parquet").Count
Write-Host "Total Parquet output files: $PARQUET_COUNT"
# Expected: > 0
```

---

## 6. Code Deep Dive

### `src/spark_job.py` — Complete Line-by-Line Explanation

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
```
- `SparkSession` — the entry point for all Spark operations. Only one per JVM.
- `functions as F` — all built-in Spark SQL functions (col, count, sum, avg, etc.)
- `Window` — for window/analytical functions (running totals, rankings)

---

```python
spark = SparkSession.builder \
    .appName("OrderAnalysis") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()
```
- `.appName("OrderAnalysis")` — shown in the Spark UI and logs for identification
- `spark.sql.adaptive.enabled = true` — **Adaptive Query Execution (AQE)**:
  Spark re-optimizes the query plan at runtime based on actual data statistics.
  Without it, Spark uses estimates that can be wildly wrong for skewed data.
- `spark.sql.adaptive.coalescePartitions.enabled = true` — after a shuffle
  (like groupBy), merge small output partitions into fewer, larger ones.
  Example: 200 tiny partitions of 1 KB each → coalesced into 3 partitions of 70 KB.
  Fewer tasks = less overhead = faster job.
- `.getOrCreate()` — creates a new session or returns existing one.
  Safe to call multiple times — essential for testing where session may already exist.

---

```python
spark.sparkContext.setLogLevel("WARN")
```
- Suppresses INFO-level messages from Spark internals.
- Without this, logs are flooded with internal Spark messages.
- WARN level shows only warnings and errors — keeps your print() output readable.

---

```python
df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(input_path)
```
- `spark.read.csv(path)` — reads ALL CSV files at `input_path` in parallel.
  If `input_path` is a folder, Spark reads every `.csv` file in it.
  S3 is treated as a distributed filesystem — each file split into ~128MB chunks.
- `.option("header", "true")` — first row of each CSV is the column header.
  Without this, columns would be named `_c0`, `_c1`, `_c2`...
- `.option("inferSchema", "true")` — Spark reads a sample of rows and guesses types.
  `amount` → double, `order_date` → string (Spark won't auto-parse dates).
  Cost: requires an extra scan pass. Fine for learning; in production, define schema explicitly.

---

```python
df_clean = df \
    .dropna(subset=["order_id", "amount"]) \
    .withColumn("order_date", F.to_date("order_date")) \
    .withColumn("year",  F.year("order_date")) \
    .withColumn("month", F.month("order_date")) \
    .withColumn("amount", F.col("amount").cast("double")) \
    .dropDuplicates(["order_id"])
```
- `.dropna(subset=["order_id","amount"])` — drop rows where these columns are null.
  `order_id` is the primary key — rows without it are meaningless.
  `amount` is required for revenue calculations — null amount = broken row.
  We don't drop rows with null `customer_id` — they'd still count in product aggregates.
- `F.to_date("order_date")` — converts string "2024-01-15" to a proper Date type.
  Allows `.year()` and `.month()` extractions. Strings can't be sorted or compared as dates.
- `F.year("order_date")` and `F.month("order_date")` — extract year/month integers.
  These become partition columns in the output (`year=2024/month=1/`).
- `.cast("double")` — even though inferSchema guesses double, explicit cast ensures safety.
  Why double not float? Double = 64-bit precision. Float = 32-bit (can cause rounding errors
  at high values like $9,999,999.99). Always use double for monetary amounts in Spark.
- `.dropDuplicates(["order_id"])` — idempotent: if the job runs twice on the same input
  (e.g., after a failure), duplicate orders won't be counted twice.
  Using only `["order_id"]` (not all columns) means: keep the first occurrence by order_id.

---

```python
df_product_monthly = df_clean \
    .groupBy("year", "month", "product") \
    .agg(
        F.count("order_id").alias("order_count"),
        F.sum("amount").alias("total_revenue"),
        F.avg("amount").alias("avg_order_value"),
        F.countDistinct("customer_id").alias("unique_customers"),
    ) \
    .withColumn("total_revenue", F.round("total_revenue", 2))
```
- `.groupBy("year", "month", "product")` — three-level grouping key.
  Every unique combination of (year, month, product) gets one output row.
  For 12 months × 5 products = 60 output rows maximum.
- `F.count("order_id")` — counts non-null order_ids per group.
  Equivalent to SQL `COUNT(order_id)`. Fast — each executor counts its partition, then merge.
- `F.sum("amount")` — sums amounts. Distributed: each executor sums its partition,
  then Driver sums those subtotals. No full data movement needed.
- `F.avg("amount")` — equivalent to sum/count. Same distribution pattern.
- `F.countDistinct("customer_id")` — **expensive operation**.
  Counts unique customer_ids per group. Requires a shuffle + HyperLogLog estimation.
  Cannot be done locally per partition — all customer_ids for a group must be co-located.
  Use sparingly on large datasets (prefer approximate_count_distinct for > 1B rows).
- `F.round("total_revenue", 2)` — round to 2 decimal places.
  Without this, floating-point math gives results like $1259.5999999998.

---

```python
df_clv = df_clean \
    .groupBy("customer_id") \
    .agg(
        F.count("order_id").alias("total_orders"),
        F.sum("amount").alias("lifetime_value"),
        F.min("order_date").alias("first_order"),
        F.max("order_date").alias("last_order"),
    ) \
    .withColumn("lifetime_value", F.round("lifetime_value", 2))
```
- Groups by `customer_id` — one row per customer.
- `total_orders` — how many orders ever placed. Key metric for customer segmentation.
- `lifetime_value` — total spend from first to last order.
  Marketing uses this to identify high-value customers, target promotions, predict churn.
- `first_order` / `last_order` — date range of activity.
  `last_order` close to today = active customer. Far in past = churned customer.
- **Business use:** Sort by `lifetime_value DESC` → top 10% of customers by spend.

---

```python
window = Window.partitionBy("customer_id").orderBy("order_date")
df_running = df_clean \
    .withColumn("running_total", F.sum("amount").over(window))
```
- `Window.partitionBy("customer_id")` — within each customer's set of orders,
  apply the window function independently.
- `.orderBy("order_date")` — process orders in chronological order per customer.
- `F.sum("amount").over(window)` — running cumulative sum.
  Row 1: $29.99, Row 2: $29.99 + $49.99 = $79.98, Row 3: $79.98 + $19.99 = $99.97...
- **In distributed computing:** Window functions require a shuffle — all rows for one
  customer must be on the same executor. Expensive for many customers.
- **Note:** `df_running` is computed but not written to S3 in this script.
  It demonstrates the concept. You could add a write call to save it.

---

```python
df_product_monthly \
    .write.mode("overwrite") \
    .partitionBy("year", "month") \
    .parquet(f"{output_path}/product_monthly/")
```
- `.write.mode("overwrite")` — if output path already has files, delete them first.
  Safe to re-run the job — no duplicate data accumulation.
  Alternative: `"append"` = adds new files without deleting existing ones.
- `.partitionBy("year", "month")` — creates Hive-style directory structure:
  `product_monthly/year=2024/month=1/part-00000.parquet`
  When Athena queries `WHERE year=2024 AND month=1`, it reads only that folder.
  Without partitioning: Athena scans ALL data for every query = expensive.
- `.parquet(path)` — writes compressed columnar Parquet format (Snappy by default).
  Parquet is 3–10x smaller than CSV. Athena charges per byte scanned — smaller = cheaper.

---

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    main(args.input, args.output)
```
- `argparse` — parses `--input` and `--output` from the command line.
  When submitted to EMR via `entryPointArguments`, these args are passed to the script.
- `required=True` — job fails immediately with clear error if either arg is missing.
  Better UX than `sys.argv[1]` which gives cryptic `IndexError`.
- `if __name__ == "__main__"` — allows the script to be imported as a module for testing
  without immediately running `main()`. Standard Python pattern.

### Common Mistakes and Fixes

| Mistake | Error / Symptom | Fix |
|---------|----------------|-----|
| Wrong trust principal | "Principal is invalid" in IAM | Use `emr-serverless.amazonaws.com` |
| App not Started | "Application not in STARTED state" | Call `start-application` before job |
| Missing `--input` arg | `argparse` error in logs | Check `entryPointArguments` JSON format |
| S3 path missing trailing `/` | Spark reads file not folder | Use `s3://bucket/raw/orders/` |
| inferSchema on large file | Job very slow at start | Define schema explicitly for production |
| `mode("append")` re-runs | Duplicate data in output | Use `mode("overwrite")` |
| Float for money | `1259.5999998` instead of `1259.60` | Always `cast("double")` + `round(col, 2)` |

---

## 7. Verification & Validation

### 7.1 AWS Console Verification

| Resource | Navigation Path | Expected State |
|----------|----------------|---------------|
| IAM Role | IAM → Roles → `handson-emr-serverless-role` | Exists, 3 inline policies |
| S3 Script | S3 → bucket → `scripts/spark_job.py` | File present, ~3 KB |
| EMR App | EMR → EMR Serverless → `handson-spark` | Status = **Started** or **Stopped** |
| Job Run | App → Job runs tab | `handson-order-analysis` State = **Success** |
| S3 Output 1 | S3 → `processed/spark/product_monthly/` | Parquet files with year=/month= partitions |
| S3 Output 2 | S3 → `processed/spark/customer_clv/` | Parquet files present |
| Spark Logs | Job run → Logs → Driver stdout | Shows "Output written to..." |

### 7.2 Full CLI Verification Script (PowerShell)

```powershell
Write-Host "=== VERIFICATION: Project 9.4 Spark EMR Serverless ===" -ForegroundColor Cyan

# Assumes $APP_ID, $JOB_RUN_ID, $BUCKET, $ROLE_NAME are set from Phase 0

# CHECK 1 — IAM role exists with 3 policies
Write-Host "`n[1] IAM Role policies..."
aws iam list-role-policies --role-name $ROLE_NAME `
  --query "PolicyNames"
# Expected: ["emr-s3-access","emr-glue-access","emr-cloudwatch-access"]

# CHECK 2 — Script exists in S3
Write-Host "`n[2] Spark script in S3..."
aws s3 ls "s3://$BUCKET/scripts/spark_job.py"
# Expected: file listed with size ~3 KB

# CHECK 3 — EMR Serverless application state
Write-Host "`n[3] EMR Serverless application..."
aws emr-serverless get-application `
  --application-id $APP_ID `
  --query "application.{Name:name,State:state,Release:releaseLabel}"
# Expected: {"Name":"handson-spark","State":"STARTED","Release":"emr-6.15.0"}

# CHECK 4 — Job run succeeded
Write-Host "`n[4] Job run status..."
aws emr-serverless get-job-run `
  --application-id $APP_ID `
  --job-run-id $JOB_RUN_ID `
  --query "jobRun.{State:state,Name:name}"
# Expected: {"State":"SUCCESS","Name":"handson-order-analysis"}

# CHECK 5 — product_monthly output exists
Write-Host "`n[5] product_monthly Parquet output..."
aws s3 ls "s3://$BUCKET/processed/spark/product_monthly/" --recursive |
  Select-String ".parquet"
# Expected: one or more .snappy.parquet files

# CHECK 6 — customer_clv output exists
Write-Host "`n[6] customer_clv Parquet output..."
aws s3 ls "s3://$BUCKET/processed/spark/customer_clv/"
# Expected: part-00000-*.snappy.parquet + _SUCCESS

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

### 7.3 End-to-End Health Check

```powershell
# Quick resubmit + verify cycle
Write-Host "Starting end-to-end test..."

# 1. Ensure app is STARTED
$STATE = aws emr-serverless get-application `
  --application-id $APP_ID --query "application.state" --output text
if ($STATE -ne "STARTED") {
  aws emr-serverless start-application --application-id $APP_ID
  Start-Sleep -Seconds 30
}
Write-Host "✅ Application STARTED"

# 2. Submit job
$NEW_JOB = aws emr-serverless start-job-run `
  --application-id $APP_ID `
  --execution-role-arn $ROLE_ARN `
  --name "verify-test" `
  --job-driver "{`"sparkSubmit`":{`"entryPoint`":`"s3://$BUCKET/scripts/spark_job.py`",`"entryPointArguments`":[`"--input`",`"s3://$BUCKET/raw/orders/`",`"--output`",`"s3://$BUCKET/processed/spark/`"]}}" `
  --query "jobRunId" --output text
Write-Host "✅ Job submitted: $NEW_JOB"

# 3. Wait for completion
for ($i=0; $i -lt 30; $i++) {
  $S = aws emr-serverless get-job-run --application-id $APP_ID `
       --job-run-id $NEW_JOB --query "jobRun.state" --output text
  if ($S -eq "SUCCESS" -or $S -eq "FAILED") { break }
  Start-Sleep -Seconds 15
}
Write-Host "✅ Final state: $S"

# 4. Count output files
$COUNT = (aws s3 ls "s3://$BUCKET/processed/spark/" --recursive |
          Select-String ".parquet").Count
Write-Host "✅ Parquet output files: $COUNT"
```

### 7.4 Expected Successful Outputs

```
IAM role:  handson-emr-serverless-role — 3 inline policies
S3 script: scripts/spark_job.py — ~3 KB
EMR App:   handson-spark — State=STARTED or STOPPED (not FAILED)
Job run:   handson-order-analysis — State=SUCCESS
Output 1:  processed/spark/product_monthly/year=YYYY/month=M/*.snappy.parquet
Output 2:  processed/spark/customer_clv/*.snappy.parquet + _SUCCESS
Logs:      "Output written to: s3://BUCKET/processed/spark/"
           "Product monthly records: N"
           "Customer CLV records: N"
```

### 7.5 Verification Checklist

- [ ] IAM role `handson-emr-serverless-role` exists
- [ ] Role has trust principal `emr-serverless.amazonaws.com`
- [ ] Role has 3 inline policies: emr-s3-access, emr-glue-access, emr-cloudwatch-access
- [ ] `scripts/spark_job.py` exists in S3 bucket
- [ ] EMR Serverless application `handson-spark` State = STARTED or STOPPED
- [ ] Application release = `emr-6.15.0`
- [ ] Job run `handson-order-analysis` State = SUCCESS
- [ ] `processed/spark/product_monthly/` contains Parquet files
- [ ] `processed/spark/customer_clv/` contains Parquet files + `_SUCCESS`
- [ ] Driver stdout log shows "Output written to..."

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During Job Execution

**When job is in Pending state (~30–60s):**
- EMR Serverless is allocating EC2 capacity in AWS-managed accounts
- This "cold start" happens because there are no pre-warmed workers
- If you set `initial_capacity`, this phase is shorter (~5–10s)
- Once workers are ready → transitions to Running

**When job is Running:**
- The Driver is executing your Python script
- Executors read CSV partitions from S3 in parallel
- Watch the job duration — a 1,000-row CSV should finish in < 2 minutes
- A 1 GB CSV on 1 shard might take 5–15 minutes

**When job completes:**
- State transitions to SUCCESS
- Workers are deallocated immediately — billing stops
- Application stays STARTED for 15 more minutes (auto-stop timer)
- After 15 min idle → application auto-stops → zero ongoing cost

### 8.2 Internal AWS Behavior

```
aws emr-serverless start-job-run
    │
    │ EMR Control Plane receives request
    ▼
EMR Serverless provisions Docker containers for Driver + Executors
(on AWS-managed EC2 fleet — you never see the machines)
    │
    │ Driver container starts, loads spark_job.py
    ▼
Driver reads args: input_path, output_path
Driver builds DAG (Directed Acyclic Graph of operations):
  Stage 1: Read CSV from S3, apply filters/casts (no shuffle)
  Stage 2: groupBy product/month → shuffle, then aggregate (shuffle)
  Stage 3: groupBy customer_id → shuffle, then aggregate (shuffle)
  Stage 4: Write Parquet to S3 (no shuffle)
    │
    │ Driver sends Stage 1 tasks to Executors
    ▼
Each Executor reads its assigned S3 partition (chunk of CSV)
Applies dropna, withColumn, dropDuplicates locally
    │
    │ Stage 1 complete → Stage 2 begins (SHUFFLE)
    ▼
Executors exchange partitions (shuffle write → shuffle read)
Now each Executor has all rows for its assigned products
Computes count, sum, avg, countDistinct
    │
    ▼
Driver collects result (small — 60 rows) + writes to S3 as Parquet
```

### 8.3 Why Parquet is Better Than CSV for Output

```
Same data, different format:
  CSV:     1,000,000 rows = 150 MB
  Parquet: 1,000,000 rows = 15 MB  (10x smaller)

Why?
  Columnar: data stored column-by-column, not row-by-row
  → Query SELECT product, SUM(amount) only reads 2 of 5 columns
  → CSV reads ALL columns even if you only need 2

  Compression: Snappy compresses repetitive values within columns
  → "Widget A" repeated 50,000 times compresses dramatically

Athena cost impact:
  Athena charges $5 per TB scanned
  CSV query:    $5 × 0.15 TB = $0.75 per query
  Parquet query: $5 × 0.015 TB = $0.075 per query
  → 10x cheaper to query Parquet
```

### 8.4 Billing Observations

- **Billing starts** when workers are allocated (Running state begins)
- **Billing stops** when workers are deallocated (job complete or app stopped)
- **Pending state** = NOT billed — you pay only for actual compute
- **Auto-stop** = application stops after 15 min idle → zero ongoing charges
- **Per-job cost** is tiny (~$0.07) — the real risk is forgetting the application exists
- **Check your bill:** Console → Billing → Cost Explorer → filter by EMR Serverless

### 8.5 Kinesis vs Glue vs EMR — When to Use Each

| Dimension | Kinesis (9.3) | Glue ETL (9.2) | EMR Serverless (9.4) |
|-----------|--------------|---------------|---------------------|
| Data arrival | Real-time (seconds) | Scheduled batch | On-demand batch |
| Dataset size | KB to MB per event | GB to TB | GB to TB+ |
| Processing | Per-record Lambda | Managed Spark | Custom Spark code |
| Control | Low | Medium | Full |
| Cost model | Per shard-hr | Per DPU-hr | Per vCPU-hr |
| Best for | Fraud, live dashboards | Simple ETL, no code | Complex ML, large scale |

---

## 9. Screenshots Guidance

### Before Implementation
| # | What to Capture | When |
|---|----------------|------|
| SS-01 | AWS Console with us-east-1 selected | Before starting |
| SS-02 | S3 bucket showing `raw/orders/` with CSV data | Phase 0 |
| SS-03 | IAM Roles list (before creating role) | Before Step 1 |
| SS-04 | EMR Serverless landing page (no applications yet) | Before Step 3 |

### During Setup (Console)
| # | What to Capture | When |
|---|----------------|------|
| SS-05 | IAM: custom trust policy form with emr-serverless.amazonaws.com | Step 1.2 |
| SS-06 | IAM: role just created (no policies yet) | Step 1.4 |
| SS-07 | IAM: role with all 3 inline policies attached | Step 1.8 |
| SS-08 | S3: spark_job.py in scripts/ folder | Step 2.3 |
| SS-09 | EMR Serverless: Create application form (name, release, capacity) | Step 3.3 |
| SS-10 | EMR Serverless: Submit job form filled in | Step 4.3 |

### After Deployment
| # | What to Capture | When |
|---|----------------|------|
| SS-11 | EMR Serverless application Status = Started | Step 3.8 |
| SS-12 | Job run Status = Running | Step 4.6 |
| SS-13 | Job run Status = Success + duration + vCPU-hours | Step 5.2 |
| SS-14 | Spark driver stdout showing "Output written to..." | Step 5.3 |
| SS-15 | S3: product_monthly/ with year=/month= partition folders | Step 6.2 |
| SS-16 | S3: customer_clv/ with Parquet files | Step 6.3 |
| SS-17 | EMR job metrics (vCPU-hours, memory GB-hours used) | Step 5.2 |

### CLI Method
| # | What to Capture | When |
|---|----------------|------|
| SS-18 | PowerShell: create-application output with application ID | Phase 3 |
| SS-19 | PowerShell: job polling loop showing SUCCESS | Phase 6 |
| SS-20 | PowerShell: s3 ls showing output Parquet files | Phase 8 |

**Total: 20 screenshots** — complete documentation portfolio for this project.

---

## 10. Cleanup Steps

> EMR Serverless applications do NOT automatically delete themselves.
> A stopped application costs $0/hr but occupies your account quota.
> Delete it after learning to keep things clean.

### 10.1 AWS Console Cleanup

1. **Stop application first** (required before delete):
   - EMR → EMR Serverless → `handson-spark`
   - Click **Actions** → **Stop application**
   - Wait for Status = **Stopped**

2. **Delete EMR Serverless application:**
   - Click **Actions** → **Delete application**
   - Confirm deletion

3. **Delete IAM role:**
   - IAM → Roles → `handson-emr-serverless-role`
   - Click **Delete** (this also deletes inline policies)
   - Type role name to confirm → Delete

4. **Delete S3 script:**
   - S3 → your bucket → `scripts/` → `spark_job.py`
   - Select → Delete → Confirm

5. **Optionally delete S3 output** (to avoid storage costs):
   - S3 → `processed/spark/` → select all → Delete

### 10.2 AWS CLI Cleanup (PowerShell)

```powershell
# Step 1 — Stop application
aws emr-serverless stop-application --application-id $APP_ID
Write-Host "Stopping application..."

# Poll until STOPPED
for ($i = 0; $i -lt 12; $i++) {
  $STATE = aws emr-serverless get-application `
    --application-id $APP_ID --query "application.state" --output text
  Write-Host "State: $STATE"
  if ($STATE -eq "STOPPED") { break }
  Start-Sleep -Seconds 10
}

# Step 2 — Delete application
aws emr-serverless delete-application --application-id $APP_ID
Write-Host "✅ Application deleted"

# Step 3 — Delete IAM inline policies
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-s3-access"
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-glue-access"
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-cloudwatch-access"

# Step 4 — Delete IAM role
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ IAM role deleted"

# Step 5 — Delete S3 script
aws s3 rm "s3://$BUCKET/scripts/spark_job.py"
Write-Host "✅ Script deleted from S3"

# Step 6 — Optionally delete output (comment out to keep)
aws s3 rm "s3://$BUCKET/processed/spark/" --recursive
Write-Host "✅ Output data deleted"

# Step 7 — Optionally delete logs
aws s3 rm "s3://$BUCKET/logs/" --recursive
Write-Host "✅ Logs deleted"
```

### 10.3 Verify Cleanup

```powershell
# Confirm application deleted
aws emr-serverless list-applications `
  --query "applications[?name=='handson-spark']"
# Expected: [] (empty list)

# Confirm IAM role deleted
aws iam get-role --role-name $ROLE_NAME 2>&1 |
  Select-String "NoSuchEntity"
# Expected: NoSuchEntityException

# Confirm no Parquet output remains
aws s3 ls "s3://$BUCKET/processed/spark/" 2>&1
# Expected: empty or "An error occurred (NoSuchKey)" if deleted
Write-Host "✅ Cleanup verified"
```

### 10.4 Cost Verification After Cleanup

```powershell
# Check EMR Serverless charges this month
aws ce get-cost-and-usage `
  --time-period "Start=$(Get-Date -Format 'yyyy-MM-01'),End=$(Get-Date -Format 'yyyy-MM-dd')" `
  --granularity DAILY `
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EMR"]}}' `
  --metrics UnblendedCost `
  --query "ResultsByTime[-1].Total.UnblendedCost.Amount"
# After cleanup: no new charges accrue
```

---

## Quick Reference Card

```
SETUP:
  Create IAM role: handson-emr-serverless-role
  Trust: emr-serverless.amazonaws.com
  Policies: emr-s3-access, emr-glue-access, emr-cloudwatch-access

UPLOAD SCRIPT:
  aws s3 cp src\spark_job.py s3://BUCKET/scripts/spark_job.py

CREATE APP:
  aws emr-serverless create-application --name handson-spark ...

START APP (required before job):
  aws emr-serverless start-application --application-id APP_ID

SUBMIT JOB:
  aws emr-serverless start-job-run \
    --application-id APP_ID \
    --execution-role-arn ROLE_ARN \
    --job-driver '{"sparkSubmit":{"entryPoint":"s3://BUCKET/scripts/spark_job.py",
                   "entryPointArguments":["--input","s3://BUCKET/raw/orders/",
                                          "--output","s3://BUCKET/processed/spark/"]}}'

MONITOR:
  aws emr-serverless get-job-run --application-id APP_ID --job-run-id JOB_RUN_ID

CHECK OUTPUT:
  aws s3 ls s3://BUCKET/processed/spark/ --recursive

CLEANUP:
  aws emr-serverless stop-application --application-id APP_ID
  aws emr-serverless delete-application --application-id APP_ID
  aws iam delete-role --role-name handson-emr-serverless-role

COST: ~$0.07/run | Always delete app after learning
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.4_spark_emr*
