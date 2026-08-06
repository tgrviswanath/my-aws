# Project 9.4 — Spark Processing on EMR Serverless
# Console UI Steps (Improved Template Format)
# Region: us-east-1 | EMR App: handson-spark | IAM Role: handson-emr-serverless-role

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `emr-serverless:*`, `iam:CreateRole`, `iam:PutRolePolicy`, `s3:PutObject`
- ✅ Services enabled: EMR, IAM, S3 — available in us-east-1
- ✅ Region: us-east-1 selected in top-right of AWS Console
- ✅ S3 bucket with `raw/orders/` CSV data

**Step 0.1: Navigate and Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → **US East (N. Virginia) us-east-1**

**Step 0.2: Verify Input Data in S3**
1. Search bar → **S3** → click your data lake bucket
2. Navigate to `raw/orders/`
3. **Expected View:** At least one `.csv` file present
4. **If Missing:** Upload a sample orders CSV (see GUIDE.md Phase 0 for format)

**📸 Screenshot P0:** S3 bucket showing `raw/orders/` with CSV file

---

### STEP 1 — Create IAM Role for EMR Serverless

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:PutRolePolicy`
- ✅ Services enabled: IAM (global)
- ✅ Region availability: IAM is global — no region needed

**Step 1.1: Navigate and Verify**
1. Search bar → **IAM** → click it
2. Left sidebar → **Roles**
3. **Expected View:** Roles list
4. Click **Create role**

**📸 Screenshot 1a:** IAM Roles list before creation

**Step 1.2: Make Selections — Trusted Entity**

**Decision Point 1:** Trusted entity type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service (dropdown) | Common services — EC2, Lambda, Glue | ❌ EMR Serverless not listed |
| **Custom trust policy** | Paste JSON for any service principal | ✅ Required |
| Web identity | OIDC / GitHub Actions | ❌ Not needed |

1. Select **Custom trust policy**
2. Clear the editor and paste:

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

3. Click **Next**

**📸 Screenshot 1b:** Custom trust policy with emr-serverless.amazonaws.com

**Step 1.3: Configure Permissions**

**Decision Point 2:** Managed policies
| Option | For This Project |
|--------|-----------------|
| Attach managed policies | ❌ No suitable AWS managed policy |
| Skip — add inline after | ✅ We add 3 inline policies |

1. Do NOT select any managed policy
2. Click **Next**

**Step 1.4: Configure Details**

| Field | Value |
|-------|-------|
| Role name | `handson-emr-serverless-role` |
| Description | `EMR Serverless execution role — S3 + Glue + CloudWatch` |

3. Click **Create role**

**Step 1.5: Validate Result**
**Expected Outcome:** Role created — 0 policies attached

**📸 Screenshot 1c:** Role just created with no policies

**Step 1.6: Add S3 Inline Policy**
1. Click on role `handson-emr-serverless-role`
2. Click **Add permissions** → **Create inline policy** → **JSON** tab
3. Paste (replace `YOUR_BUCKET`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
    "Resource": ["arn:aws:s3:::YOUR_BUCKET","arn:aws:s3:::YOUR_BUCKET/*"]
  }]
}
```

4. Policy name: `emr-s3-access` → **Create policy**

**Step 1.7: Add Glue Inline Policy**
1. Click **Add permissions** → **Create inline policy** → **JSON** tab, paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["glue:GetDatabase","glue:GetTable","glue:GetPartitions","glue:CreateTable","glue:UpdateTable"],
    "Resource": "*"
  }]
}
```

2. Policy name: `emr-glue-access` → **Create policy**

**Step 1.8: Add CloudWatch Logs Inline Policy**
1. Click **Add permissions** → **Create inline policy** → **JSON** tab, paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents","logs:DescribeLogGroups","logs:DescribeLogStreams"],
    "Resource": "*"
  }]
}
```

2. Policy name: `emr-cloudwatch-access` → **Create policy**

**Step 1.9: Validate Result**
**Expected Outcome:** Role shows 3 inline policies: `emr-s3-access`, `emr-glue-access`, `emr-cloudwatch-access`

**Troubleshooting:**
- "Invalid principal in policy": Must be `emr-serverless.amazonaws.com` — NOT `emr.amazonaws.com`
- "Invalid JSON": Check brackets and commas using jsonlint.com
- "AccessDenied on create-role": Your user needs `iam:CreateRole` permission

**📸 Screenshot 1d:** Role with all 3 inline policies visible

---

### STEP 2 — Upload Spark Script to S3

**Prerequisites Check:**
- ✅ Required permissions: `s3:PutObject`
- ✅ `src/spark_job.py` exists locally

**Step 2.1: Navigate and Verify**
1. Search bar → **S3** → click your data lake bucket

**Step 2.2: Create scripts/ Folder**
1. Click **Create folder**
2. Name: `scripts` → Click **Create folder**

**Step 2.3: Upload spark_job.py**
1. Click the `scripts/` folder
2. Click **Upload** → **Add files**
3. Navigate to project `src/spark_job.py` → **Open**
4. Click **Upload**

**Step 2.4: Validate Result**
**Expected Outcome:** `scripts/spark_job.py` visible, size ~3 KB

**📸 Screenshot 2a:** S3 scripts/spark_job.py uploaded

---

### STEP 3 — Create EMR Serverless Application

**Prerequisites Check:**
- ✅ Required permissions: `emr-serverless:CreateApplication`
- ✅ Region: us-east-1

**Step 3.1: Navigate and Verify**
1. Search bar → **EMR** → click **Amazon EMR**
2. Left sidebar → **EMR Serverless**
3. **Expected View:** EMR Serverless dashboard with **Create application** button
4. **If Different:** Check you're in EMR Serverless, NOT Clusters (EMR on EC2)

**📸 Screenshot 3a:** EMR Serverless landing page

**Step 3.2: Make Selections — Application Type**

**Decision Point 1:** Application type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Spark** | PySpark / Scala Spark ETL, ML | ✅ spark_job.py is PySpark |
| Hive | SQL batch processing | ❌ Not used |

1. Click **Create application** → Select **Spark**

**Step 3.3: Make Selections — Setup Option**

**Decision Point 2:** Setup option
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Default settings | Quick start, pre-set capacity | ❌ No capacity control |
| **Custom settings** | Control driver/executor resources | ✅ Match main.tf config |

1. Select **Use custom settings**

**Step 3.4: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Application name | `handson-spark` | Matches terraform/main.tf resource name |
| EMR release | `emr-6.15.0` | Latest stable — Spark 3.4 included |

**📸 Screenshot 3b:** Application name and release filled in

**Step 3.5: Configure Initial Capacity**

| Field | Value | Why |
|-------|-------|-----|
| Worker type | Driver | Pre-warm 1 driver |
| Worker count | `1` | 1 driver per job |
| CPU | `2 vCPU` | Matches initial_capacity in main.tf |
| Memory | `4 GB` | Matches initial_capacity in main.tf |

**Step 3.6: Configure Maximum Capacity**

| Field | Value | Why |
|-------|-------|-----|
| CPU | `20 vCPU` | Max auto-scale ceiling |
| Memory | `40 GB` | Matches maximum_capacity in main.tf |

**Step 3.7: Configure Auto-Stop**

| Field | Value |
|-------|-------|
| Auto-stop enabled | ✅ Yes |
| Idle timeout | `15` minutes |

**Step 3.8: Create and Validate**
1. Click **Create application**
2. **Expected Outcome:** Status transitions: Creating → Started (auto-starts after creation)

**Troubleshooting:**
- Status stays Creating > 2 min: Refresh. Check CloudTrail if still stuck.
- "Application limit reached": Delete unused applications in this region.

**📸 Screenshot 3c:** Application `handson-spark` Status = **Started**

---

### STEP 4 — Submit Spark Job

**Prerequisites Check:**
- ✅ Application `handson-spark` Status = **Started**
- ✅ IAM role `handson-emr-serverless-role` — 3 inline policies
- ✅ `scripts/spark_job.py` uploaded to S3
- ✅ `raw/orders/` has CSV data

**Step 4.1: Navigate and Verify**
1. Click on application **handson-spark**
2. Click **Submit job**
3. **Expected View:** Job submission form

**📸 Screenshot 4a:** Submit job form before filling

**Step 4.2: Configure Job Details**

| Field | Value |
|-------|-------|
| Job name | `handson-order-analysis` |
| Runtime role | `handson-emr-serverless-role` |
| Script location | `s3://YOUR_BUCKET/scripts/spark_job.py` |

**Step 4.3: Configure Script Arguments**

Add these arguments (each on a new line or comma-separated):
```
--input
s3://YOUR_BUCKET/raw/orders/
--output
s3://YOUR_BUCKET/processed/spark/
```

**Step 4.4: Configure Spark Properties (Optional)**

| Key | Value |
|-----|-------|
| `spark.executor.cores` | `2` |
| `spark.executor.memory` | `4g` |

**Step 4.5: Configure Job Logs**
1. Enable: ✅ **Publish logs to Amazon S3**
2. S3 log location: `s3://YOUR_BUCKET/logs/`

**Step 4.6: Submit and Validate**
1. Click **Submit job**
2. **Expected Outcome:** Job appears with Status = **Pending** → **Running**

**Troubleshooting:**
- "Application not started": Go back and start the application first.
- "Role not found": Check IAM role name spelling — must be `handson-emr-serverless-role`

**📸 Screenshot 4b:** Job Status = **Running**

---

### STEP 5 — Monitor the Job

**Step 5.1: Watch Status**
1. On the Job runs tab, watch the status badge
2. **Pending** (~30–60s) → **Running** (~3–10 min) → **Success** or **Failed**

**Step 5.2: View Job Metrics (after Success)**
1. Click on job run `handson-order-analysis`
2. **Expected View:** Duration, vCPU-hours, GB-hours

**📸 Screenshot 5a:** Job details — Status=Success, duration, vCPU-hours

**Step 5.3: View Spark Logs**
1. Scroll to **Logs** section → click **Driver stdout**
2. **Expected:**
```
Reading from: s3://...
Total records: 1000
Output written to: s3://...
Product monthly records: 15
Customer CLV records: 200
```

**📸 Screenshot 5b:** Driver stdout showing successful output

---

### STEP 6 — Verify Output in S3

**Step 6.1: Navigate to S3 Output**
1. S3 → bucket → `processed/spark/`
2. **Expected View:** Two folders: `product_monthly/` and `customer_clv/`

**Step 6.2: Verify product_monthly/**
1. Click `product_monthly/`
2. **Expected View:** `year=2024/` → `month=1/` → `.snappy.parquet` files

**Step 6.3: Verify customer_clv/**
1. Click `customer_clv/`
2. **Expected View:** `part-00000-*.snappy.parquet` + `_SUCCESS`

**Expected Outcome:** Both output paths have Parquet data with `_SUCCESS` marker.

**Troubleshooting:**
- No output: Job may have failed — check Step 5.3 logs
- Wrong path: Verify `--output` argument matches what you're looking for

**📸 Screenshot 6a:** product_monthly/ with year=/month= partitions
**📸 Screenshot 6b:** customer_clv/ with Parquet files

---

### Console UI Summary

| Step | Resource | Name |
|------|---------|------|
| Step 1 | IAM Role + 3 policies | `handson-emr-serverless-role` |
| Step 2 | S3 script | `scripts/spark_job.py` |
| Step 3 | EMR Serverless App | `handson-spark` |
| Step 4 | Job Run | `handson-order-analysis` |
| Step 6 | S3 Output | `processed/spark/product_monthly/` + `customer_clv/` |

### Screenshot Summary
| # | Description | Step |
|---|-------------|------|
| P0 | S3 raw/orders/ with CSV input | Phase 0 |
| 1a | IAM Roles list | Step 1.1 |
| 1b | Custom trust policy form | Step 1.2 |
| 1c | Role with no policies | Step 1.4 |
| 1d | Role with 3 inline policies | Step 1.9 |
| 2a | S3 scripts/spark_job.py | Step 2.3 |
| 3a | EMR Serverless landing page | Step 3.1 |
| 3b | App creation form | Step 3.4 |
| 3c | App Status=Started | Step 3.8 |
| 4a | Submit job form | Step 4.1 |
| 4b | Job Status=Running | Step 4.6 |
| 5a | Job details Success + metrics | Step 5.2 |
| 5b | Driver stdout log output | Step 5.3 |
| 6a | product_monthly partitions | Step 6.2 |
| 6b | customer_clv Parquet files | Step 6.3 |

**Total: 15 screenshots for complete documentation**
