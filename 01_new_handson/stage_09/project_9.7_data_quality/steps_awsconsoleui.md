# Project 9.7 — Data Quality Validation
# Console UI Steps (Improved Template Format)
# Lambda: handson-data-quality-check | SNS: handson-data-quality-alerts

---

> **Recommended order:**
> 1. Run validation locally (zero cost, immediate feedback)
> 2. Create SNS topic + email subscription
> 3. Create EventBridge rule for automation
> 4. Create Lambda for cloud-based execution

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Python + great-expectations installed locally
- ✅ AWS CLI configured (`aws sts get-caller-identity` works)
- ✅ S3 bucket with `processed/orders/` Parquet data
- ✅ Region: us-east-1 selected

**Step 0.1: Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → **US East (N. Virginia) us-east-1**

**Step 0.2: Verify S3 Input Data**
1. Search → **S3** → your data lake bucket → `processed/orders/`
2. **Expected View:** Parquet files from Glue ETL
3. **If Empty:** Run Glue ETL (Project 9.2) first to produce processed data

**📸 Screenshot P0:** S3 `processed/orders/` showing Parquet files

---

### STEP 1 — Run Validation Locally First (Zero Cost)

> Run this before any AWS setup. Validates the script works and shows what failures look like.

**Prerequisites Check:**
- ✅ Python 3.9+ installed
- ✅ `pip install great-expectations pandas pyarrow s3fs` completed

**Step 1.1: Create Dirty Test Data (PowerShell)**
```powershell
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown Product','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
}).to_parquet('/tmp/test.parquet', index=False)
print('Test data created')
"
```

**Step 1.2: Run Validation (Expect FAILURE)**
```powershell
$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
```

**Step 1.3: Validate Result**
**Expected Outcome:**
```
Status:  ❌ FAILED
Checks:  7/10 passed
Failed checks:
  ❌ expect_column_values_to_not_be_null: order_id
  ❌ expect_column_values_to_be_unique: order_id
  ❌ expect_column_values_to_be_between: amount
```
Exit code: `$LASTEXITCODE` = 1

**Troubleshooting:**
- `ModuleNotFoundError: great_expectations`: Run `pip install great-expectations`
- `FileNotFoundError /tmp/test.parquet`: Fix the Python create script — check quotes

**📸 Screenshot 1a:** Terminal showing FAILED validation with 3 specific failing checks
**📸 Screenshot 1b:** Terminal showing PASSED validation on clean data (all 10 green)

---

### STEP 2 — Create SNS Topic for Quality Alerts

**Prerequisites Check:**
- ✅ Required permissions: `sns:CreateTopic`, `sns:Subscribe`
- ✅ Services enabled: Amazon SNS (us-east-1)
- ✅ Email address to subscribe

**Step 2.1: Navigate and Verify**
1. Search bar → **SNS** → click **Simple Notification Service**
2. Left sidebar → **Topics**
3. **Expected View:** Topics list
4. Click **Create topic** (orange button)

**📸 Screenshot 2a:** SNS Topics list

**Step 2.2: Make Selections — Topic Type**

**Decision Point 1:** Topic type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Standard** | Email alerts, unordered delivery | ✅ Quality alerts don't need ordering |
| FIFO | Exactly-once, ordered | ❌ Overkill for email notifications |

1. Select **Standard**

**Step 2.3: Configure Topic**

| Field | Value |
|-------|-------|
| Name | `handson-data-quality-alerts` |
| Display name | `Data Quality Alerts` |
| Tags | Project=handson |

**Step 2.4: Create and Validate**
1. Click **Create topic**
2. **Expected Outcome:** Topic ARN shown: `arn:aws:sns:us-east-1:ACCOUNT:handson-data-quality-alerts`

**📸 Screenshot 2b:** SNS topic `handson-data-quality-alerts` just created

**Step 2.5: Subscribe Email**
1. On the topic page → click **Create subscription**
2. Fill in:

| Field | Value |
|-------|-------|
| Topic ARN | (auto-filled) |
| Protocol | **Email** |
| Endpoint | your-email@example.com |

3. Click **Create subscription**
4. **⚠️ Check your email inbox — click the AWS confirmation link**

**Step 2.6: Confirm Subscription**
1. Refresh Subscriptions tab
2. **Expected View:** Status changes from `PendingConfirmation` to `Confirmed`

**Troubleshooting:**
- No email after 2 minutes: Check spam. Try re-subscribing.
- `AccessDenied`: IAM user needs `sns:Subscribe`

**📸 Screenshot 2c:** Subscription status = **Confirmed**

---

### STEP 3 — Create EventBridge Rule (Auto-Trigger)

**Prerequisites Check:**
- ✅ Required permissions: `events:PutRule`, `events:PutTargets`
- ✅ Lambda function exists (create first in Step 4, then come back to add target)
- ✅ Services enabled: Amazon EventBridge

**Step 3.1: Navigate and Verify**
1. Search bar → **EventBridge** → **Amazon EventBridge**
2. Left sidebar → **Rules** → **Create rule**

**📸 Screenshot 3a:** EventBridge Rules list

**Step 3.2: Configure Rule Details**

| Field | Value |
|-------|-------|
| Name | `handson-glue-job-success` |
| Description | `Trigger data quality check after Glue ETL job succeeds` |
| Event bus | **default** |
| Rule type | **Rule with an event pattern** |

Click **Next**

**Step 3.3: Make Selections — Event Pattern Method**

**Decision Point 1:** Pattern creation method
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Use pattern form | UI-guided, simple | ❌ Glue events not in standard form |
| **Custom pattern (JSON)** | Full control over Glue events | ✅ Required |

1. Select **Custom pattern (JSON editor)**
2. Paste exactly:

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

**Field-by-field explanation:**

| Field | Value | Why |
|-------|-------|-----|
| `source` | `aws.glue` | Only events from Glue service |
| `detail-type` | `Glue Job State Change` | Only state change events |
| `detail.jobName` | `handson-etl-job` | Only our specific Glue job |
| `detail.state` | `SUCCEEDED` | Only on success (not start, not fail) |

3. Click **Next**

**📸 Screenshot 3b:** EventBridge JSON event pattern filled in

**Step 3.4: Add Target**
1. Target type: **AWS service**
2. Select target: **Lambda function**
3. Function: **handson-data-quality-check**
   - If not yet created: save rule without target, create Lambda (Step 4), then edit rule
4. Click **Next** → **Create rule**

**Step 3.5: Validate Result**
**Expected Outcome:** Rule `handson-glue-job-success` Status = **Enabled**

**Troubleshooting:**
- "Lambda function not found": Create Lambda first (Step 4), then edit rule to add target
- "Access denied": Need `events:PutRule` and `events:PutTargets`

**📸 Screenshot 3c:** EventBridge rule `handson-glue-job-success` Status = **Enabled**

---

### STEP 4 — Create Lambda Function

**Prerequisites Check:**
- ✅ Required permissions: `lambda:CreateFunction`, `iam:CreateRole`, `iam:PassRole`
- ✅ `src/validate_orders.py` exists locally
- ✅ SNS topic ARN from Step 2

**Step 4.1: Create IAM Role**
1. IAM → Roles → **Create role**
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
4. Attach: `AWSLambdaBasicExecutionRole`
5. Add inline policy `quality-s3-sns-access` (replace YOUR_BUCKET and YOUR_ACCOUNT):

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

**Step 4.2: Create Lambda**
1. Search → **Lambda** → **Create function** → **Author from scratch**

| Field | Value |
|-------|-------|
| Function name | `handson-data-quality-check` |
| Runtime | **Python 3.11** |
| Execution role | Use existing: `handson-quality-lambda-role` |

2. Click **Create function**

**Step 4.3: Package and Upload Code**

```powershell
# Create deployment package (PowerShell)
New-Item -ItemType Directory -Path lambda_package -Force
pip install great-expectations pandas pyarrow s3fs -t lambda_package\ --quiet
Copy-Item src\validate_orders.py lambda_package\
Compress-Archive -Path lambda_package\* -DestinationPath quality.zip -Force
```

1. Lambda → Code tab → **Upload from** → **.zip file** → upload `quality.zip`
2. Handler: `validate_orders.main`

**Step 4.4: Configure Settings**
1. Configuration → **General configuration** → Edit
   - Timeout: **5 min 0 sec** (300 seconds)
   - Memory: **512 MB**
2. Configuration → **Environment variables** → Edit → Add:

| Key | Value |
|-----|-------|
| `DATA_LAKE_BUCKET` | `handson-data-lake-YOUR_ACCOUNT_ID` |
| `SNS_TOPIC_ARN` | `arn:aws:sns:us-east-1:ACCOUNT:handson-data-quality-alerts` |

**Step 4.5: Validate Result**
**Expected Outcome:** Function state = Active, handler = `validate_orders.main`

**Troubleshooting:**
- "Handler not found": Must be `validate_orders.main` (filename.function_name)
- Lambda timeout during test: Great Expectations context creation can take 30–60s — ensure timeout >= 300s
- Memory error: Increase to 1024 MB if pandas OOM on large datasets

**📸 Screenshot 4a:** Lambda function with 300s timeout, 512MB memory, env vars set

---

### STEP 5 — Test Lambda via Console

**Step 5.1: Create Test Event**
1. Lambda → **Test** tab → **Create new event**
2. Event name: `test-quality-check`
3. Event JSON: `{}`  (Lambda reads S3 path from env var, not the event)
4. Click **Save**

**Step 5.2: Invoke**
1. Click **Test** (orange button)
2. **Expected View:** Execution results panel (green = success, red = error)

**Decision Point 1:** Result interpretation
| Result | Meaning | Action |
|--------|---------|--------|
| Green, exit 0 | PASS — S3 data is clean | ✅ Pipeline would continue |
| Red, exit 1 | FAIL — bad data detected | Check "Log output" section for which checks failed |
| Red, exception | Script error | Check Handler name, timeout, memory |

**📸 Screenshot 5a:** Lambda test result — showing validation output in execution details

---

### Console UI Summary

| Step | Action | Resource Created |
|------|--------|----------------|
| Step 1 | Local validation (no AWS) | Demonstrates PASS/FAIL behavior |
| Step 2 | SNS topic + email sub | `handson-data-quality-alerts` |
| Step 3 | EventBridge rule | `handson-glue-job-success` (auto-trigger) |
| Step 4 | Lambda + IAM | `handson-data-quality-check` |
| Step 5 | Test Lambda | Validation report in CloudWatch Logs |

### Screenshot Summary

| # | Description | Step |
|---|-------------|------|
| P0 | S3 processed/orders/ with Parquet files | Phase 0 |
| 1a | Terminal: FAILED validation — 3 checks | Step 1.2 |
| 1b | Terminal: PASSED validation — all 10 | Step 1.2 |
| 2a | SNS Topics list | Step 2.1 |
| 2b | SNS topic created | Step 2.4 |
| 2c | Email subscription Confirmed | Step 2.6 |
| 3a | EventBridge Rules list | Step 3.1 |
| 3b | EventBridge JSON pattern | Step 3.3 |
| 3c | Rule Status = Enabled | Step 3.5 |
| 4a | Lambda with timeout/memory/env vars | Step 4.4 |
| 5a | Lambda test result with validation output | Step 5.2 |

**Total: 11 screenshots for complete documentation**
