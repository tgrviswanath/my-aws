# Complete Implementation Guide — Project 9.7: Data Quality Validation
# Great Expectations + AWS Lambda + SNS + EventBridge + S3

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 2–3 hours
**Cost:** ~$0.11/month | **Great Expectations Core is 100% free**

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
**Automated Data Quality Validation with Great Expectations, AWS Lambda, and SNS**

### Business / Problem Statement

Your analytics dashboard shows revenue of $1.2M last quarter. The CFO uses it for
board presentations. But last month someone discovered that negative order amounts
(`amount = -5.00`) had been silently summing into the revenue calculation for weeks.
The actual revenue was $1.1M. An embarrassing correction was needed.

**Root cause:** No data quality gate. Bad data entered the pipeline at ingestion,
flowed through Glue ETL, through dbt models, and straight into dashboards. Nobody
checked the data until the business noticed the numbers were wrong — weeks later.

**Goal:** Add automated quality gates at every stage of the pipeline:
- Validate data **immediately after Glue ETL completes** (via EventBridge → Lambda)
- If quality fails → **pipeline stops**, SNS alert sent, bad records quarantined in S3
- If quality passes → pipeline continues to dbt models → dashboard is trustworthy
- Full validation report saved to S3 for audit trail

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════════════
 INPUT — Data to validate
═══════════════════════════════════════════════════════════════════════════
Source:   S3: processed/orders/ (Parquet files after Glue ETL)
Schema:
  order_id     STRING   must be non-null, unique
  customer_id  STRING   must be non-null
  product      STRING   must be in known list (99% threshold)
  amount       DOUBLE   must be between 0.01 and 10,000.00
  order_date   STRING   must match YYYY-MM-DD format

═══════════════════════════════════════════════════════════════════════════
 VALIDATION CHECKS (src/validate_orders.py)
═══════════════════════════════════════════════════════════════════════════

Completeness checks:
  ✓ Row count >= 1          (table is not empty)
  ✓ order_id not null       (100% required)
  ✓ customer_id not null    (100% required)
  ✓ amount not null         (100% required)
  ✓ order_date not null     (100% required)

Uniqueness checks:
  ✓ order_id unique         (no duplicate orders)

Validity checks:
  ✓ amount between 0.01 and 10,000  (no negatives, no absurd values)
  ✓ product in known list            (99% threshold — 1% unknown allowed)
  ✓ order_date matches %Y-%m-%d      (valid date format)

Statistical checks:
  ✓ mean(amount) between 10.0 and 200.0  (sanity check on order value range)

═══════════════════════════════════════════════════════════════════════════
 OUTPUT — Three possible results
═══════════════════════════════════════════════════════════════════════════

RESULT 1 — ALL CHECKS PASS:
  Console output:
    ✅ PASSED | 10/10 checks passed | 1,000 rows
  Exit code: 0 (pipeline continues)
  S3 report: data-quality/reports/2024-01-15T14:30:00.json
  Action: dbt runs next, dashboard updated

RESULT 2 — ONE OR MORE CHECKS FAIL:
  Console output:
    ❌ FAILED | 7/10 checks passed | 1,000 rows
    ❌ order_id not null: FAILED (1 null found)
    ❌ order_id unique:   FAILED (duplicate: ORD-001)
    ❌ amount > 0:        FAILED (1 negative: -5.00)
  Exit code: 1 (pipeline STOPS — bad data blocked)
  S3 quarantine: quarantine/orders/2024-01-15/ (bad records isolated)
  SNS alert: "Data quality FAILED for 2024-01-15 pipeline run"
  Action: Engineer fixes source data and re-runs

RESULT 3 — VALIDATION ERROR (cannot read data):
  Console output: Exception with traceback
  Exit code: 1 (pipeline STOPS)
  SNS alert: "Data quality validator CRASHED"
  Action: Check S3 path, AWS credentials, Lambda timeout
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain why "fail fast" data quality gates prevent expensive data bugs
- [ ] Install and use Great Expectations Core locally
- [ ] Write completeness, uniqueness, validity, and statistical checks
- [ ] Understand the `mostly=` threshold parameter
- [ ] Run validation against both clean and dirty data
- [ ] Interpret the Great Expectations validation report
- [ ] Create an SNS topic and email subscription for alerts
- [ ] Set up an EventBridge rule to trigger Lambda after Glue job completion
- [ ] Understand the quarantine pattern for bad records
- [ ] Integrate data quality into an Airflow pipeline as a blocking task

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│              DATA QUALITY GATE PIPELINE                                  │
│                                                                          │
│  ┌────────────────────────┐                                              │
│  │  Glue ETL Job          │                                              │
│  │  handson-etl-job       │                                              │
│  │  Status: SUCCEEDED     │                                              │
│  └────────────┬───────────┘                                              │
│               │  EventBridge Rule: aws.glue → SUCCEEDED                  │
│               ▼                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Lambda: handson-data-quality-check                                │ │
│  │  Runtime: Python 3.11 | Timeout: 300s | Memory: 512 MB            │ │
│  │                                                                     │ │
│  │  validate_orders.main()                                            │ │
│  │    1. Load processed/orders/ from S3 → DataFrame                  │ │
│  │    2. Run Great Expectations suite (10 checks)                     │ │
│  │    3. Evaluate results                                              │ │
│  └───────────────────────┬────────────────────────────────────────────┘ │
│                          │                                               │
│          ┌───────────────┴──────────────────┐                          │
│          ▼ PASS                              ▼ FAIL                    │
│  ┌─────────────────────┐    ┌──────────────────────────────────────┐  │
│  │  Pipeline continues │    │  SNS Alert sent to email             │  │
│  │  (dbt runs next)    │    │  "Data quality FAILED"               │  │
│  │                     │    │                                       │  │
│  │  Report saved to:   │    │  Bad records → S3 quarantine/        │  │
│  │  data-quality/      │    │  Pipeline STOPS (exit code 1)        │  │
│  │  reports/*.json     │    └──────────────────────────────────────┘  │
│  └─────────────────────┘                                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  S3 BUCKET: handson-data-lake-ACCOUNT                            │  │
│  │  processed/orders/     ← input data (from Glue ETL)             │  │
│  │  quarantine/orders/    ← bad records (on FAIL)                   │  │
│  │  data-quality/reports/ ← validation JSON reports                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **AWS Lambda** | Runs Great Expectations validation on trigger | ✅ 1M invocations/month |
| **Amazon EventBridge** | Triggers Lambda when Glue job succeeds | ✅ Free (custom events) |
| **Amazon SNS** | Sends failure alert emails | ✅ 1M publishes/month |
| **Amazon S3** | Stores reports, quarantine records | ✅ 5 GB free |
| **Great Expectations Core** | Validation library (runs inside Lambda) | ✅ Free (open source) |
| **CloudWatch Logs** | Lambda execution logs | ✅ 5 GB free |

### Key Concepts Explained

**Fail Fast — why quality gates matter:**
```
Without quality gate:
  Bad data → Glue ETL → dbt models → Redshift → BI Dashboard
  Discovery: weeks later (business notices wrong numbers)
  Fix cost: $$$$ (data cleanup, customer trust damage, reprocessing)

With quality gate (this project):
  Bad data → Glue ETL → ❌ Quality check FAILS → pipeline STOPS
  Discovery: immediately (same pipeline run)
  Fix cost: $ (fix source, re-run ETL)

Rule: catch bad data as early in the pipeline as possible
```

**Great Expectations Expectation types:**
```python
# Completeness — data exists
expect_table_row_count_to_be_between(min_value=1)
expect_column_values_to_not_be_null("order_id")

# Uniqueness — no duplicates
expect_column_values_to_be_unique("order_id")

# Validity — values make sense
expect_column_values_to_be_between("amount", min_value=0.01, max_value=10000)
expect_column_values_to_be_in_set("product", value_set=["Widget A", ...])
expect_column_values_to_match_strftime_format("order_date", "%Y-%m-%d")

# Statistical — distribution is reasonable
expect_column_mean_to_be_between("amount", min_value=10.0, max_value=200.0)
```

**The `mostly=` threshold parameter:**
```python
# Strict: 100% of rows must pass (default)
expect_column_values_to_be_in_set("product", value_set=[...])

# Relaxed: 99% of rows must pass (allow 1% unknown)
expect_column_values_to_be_in_set("product", value_set=[...], mostly=0.99)

# Use mostly= when:
# - New products appear legitimately (not data errors)
# - Dimension table hasn't been updated yet
# - Historical data has some expected gaps
# Don't use mostly= for order_id (always 100% — no acceptable duplicates)
```

**Quarantine pattern:**
```
Bad records are NOT deleted — they are MOVED to quarantine/
Why? For audit + investigation:
  - Understand why data was bad
  - Fix source system
  - Potentially recover valid records

quarantine/orders/2024-01-15/
  bad_records.parquet  ← rows that failed any check
  validation_report.json ← which checks failed and why

Later: Engineer reviews quarantine, fixes upstream, deletes quarantine file
```

**EventBridge → Lambda trigger:**
```
EventBridge watches for AWS Glue events:
  source:      aws.glue
  detail-type: Glue Job State Change
  detail.state: SUCCEEDED
  detail.jobName: handson-etl-job

When Glue job succeeds → EventBridge fires → Lambda invoked automatically
No manual trigger needed — fully automated quality gate
```

### Best Practices Followed

- **Fail fast** — pipeline stops immediately on quality failure, no downstream corruption
- **`mostly=0.99`** on product — allows 1% new products without false positives
- **Quarantine, don't delete** — bad records preserved for investigation
- **Exit code 1 on failure** — enables Airflow/CI/CD to detect and stop pipeline
- **Statistical mean check** — catches subtle data shifts (not just nulls/negatives)
- **SNS alert** — team notified immediately, not hours later
- **Validation report to S3** — audit trail, shareable with data consumers

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia)
- S3 bucket with `processed/orders/` Parquet data (from Project 9.1/9.2)
- Email address for SNS alerts

### 3.2 IAM Permissions Required (for YOUR user)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["lambda:*"],
      "Resource": "arn:aws:lambda:us-east-1:*:function:handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:CreateTopic","sns:Subscribe","sns:Publish","sns:ListTopics"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["events:PutRule","events:PutTargets","events:DescribeRule"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole","iam:AttachRolePolicy","iam:PutRolePolicy",
                 "iam:PassRole","iam:GetRole","iam:DeleteRole"],
      "Resource": "arn:aws:iam::*:role/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": ["arn:aws:s3:::handson-data-lake-*","arn:aws:s3:::handson-data-lake-*/*"]
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) |
|------|---------|------------------|
| Python | >= 3.9 | `winget install Python.Python.3.11` |
| Great Expectations | 0.18.x | `pip install great-expectations` |
| pandas | latest | `pip install pandas` |
| pyarrow | latest | `pip install pyarrow` |
| s3fs | latest | `pip install s3fs` |
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |
| Git | latest | `winget install Git.Git` |

### 3.4 Environment Variables (PowerShell)

```powershell
$env:AWS_REGION        = "us-east-1"
$env:ACCOUNT           = aws sts get-caller-identity --query Account --output text
$env:DATA_LAKE_BUCKET  = "handson-data-lake-$env:ACCOUNT"
$env:SNS_TOPIC_NAME    = "handson-data-quality-alerts"
$env:LAMBDA_NAME       = "handson-data-quality-check"
$env:ALERT_EMAIL       = "your-email@example.com"   # change this

aws sts get-caller-identity
```

### 3.5 Estimated AWS Cost

| Resource | Cost |
|----------|------|
| Great Expectations Core | $0 (open source) |
| Lambda (< 1M invocations/month free tier) | $0 |
| SNS (< 1M publishes/month free tier) | $0 |
| EventBridge (first 5M events/month free) | $0 |
| S3 (reports + quarantine, < 5 GB) | ~$0.01/month |
| **Total for learning** | **~$0.01/month** |

> **Great Expectations is 100% free.** The only real cost is S3 storage for reports (~$0.01).
> Lambda, SNS, and EventBridge all fall within free tier at learning scale.

---

## 4. Project Folder Structure

```
project_9.7_data_quality/
│
├── GUIDE.md                  ← This comprehensive guide (you are here)
├── README.md                 ← Quick start and lessons learned
├── steps.md                  ← CLI commands reference (PowerShell)
├── steps_awsconsoleui.md     ← Console UI steps (improved template)
├── verify.md                 ← Verification checklist + commands
├── cost_estimate.md          ← Detailed cost breakdown
│
├── src/
│   └── validate_orders.py    ← Great Expectations validation script
│                                Runs locally OR inside Lambda
│                                10 checks: completeness, uniqueness, validity, stats
│
├── docs/
│   └── architecture.md       ← Pipeline diagram, fail-fast concept, GX concepts
│
└── terraform/
    └── main.tf               ← Lambda + SNS + EventBridge (reference — not in this guide)
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `src/validate_orders.py` | Main validation script. Reads S3 Parquet, runs 10 GX checks, prints report, exits 0 (pass) or 1 (fail). |
| `docs/architecture.md` | Quality gate flow, fail-fast principle, GX concepts |
| `terraform/main.tf` | Lambda function + SNS topic + EventBridge rule (reference only) |

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> The validation script runs **locally** (or in Lambda).
> Console steps cover the AWS infrastructure: SNS topic + EventBridge rule.
> After setup, you test the validation locally, then the cloud automation fires on Glue jobs.

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `sns:CreateTopic`, `events:PutRule`, `lambda:CreateFunction`
- ✅ Python + Great Expectations installed locally
- ✅ S3 bucket with `processed/orders/` Parquet data exists
- ✅ Region: us-east-1 selected

**Step 0.1: Verify S3 Input Data**
1. Search → **S3** → your data lake bucket
2. Navigate to `processed/orders/`
3. **Expected View:** Parquet files from Glue ETL
4. **If Empty:** Run Glue ETL (Project 9.2) first, or create test data locally

**📸 Screenshot P0:** S3 bucket showing `processed/orders/` with Parquet files

---

#### Step 1 — Create SNS Topic for Quality Alerts

**Prerequisites Check:**
- ✅ Required permissions: `sns:CreateTopic`, `sns:Subscribe`
- ✅ Services enabled: Amazon SNS (us-east-1)
- ✅ Email address to subscribe

**Step 1.1: Navigate and Verify**
1. Search bar → **SNS** → **Simple Notification Service**
2. Left sidebar → **Topics**
3. **Expected View:** Topics list
4. Click **Create topic**

**📸 Screenshot 1a:** SNS Topics list before creation

**Step 1.2: Make Selections — Topic Type**

**Decision Point 1:** Topic type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Standard** | Email alerts, high throughput | ✅ Quality alerts don't need ordering |
| FIFO | Ordered, exactly-once | ❌ Overkill for notifications |

1. Select **Standard**

**Step 1.3: Configure Topic Details**

| Field | Value |
|-------|-------|
| Name | `handson-data-quality-alerts` |
| Display name | `Data Quality Alerts` |

**Step 1.4: Create and Subscribe**
1. Click **Create topic**
2. On the topic page → click **Create subscription**
3. Fill in:

| Field | Value |
|-------|-------|
| Protocol | **Email** |
| Endpoint | your-email@example.com |

4. Click **Create subscription**
5. **Check your email inbox** → click the confirmation link
6. **Expected:** Subscription Status changes from `PendingConfirmation` → `Confirmed`

**Troubleshooting:**
- No confirmation email: Check spam folder. Wait 2 minutes then re-subscribe.
- `AccessDenied`: Your IAM user needs `sns:Subscribe`.

**📸 Screenshot 1b:** SNS topic `handson-data-quality-alerts` with email subscription Confirmed

---

#### Step 2 — Create EventBridge Rule (Glue → Lambda Trigger)

**Prerequisites Check:**
- ✅ Required permissions: `events:PutRule`, `events:PutTargets`
- ✅ Lambda function `handson-data-quality-check` must exist (created later or via Terraform)
- ✅ Services enabled: Amazon EventBridge

**Step 2.1: Navigate and Verify**
1. Search bar → **EventBridge** → click **Amazon EventBridge**
2. Left sidebar → **Rules** → click **Create rule**

**📸 Screenshot 2a:** EventBridge Rules list

**Step 2.2: Configure Rule Details**

| Field | Value |
|-------|-------|
| Name | `handson-glue-job-success` |
| Description | `Trigger data quality check after Glue ETL job succeeds` |
| Event bus | **default** |
| Rule type | **Rule with an event pattern** |

Click **Next**

**Step 2.3: Define Event Pattern**

**Decision Point 1:** Pattern method
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Use pattern form | Quick, UI-driven | ❌ Limited for Glue events |
| **Custom pattern (JSON)** | Full control | ✅ Glue state change events |

1. Select **Custom pattern (JSON editor)**
2. Paste this exact pattern:

```json
{
  "source": ["aws.glue"],
  "detail-type": ["Glue Job State Change"],
  "detail": {
    "jobName": ["handson-etl-job"],
    "state": ["SUCCEEDED"]
  }
}
```

**What each field means:**
- `source: ["aws.glue"]` — events from the AWS Glue service only
- `detail-type: ["Glue Job State Change"]` — only Glue job state events
- `detail.jobName` — only the specific Glue job we want to monitor
- `detail.state: ["SUCCEEDED"]` — only when the job succeeds (not starts or fails)

3. Click **Next**

**📸 Screenshot 2b:** EventBridge event pattern JSON filled in

**Step 2.4: Add Target (Lambda)**
1. Target type: **AWS service**
2. Target: **Lambda function**
3. Function: select **handson-data-quality-check**
4. Click **Next** → **Next** → **Create rule**

**Step 2.5: Validate Result**
**Expected Outcome:** Rule `handson-glue-job-success` Status = **Enabled**

**Troubleshooting:**
- "Lambda function not found": Create the Lambda first (Step 3 below)
- "Access denied": Need `events:PutRule` and `lambda:AddPermission`

**📸 Screenshot 2c:** EventBridge rule `handson-glue-job-success` Enabled

---

#### Step 3 — Create Lambda Function for Quality Checks

**Prerequisites Check:**
- ✅ Required permissions: `lambda:CreateFunction`, `iam:CreateRole`, `iam:PassRole`
- ✅ `src/validate_orders.py` exists locally
- ✅ SNS topic ARN from Step 1

**Step 3.1: Create IAM Role for Lambda**
1. Search → **IAM** → Roles → **Create role**
2. **Custom trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

3. Role name: `handson-quality-lambda-role`
4. Attach managed policy: `AWSLambdaBasicExecutionRole`
5. Add inline policy `quality-s3-sns-access`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:ListBucket","s3:PutObject"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET","arn:aws:s3:::YOUR_BUCKET/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:us-east-1:YOUR_ACCOUNT:handson-data-quality-alerts"
    }
  ]
}
```

**Step 3.2: Create Lambda Function**
1. Search → **Lambda** → **Create function**
2. Select **Author from scratch**

| Field | Value |
|-------|-------|
| Function name | `handson-data-quality-check` |
| Runtime | Python 3.11 |
| Existing role | `handson-quality-lambda-role` |

3. Click **Create function**

**Step 3.3: Upload Code**
```powershell
# Create deployment package with Great Expectations
mkdir lambda_package
pip install great-expectations pandas pyarrow s3fs -t lambda_package/
Copy-Item src\validate_orders.py lambda_package\
Compress-Archive -Path lambda_package\* -DestinationPath quality.zip -Force
```

1. Lambda → Code tab → **Upload from** → **.zip file** → upload `quality.zip`
2. Handler: `validate_orders.main`
3. Timeout: **5 min** | Memory: **512 MB**

**Step 3.4: Set Environment Variables**
1. Configuration → Environment variables → Edit
2. Add:

| Key | Value |
|-----|-------|
| `DATA_LAKE_BUCKET` | `handson-data-lake-YOUR_ACCOUNT_ID` |
| `SNS_TOPIC_ARN` | `arn:aws:sns:us-east-1:ACCOUNT:handson-data-quality-alerts` |

**📸 Screenshot 3a:** Lambda function with env vars and 5-min timeout

---

#### Step 4 — Test Locally (No AWS Cost)

> Run the validator locally before deploying. Zero AWS cost for local testing.

**Step 4.1: Install Dependencies**
```powershell
pip install great-expectations pandas pyarrow s3fs
```

**Step 4.2: Create Test Data with Quality Issues**
```powershell
python -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown Product','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
})
df.to_parquet('/tmp/test_dirty.parquet', index=False)
print('Dirty test data created')
"
```

**Step 4.3: Run Validation on Dirty Data (Expect FAILURE)**
```powershell
$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
```

**Expected Output:**
```
❌ FAILED | 7/10 checks passed | 4 rows
Failed checks:
  ❌ expect_column_values_to_not_be_null: order_id (1 null)
  ❌ expect_column_values_to_be_unique: order_id (duplicate ORD-001)
  ❌ expect_column_values_to_be_between: amount (-5.00 < 0.01)
```

**📸 Screenshot 4a:** Terminal showing FAILED validation with specific failed checks

**Step 4.4: Create Clean Test Data and Re-validate (Expect PASS)**
```powershell
python -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002','ORD-003'],
    'customer_id':['C1','C2','C3'],
    'product':    ['Widget A','Widget B','Widget C'],
    'amount':     [29.99,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16']
})
df.to_parquet('/tmp/test_clean.parquet', index=False)
print('Clean data created')
"
python src\validate_orders.py
```

**Expected Output:**
```
✅ PASSED | 10/10 checks passed | 3 rows
Data quality: EXCELLENT ✅
```

**📸 Screenshot 4b:** Terminal showing PASSED validation — all 10 checks green

---

## 5B. AWS CLI Method

### Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.7_data_quality

$REGION       = "us-east-1"
$ACCOUNT      = aws sts get-caller-identity --query Account --output text
$BUCKET       = "handson-data-lake-$ACCOUNT"
$LAMBDA_NAME  = "handson-data-quality-check"
$ROLE_NAME    = "handson-quality-lambda-role"
$TOPIC_NAME   = "handson-data-quality-alerts"
$ALERT_EMAIL  = "your-email@example.com"   # change this

Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
```

---

### Phase 1 — Install Dependencies + Run Locally

```powershell
# Install Great Expectations and dependencies
pip install great-expectations==0.18.12 pandas pyarrow s3fs

# Verify
python -c "import great_expectations as gx; print('GX version:', gx.__version__)"

# Create dirty test data
python -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown Product','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
})
df.to_parquet('/tmp/test_dirty.parquet', index=False)
print('Dirty test data created at /tmp/test_dirty.parquet')
"

# Run validation — expects FAILURE
$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
# Expected: FAILED — 3 checks fail (null, duplicate, negative amount)

# Create clean data and re-validate
python -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002','ORD-003'],
    'customer_id':['C1','C2','C3'],
    'product':    ['Widget A','Widget B','Widget C'],
    'amount':     [29.99,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16']
})
df.to_parquet('/tmp/test_clean.parquet', index=False)
print('Clean data created')
"
python src\validate_orders.py
# Expected: PASSED — all 10 checks pass
```

---

### Phase 2 — Create SNS Topic + Email Subscription

```powershell
# Create SNS topic
$TOPIC_ARN = aws sns create-topic `
  --name $TOPIC_NAME `
  --query "TopicArn" --output text
Write-Host "Topic ARN: $TOPIC_ARN"
# Expected: arn:aws:sns:us-east-1:ACCOUNT:handson-data-quality-alerts

# Subscribe email address
aws sns subscribe `
  --topic-arn $TOPIC_ARN `
  --protocol email `
  --notification-endpoint $ALERT_EMAIL
# Expected: SubscriptionArn = PendingConfirmation

Write-Host "⚠️ Check email '$ALERT_EMAIL' and click the confirmation link!"
Write-Host "Subscription will be 'PendingConfirmation' until confirmed."

# After confirming email, verify subscription
aws sns list-subscriptions-by-topic `
  --topic-arn $TOPIC_ARN `
  --query "Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint,Status:SubscriptionArn}"
# Expected: Protocol=email, Status=arn:... (not PendingConfirmation)

# Test SNS (optional — sends test email)
aws sns publish `
  --topic-arn $TOPIC_ARN `
  --subject "Test: Data Quality Alert" `
  --message "This is a test notification from handson-data-quality pipeline."
# Expected: MessageId returned, email arrives in inbox
```

---

### Phase 3 — Create IAM Role for Lambda

```powershell
# Trust policy
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\quality-trust.json" -Encoding utf8

aws iam create-role `
  --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\quality-trust.json"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME `
  --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"

# Attach basic Lambda execution (CloudWatch Logs)
aws iam attach-role-policy `
  --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# Add S3 + SNS inline policy
@"
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Effect":"Allow",
      "Action":["s3:GetObject","s3:ListBucket","s3:PutObject"],
      "Resource":["arn:aws:s3:::$BUCKET","arn:aws:s3:::$BUCKET/*"]
    },
    {
      "Effect":"Allow",
      "Action":["sns:Publish"],
      "Resource":"$TOPIC_ARN"
    }
  ]
}
"@ | Out-File "$env:TEMP\quality-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name $ROLE_NAME `
  --policy-name "quality-s3-sns-access" `
  --policy-document "file://$env:TEMP\quality-policy.json"

Write-Host "✅ IAM role ready with 2 policies"
```

---

### Phase 4 — Package and Deploy Lambda

```powershell
# Create deployment package with all dependencies
New-Item -ItemType Directory -Path "lambda_package" -Force
pip install great-expectations pandas pyarrow s3fs -t lambda_package\ --quiet
Copy-Item src\validate_orders.py lambda_package\
Compress-Archive -Path lambda_package\* -DestinationPath quality.zip -Force

Write-Host "Package size: $((Get-Item quality.zip).Length / 1MB) MB"
# Expected: ~50–80 MB (Great Expectations has many dependencies)

# Wait for IAM role propagation
Start-Sleep -Seconds 10

# Create Lambda function
aws lambda create-function `
  --function-name $LAMBDA_NAME `
  --runtime python3.11 `
  --role $ROLE_ARN `
  --handler validate_orders.main `
  --zip-file "fileb://quality.zip" `
  --timeout 300 `
  --memory-size 512 `
  --environment "Variables={DATA_LAKE_BUCKET=$BUCKET,SNS_TOPIC_ARN=$TOPIC_ARN}"

aws lambda wait function-active --function-name $LAMBDA_NAME
Write-Host "✅ Lambda deployed and active"

# Verify
aws lambda get-function --function-name $LAMBDA_NAME `
  --query "Configuration.{State:State,Runtime:Runtime,Timeout:Timeout,Memory:MemorySize}"
# Expected: State=Active, Runtime=python3.11, Timeout=300, Memory=512
```

---

### Phase 5 — Create EventBridge Rule (Auto-trigger)

```powershell
# Get Lambda ARN
$LAMBDA_ARN = aws lambda get-function `
  --function-name $LAMBDA_NAME `
  --query "Configuration.FunctionArn" --output text

# Create EventBridge rule
$RULE_ARN = aws events put-rule `
  --name "handson-glue-job-success" `
  --event-pattern '{
    "source": ["aws.glue"],
    "detail-type": ["Glue Job State Change"],
    "detail": {
      "jobName": ["handson-etl-job"],
      "state": ["SUCCEEDED"]
    }
  }' `
  --state ENABLED `
  --description "Trigger data quality check after Glue ETL job succeeds" `
  --query "RuleArn" --output text

Write-Host "Rule ARN: $RULE_ARN"

# Add Lambda as target
aws events put-targets `
  --rule "handson-glue-job-success" `
  --targets "Id=QualityCheck,Arn=$LAMBDA_ARN"

# Allow EventBridge to invoke Lambda
aws lambda add-permission `
  --function-name $LAMBDA_NAME `
  --statement-id "AllowEventBridge" `
  --action "lambda:InvokeFunction" `
  --principal "events.amazonaws.com" `
  --source-arn $RULE_ARN

Write-Host "✅ EventBridge rule configured — auto-triggers after Glue job"
```

---

### Phase 6 — Test Lambda Manually

```powershell
# Invoke Lambda directly (simulates EventBridge trigger)
aws lambda invoke `
  --function-name $LAMBDA_NAME `
  --payload '{}' `
  --log-type Tail `
  response.json

# Show response
Get-Content response.json

# Show Lambda logs (base64 encoded in response)
$LOG = aws lambda invoke `
  --function-name $LAMBDA_NAME `
  --payload '{}' `
  --log-type Tail `
  --query "LogResult" `
  /dev/null 2>&1

# Check CloudWatch Logs for output
aws logs tail "/aws/lambda/$LAMBDA_NAME" --since 5m
# Expected: Validation report output with PASSED or FAILED status
```

---

### Phase 7 — Verify S3 Quarantine and Reports

```powershell
# Check quarantine zone (populated when validation fails)
aws s3 ls "s3://$BUCKET/quarantine/" --recursive
# Expected: quarantine files if any validation failed

# Check quality reports
aws s3 ls "s3://$BUCKET/data-quality/reports/" --recursive
# Expected: JSON report files from each validation run

# Download and read latest report
$LATEST = aws s3 ls "s3://$BUCKET/data-quality/reports/" `
  --recursive --query "Contents[-1].Key" --output text 2>$null
if ($LATEST) {
  aws s3 cp "s3://$BUCKET/$LATEST" /tmp/latest_report.json
  Get-Content /tmp/latest_report.json | ConvertFrom-Json |
    Select-Object success, passed, total, row_count, timestamp
}
```

---

## 6. Code Deep Dive

### `src/validate_orders.py` — Complete Explanation

```python
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
```
- `great_expectations` — the validation library. Runs entirely locally or in Lambda.
- `RuntimeBatchRequest` — allows passing a live DataFrame (not just file paths).
  Enables in-memory validation without saving intermediate files.

---

```python
context = gx.get_context()
datasource = context.sources.add_pandas("orders_datasource")
asset = datasource.add_dataframe_asset("orders")
batch_request = asset.build_batch_request(dataframe=df)
```
- `gx.get_context()` — creates an in-memory GX context (no config files needed).
- `context.sources.add_pandas(...)` — registers a Pandas datasource. Accepts DataFrames.
- `add_dataframe_asset("orders")` — names this asset "orders" for tracking.
- `build_batch_request(dataframe=df)` — wraps the DataFrame for validation.

---

```python
validator.expect_table_row_count_to_be_between(min_value=1)
```
- Checks: `len(df) >= 1`. Fails if the table is empty.
- Why? An empty table after ETL means the job produced no output — a serious pipeline failure.

---

```python
validator.expect_column_values_to_not_be_null("order_id")
validator.expect_column_values_to_be_unique("order_id")
```
- `not_null` — scans every row, counts NULLs. Fails if count > 0.
- `unique` — groups by order_id, finds any with count > 1.
- Together: `order_id` is the primary key. One NULL or duplicate = data integrity violation.

---

```python
validator.expect_column_values_to_be_between(
    "amount", min_value=0.01, max_value=10000.0
)
```
- Checks: `0.01 <= amount <= 10000.0` for every row.
- `min_value=0.01` (not 0) — rejects zero-amount orders (likely data errors).
- `max_value=10000.0` — rejects absurd values (data entry errors, type overflow).

---

```python
validator.expect_column_values_to_be_in_set(
    "product",
    value_set=["Widget A", "Widget B", "Widget C", "Gadget X", "Gadget Y"],
    mostly=0.99,
)
```
- `value_set` — the known/allowed product names.
- `mostly=0.99` — 99% of rows must match. 1% can be unknown.
- Why 99% not 100%? New products may appear before the dimension table is updated.
  Using 100% would cause false failures on legitimate new products.
- The 1% that don't match are flagged but don't fail the pipeline.

---

```python
validator.expect_column_mean_to_be_between(
    "amount", min_value=10.0, max_value=200.0
)
```
- Statistical check — detects subtle data drift.
- If mean drops to $2 (most orders are $2 instead of $30), something is wrong.
- This catches problems that row-level checks miss:
  - All amounts are positive (passes validity check)
  - But most are $0.01 (passes range check, fails mean check)

---

```python
results = validator.validate()
success = results["success"]
passed  = results["statistics"]["successful_expectations"]
total   = results["statistics"]["evaluated_expectations"]
```
- `validate()` runs ALL expectations and returns a `ValidationResult` object.
- `results["success"]` = True only if ALL expectations passed.
- `statistics` gives the summary counts.

---

```python
if not results["success"]:
    print("Failed checks:")
    for result in results["results"]:
        if not result["success"]:
            print(f"  ❌ {result['expectation_config']['expectation_type']}: "
                  f"{result['expectation_config']['kwargs']}")
```
- Iterates all results, prints only the failing ones.
- `expectation_type` = the GX method name (e.g., `expect_column_values_to_not_be_null`)
- `kwargs` = the parameters (e.g., `{"column": "order_id"}`)

---

```python
if not results["success"]:
    print("❌ Data quality validation FAILED — pipeline should not proceed")
    sys.exit(1)
else:
    sys.exit(0)
```
- `sys.exit(1)` — non-zero exit code signals failure to any calling process:
  - Airflow `BashOperator`: raises `AirflowException` → task FAILS → pipeline stops
  - CI/CD pipeline: step marked as failed → deployment blocked
  - AWS Lambda: returns error response → EventBridge records as failed invocation

### Common Mistakes and Fixes

| Mistake | Error | Fix |
|---------|-------|-----|
| `mostly=1.0` on evolving dimension | Fails on new products | Use `mostly=0.99` |
| No `min_value` on amount | Accepts negative amounts | Set `min_value=0.01` |
| Not checking row count | Empty table passes all checks | Add `expect_table_row_count_to_be_between(min_value=1)` |
| Wrong `strftime_format` | All dates fail format check | Use `%Y-%m-%d` for `2024-01-15` |
| Lambda timeout too short | GX context creation slow | Set timeout >= 300s |
| Lambda memory too low | pandas OOM on large files | Set memory >= 512 MB |

---

## 7. Verification & Validation

### 7.1 Local Verification

```powershell
# Full verification sequence
Write-Host "=== DATA QUALITY VERIFICATION ===" -ForegroundColor Cyan

# Test 1: Clean data → should PASS
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002','ORD-003'],
    'customer_id':['C1','C2','C3'],
    'product':    ['Widget A','Widget B','Widget C'],
    'amount':     [29.99,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16']
}).to_parquet('/tmp/clean.parquet', index=False)
"
$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Clean data: PASSED" } else { Write-Host "❌ Clean data: FAILED" }

# Test 2: Dirty data → should FAIL
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
}).to_parquet('/tmp/dirty.parquet', index=False)
"
python src\validate_orders.py
if ($LASTEXITCODE -ne 0) { Write-Host "✅ Dirty data correctly detected: FAILED" } else { Write-Host "❌ Dirty data was NOT detected" }

Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

### 7.2 AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| SNS Topic | SNS → Topics | `handson-data-quality-alerts` listed |
| Email subscription | Topic → Subscriptions | Status = Confirmed |
| EventBridge rule | EventBridge → Rules | `handson-glue-job-success` Enabled |
| Lambda function | Lambda → Functions | `handson-data-quality-check` Active |
| Lambda env vars | Lambda → Configuration → Env vars | DATA_LAKE_BUCKET + SNS_TOPIC_ARN set |
| CloudWatch Logs | CloudWatch → Log groups | `/aws/lambda/handson-data-quality-check` |

### 7.3 Verification Checklist

- [ ] `pip install great-expectations` succeeds
- [ ] `python src/validate_orders.py` runs without import errors
- [ ] Clean data: all 10 checks PASSED, exit code = 0
- [ ] Dirty data: null check FAILED, unique check FAILED, range check FAILED
- [ ] Dirty data: exit code = 1 (pipeline would stop)
- [ ] SNS topic `handson-data-quality-alerts` created
- [ ] Email subscription Status = Confirmed
- [ ] Lambda `handson-data-quality-check` State = Active
- [ ] EventBridge rule `handson-glue-job-success` Enabled
- [ ] Lambda invoked manually returns validation report

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During Validation

**When running on clean data:**
- Each `expect_*` call adds an expectation to the suite silently
- `validator.validate()` runs ALL expectations in one pass
- GX reports: `10/10 expectations succeeded`
- `sys.exit(0)` — Airflow/CI marks as SUCCESS

**When running on dirty data:**
- Same `validate()` call, same expectations
- GX reports failures with the actual values that violated the expectation
- The `mostly=0.99` check on product PASSES even if "Unknown" appears — because only 1 of 4 rows (25%) has Unknown, which is below the 99% threshold. If 99%+ of rows had "Unknown", it would fail.
- `sys.exit(1)` — Airflow/CI marks as FAILURE → blocks downstream tasks

### 8.2 GX Validation Report Structure

```json
{
  "success": false,
  "statistics": {
    "evaluated_expectations": 10,
    "successful_expectations": 7,
    "unsuccessful_expectations": 3
  },
  "results": [
    {
      "success": false,
      "expectation_config": {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {"column": "order_id"}
      },
      "result": {
        "element_count": 4,
        "unexpected_count": 1,
        "unexpected_percent": 25.0,
        "unexpected_values": [null]
      }
    }
  ]
}
```

### 8.3 Billing Observations

- **Local runs** = $0 (no AWS resources used)
- **Lambda invocations** = $0 (free tier covers 1M/month)
- **SNS alerts** = $0 (free tier covers 1M publishes/month)
- **EventBridge** = $0 (first 5M events/month free)
- **S3 reports** = ~$0.01/month (tiny JSON files)
- **Real cost driver at scale**: Lambda with heavy GX context = 300s × 512 MB × many runs
  At 1,000 runs/month: 1,000 × 300s × 512 MB = 153,600 GB-seconds ≈ $2.45/month

### 8.4 Data Quality Tools Comparison

| Tool | Language | Scale | Best For |
|------|---------|-------|---------|
| **Great Expectations** | Python | Medium | Rich reports, Python pipelines |
| dbt tests | SQL | Small | Quick checks in dbt models |
| AWS Deequ | PySpark/Scala | Large | EMR/Glue large datasets |
| Pandas assertions | Python | Small | Quick ad-hoc checks |

---

## 9. Screenshots Guidance

| # | What to Capture | When |
|---|----------------|------|
| SS-01 | S3 `processed/orders/` with Parquet files | Phase 0 |
| SS-02 | `pip install great-expectations` output | Phase 1 |
| SS-03 | **FAILED** validation output — 3 specific checks | Phase 1 |
| SS-04 | **PASSED** validation output — all 10 green | Phase 1 |
| SS-05 | SNS Topics list | Step 1.1 |
| SS-06 | SNS topic `handson-data-quality-alerts` + email subscription Confirmed | Step 1.4 |
| SS-07 | EventBridge rule JSON pattern form | Step 2.3 |
| SS-08 | EventBridge rule `handson-glue-job-success` Enabled | Step 2.5 |
| SS-09 | Lambda `handson-data-quality-check` with env vars | Step 3.4 |
| SS-10 | Lambda invocation response showing validation output | Phase 6 |
| SS-11 | CloudWatch Logs showing validation report | Phase 7 |
| SS-12 | S3 `data-quality/reports/` with JSON report files | Phase 7 |

**Total: 12 screenshots**

---

## 10. Cleanup Steps

### 10.1 AWS Console Cleanup

1. **Lambda:** Lambda → `handson-data-quality-check` → Actions → **Delete**
2. **EventBridge rule:** EventBridge → Rules → `handson-glue-job-success` → **Delete**
3. **SNS subscription:** SNS → Topic → Subscriptions → **Unsubscribe** (email)
4. **SNS topic:** SNS → Topics → `handson-data-quality-alerts` → **Delete**
5. **IAM role:** IAM → Roles → `handson-quality-lambda-role` → **Delete**
6. **S3 artifacts:** S3 → bucket → `data-quality/`, `quarantine/` → **Delete**

### 10.2 AWS CLI Cleanup (PowerShell)

```powershell
# 1. Remove EventBridge target + rule
aws events remove-targets --rule "handson-glue-job-success" --ids "QualityCheck"
aws events delete-rule --name "handson-glue-job-success"

# 2. Delete Lambda
aws lambda delete-function --function-name $LAMBDA_NAME

# 3. Delete SNS subscription + topic
$SUBS = aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN `
  --query "Subscriptions[*].SubscriptionArn" --output text
foreach ($sub in $SUBS -split "`t") {
  if ($sub -ne "PendingConfirmation") {
    aws sns unsubscribe --subscription-arn $sub
  }
}
aws sns delete-topic --topic-arn $TOPIC_ARN

# 4. Delete IAM role + policies
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "quality-s3-sns-access"
aws iam detach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
aws iam delete-role --role-name $ROLE_NAME

# 5. Clean S3 artifacts
aws s3 rm "s3://$BUCKET/data-quality/" --recursive
aws s3 rm "s3://$BUCKET/quarantine/" --recursive

# 6. Clean local files
Remove-Item -Force quality.zip, response.json -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force lambda_package -ErrorAction SilentlyContinue

Write-Host "✅ All resources cleaned up"
```

### 10.3 Verify Cleanup

```powershell
aws lambda get-function --function-name $LAMBDA_NAME 2>&1 |
  Select-String "ResourceNotFoundException"
# Expected: ResourceNotFoundException

aws events describe-rule --name "handson-glue-job-success" 2>&1 |
  Select-String "ResourceNotFoundException"
# Expected: ResourceNotFoundException

Write-Host "✅ Cleanup verified"
```

---

## Quick Reference Card

```
INSTALL:
  pip install great-expectations pandas pyarrow s3fs

RUN LOCALLY:
  $env:DATA_LAKE_BUCKET = "handson-data-lake-ACCOUNT"
  python src\validate_orders.py
  Echo "Exit code: $LASTEXITCODE"   # 0=PASS, 1=FAIL

CREATE DIRTY TEST DATA:
  python -c "import pandas as pd; pd.DataFrame({'order_id':['ORD-001',None],'amount':[29.99,-5.00],'customer_id':['C1','C2'],'product':['Widget A','Widget B'],'order_date':['2024-01-15','2024-01-15']}).to_parquet('/tmp/test.parquet',index=False)"

CHECKS: row_count >= 1 | order_id not_null + unique | amount 0.01-10000
        product in list (99%) | order_date format | mean(amount) 10-200

SNS:
  aws sns create-topic --name handson-data-quality-alerts
  aws sns subscribe --topic-arn TOPIC_ARN --protocol email --notification-endpoint EMAIL

EVENTBRIDGE:
  aws events put-rule --name handson-glue-job-success \
    --event-pattern '{"source":["aws.glue"],"detail":{"jobName":["handson-etl-job"],"state":["SUCCEEDED"]}}'

CLEANUP:
  aws events delete-rule --name handson-glue-job-success
  aws lambda delete-function --function-name handson-data-quality-check
  aws sns delete-topic --topic-arn TOPIC_ARN
  aws iam delete-role --role-name handson-quality-lambda-role

COST: ~$0.01/month | Great Expectations is FREE
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.7_data_quality*
