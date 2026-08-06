# Project 9.2 — AWS Glue ETL Pipeline
# PART 4: Verification, Observations, Screenshots & Cleanup

---

## 7. VERIFICATION & VALIDATION

### 7.1 AWS Console Verification Checklist

| Resource | Where to Check | Expected State |
|----------|---------------|----------------|
| Glue Job | Glue → ETL Jobs | `handson-etl-job` listed |
| Job Script tab | Click job → Script tab | PySpark code visible |
| Job Run history | Click job → Runs tab | Last run: **Succeeded** |
| Processed S3 output | S3 → bucket → `processed/orders/` | Parquet files with `year=X/month=Y/` |
| Trigger | Glue → Triggers | `handson-etl-daily` with CREATED state |
| CloudWatch Logs | CloudWatch → Log Groups → `/aws-glue/jobs/output` | Log stream for your run |

---

### 7.2 Full CLI Verification Script

Copy and run this entire block to verify everything at once:

```bash
# Set your variables
$BUCKET   = "YOUR_BUCKET_NAME"
$JOB_NAME = "handson-etl-job"
$DATABASE = "handson_data_lake"

Write-Host "=== VERIFICATION: Project 9.2 Glue ETL ===" -ForegroundColor Cyan

# CHECK 1 — Glue job exists
Write-Host "`n[1] Checking Glue job..."
aws glue get-job --job-name $JOB_NAME `
  --query "Job.{Name:Name,Version:GlueVersion,Workers:NumberOfWorkers,Type:WorkerType}" `
  --output table
# Expected: table row with handson-etl-job, 4.0, 2, G.1X

# CHECK 2 — ETL script in S3
Write-Host "`n[2] Checking ETL script in S3..."
aws s3 ls s3://$BUCKET/scripts/etl_job.py
# Expected: date, size, filename

# CHECK 3 — Last job run status
Write-Host "`n[3] Checking last job run..."
aws glue get-job-runs --job-name $JOB_NAME `
  --query "JobRuns[0].{State:JobRunState,Duration:ExecutionTime,Started:StartedOn}" `
  --max-results 1
# Expected: State=SUCCEEDED

# CHECK 4 — Parquet output in S3
Write-Host "`n[4] Checking processed Parquet files..."
aws s3 ls s3://$BUCKET/processed/orders/ --recursive | Select-Object -First 5
# Expected: .parquet files with year=XXXX/month=XX/ paths

# CHECK 5 — Trigger exists
Write-Host "`n[5] Checking Glue trigger..."
aws glue get-trigger --name "handson-etl-daily" `
  --query "Trigger.{Name:Name,Type:Type,Schedule:Schedule,State:State}"
# Expected: CREATED state (not ACTIVATED during learning)

# CHECK 6 — Athena query on processed data
Write-Host "`n[6] Running Athena verification query..."
$QID = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) as record_count FROM orders" `
  --query-execution-context Database=$DATABASE `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text

Start-Sleep 10  # Wait for query
aws athena get-query-results --query-execution-id $QID `
  --query "ResultSet.Rows[1].Data[0].VarCharValue"
# Expected: a number > 0 (e.g., "998")

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

---

### 7.3 Terraform State Verification

```bash
cd terraform

# List all managed resources
terraform state list
# Expected:
# aws_glue_job.etl
# aws_glue_trigger.daily
# aws_s3_object.etl_script

# Confirm no configuration drift
terraform plan -var="data_lake_bucket=YOUR_BUCKET" `
              -var="glue_role_arn=YOUR_ROLE_ARN" `
              -var="database_name=handson_data_lake"
# Expected last line:
# No changes. Your infrastructure matches the configuration.
```

---

### 7.4 Data Quality Validation

```bash
# Verify no nulls in critical columns (run in Athena)
$QID = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM orders WHERE order_id IS NULL OR amount IS NULL" `
  --query-execution-context Database=$DATABASE `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text

Start-Sleep 10
$NULL_COUNT = aws athena get-query-results --query-execution-id $QID `
  --query "ResultSet.Rows[1].Data[0].VarCharValue" --output text

if ($NULL_COUNT -eq "0") {
    Write-Host "✅ No nulls in key columns" -ForegroundColor Green
} else {
    Write-Host "⚠️  Found $NULL_COUNT null rows" -ForegroundColor Yellow
}
```

---

### 7.5 Expected Successful Outputs Summary

**After `terraform apply`:**
```
Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
Outputs:
  glue_job_name     = "handson-etl-job"
  glue_trigger_name = "handson-etl-daily"
```

**After `aws glue start-job-run`:**
```json
{ "JobRunId": "jr_abc123def456ghi789" }
```

**After job completes (`get-job-run`):**
```json
{
    "State": "SUCCEEDED",
    "Duration": 387,
    "Error": null
}
```

**S3 output structure:**
```
processed/orders/year=2024/month=01/part-00000.parquet
processed/orders/year=2024/month=02/part-00000.parquet
processed/orders_daily/year=2024/month=01/part-00000.parquet
```

**Athena revenue query result:**
```
product    | orders | revenue
-----------+--------+---------
WIDGET     | 150    | 15823.50
GADGET     | 142    | 14219.00
DOOHICKEY  | 138    | 13891.00
```

---

## 8. OBSERVATIONS & LEARNING NOTES

### 8.1 What to Observe During Execution

**During STARTING state (0–2 min):**
- AWS provisions EC2 instances in a managed account (invisible to you)
- Spark master/worker processes start up
- Your S3 script is downloaded to the worker nodes
- You cannot SSH into Glue workers — fully managed

**During RUNNING state (2–10 min):**
- Go to CloudWatch → Log Groups → `/aws-glue/jobs/output`
- Find the log stream for your run ID
- Watch your `print()` statements appear in real-time
- You'll see: "Reading raw orders data... Raw record count: X... Transforming..."

**After SUCCEEDED:**
- Go to S3 → processed/orders/ — partition folders created immediately
- Glue Bookmark state is saved in AWS-managed DynamoDB (not visible to you)
- CloudWatch Metrics → Glue → namespace — check executor memory, CPU utilization

### 8.2 Internal AWS Behavior

```
Your API call → Glue Control Plane → allocates EC2 workers
                                   → assigns IAM role
                                   → mounts EBS volumes
                                   → starts JVM processes
                                   → runs your PySpark code
                                   → S3 writes go via VPC endpoint (if configured)
                                   → workers terminated immediately after job
                                   → billing stops at termination
```

Key insight: **You are billed from the moment workers are allocated to the moment they terminate** — even the STARTING time (2 min) is billed. This is why job timeout matters.

### 8.3 Resource Dependencies

```
aws_s3_object.etl_script
    ↓ (must exist before job can reference it)
aws_glue_job.etl
    ↓ (must exist before trigger can reference it)
aws_glue_trigger.daily
```

Terraform automatically detects this dependency chain from the `aws_glue_job.etl.name` reference in the trigger resource.

### 8.4 Networking Observations
- Glue workers run in an AWS-managed VPC by default
- For this project: no VPC configuration needed (public S3 access works)
- In production: connect Glue to your VPC for private database access (Glue Connection)
- S3 access goes over public internet unless VPC endpoint configured

### 8.5 Billing Observations
- Go to AWS Cost Explorer (Billing → Cost Explorer) after your first run
- Filter by Service = "AWS Glue" to see actual DPU-hour charges
- A 10-minute run with 2 × G.1X workers typically shows ~$0.14–$0.16
- The `aws_glue_trigger.daily` in CREATED state (not ACTIVATED) does NOT incur cost
- Cost only accrues when the job actually RUNS

### 8.6 Performance Observations
- First run: ~8–12 min (worker startup overhead dominates)
- Subsequent runs on same data: ~5–8 min (bookmark skips already-processed files)
- If you run with larger data (1GB+): worker startup is still 2 min but job execution scales linearly
- Parquet Snappy compression: expect ~70–80% size reduction vs CSV
- Athena query on partitioned Parquet is ~10x faster than unpartitioned CSV

---

## 9. SCREENSHOTS GUIDANCE

Create a `screenshots/` folder in the project and save screenshots in order:

### Before Implementation
| # | What to Capture | Why |
|---|----------------|-----|
| SS-01 | IAM → Roles → your Glue role details | Confirm role exists with correct permissions |
| SS-02 | S3 bucket showing `raw/orders/` CSV files | Baseline — raw data is present |
| SS-03 | Glue → ETL Jobs → empty list | Before state — no jobs yet |

### During Setup (Console)
| # | What to Capture | Why |
|---|----------------|-----|
| SS-04 | S3 upload screen with `etl_job.py` ready | Script being uploaded |
| SS-05 | Glue job creation — Job details tab filled | Shows all configuration values |
| SS-06 | Glue job creation — Parameters section | Shows all 7 job parameters |
| SS-07 | Job saved — success banner | Confirms job created successfully |
| SS-08 | Job run started — notification with Run ID | Proof of execution start |
| SS-09 | Job run in RUNNING state | Shows active execution with timer |

### After Deployment
| # | What to Capture | Why |
|---|----------------|-----|
| SS-10 | Job run SUCCEEDED — Runs tab | Key success proof |
| SS-11 | CloudWatch logs — "ETL job complete!" line | Shows script ran to completion |
| SS-12 | S3 processed/orders/ partition folders | Output data structure |
| SS-13 | S3 drill-down — actual .parquet file | Confirms file format |
| SS-14 | Glue trigger created (CREATED state) | Scheduling infrastructure |

### Validation
| # | What to Capture | Why |
|---|----------------|-----|
| SS-15 | Athena query results — product revenue | End-to-end proof: Parquet is queryable |
| SS-16 | Terraform apply output in terminal | IaC deployment proof |
| SS-17 | `terraform state list` output | State management proof |

### Error Screenshots (if encountered)
| # | What to Capture | Why |
|---|----------------|-----|
| SS-E1 | CloudWatch logs — error message | For troubleshooting reference |
| SS-E2 | Job run FAILED state | Documents the failure |

---

## 10. CLEANUP STEPS

> Always clean up after each learning session to avoid unnecessary charges.
> The Glue trigger costs nothing when CREATED but WILL cost money if ACTIVATED and running daily.

### 10.1 Terraform Destroy (Recommended — destroys all 3 resources)

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl\terraform

terraform destroy \
  -var="data_lake_bucket=YOUR_BUCKET" \
  -var="glue_role_arn=YOUR_ROLE_ARN" \
  -var="database_name=handson_data_lake"

# Confirm with "yes" when prompted
# Expected output:
# aws_glue_trigger.daily: Destroying...
# aws_glue_trigger.daily: Destruction complete after 2s
# aws_glue_job.etl: Destroying...
# aws_glue_job.etl: Destruction complete after 3s
# aws_s3_object.etl_script: Destroying...
# aws_s3_object.etl_script: Destruction complete after 1s
#
# Destroy complete! Resources: 3 destroyed.
```

### 10.2 AWS Console Cleanup

1. **Disable Trigger first (if activated):**
   - Glue → Triggers → click `handson-etl-daily` → Actions → Stop trigger

2. **Delete Trigger:**
   - Glue → Triggers → select `handson-etl-daily` → Actions → Delete trigger → Confirm

3. **Delete Glue Job:**
   - Glue → ETL Jobs → select `handson-etl-job` → Actions → Delete → Confirm

4. **Delete S3 Script:**
   - S3 → your bucket → `scripts/` → check `etl_job.py` → Delete → Confirm

5. **Clean processed output (optional — saves S3 storage cost):**
   - S3 → your bucket → select `processed/` → Delete

6. **Clean CloudWatch Logs (optional):**
   - CloudWatch → Log groups → `/aws-glue/jobs/output` → Delete log group

### 10.3 AWS CLI Cleanup

```bash
# 1. Stop trigger (if active)
aws glue stop-trigger --name "handson-etl-daily"

# 2. Delete trigger
aws glue delete-trigger --name "handson-etl-daily"
# Expected: { "Name": "handson-etl-daily" }

# 3. Delete Glue job
aws glue delete-job --job-name "handson-etl-job"
# Expected: { "JobName": "handson-etl-job" }

# 4. Delete ETL script from S3
aws s3 rm s3://$BUCKET/scripts/etl_job.py
# Expected: delete: s3://bucket/scripts/etl_job.py

# 5. Remove processed output (optional)
aws s3 rm s3://$BUCKET/processed/ --recursive
# Expected: delete: s3://bucket/processed/orders/year=2024/...

# 6. Verify cleanup
aws glue get-job --job-name "handson-etl-job" 2>&1
# Expected: An error occurred (EntityNotFoundException) — job no longer exists
```

### 10.4 Cost Verification After Cleanup

```bash
# Check Cost Explorer for Glue charges
# (CLI — requires ce:GetCostAndUsage permission)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS Glue"]}}' \
  --metrics "UnblendedCost" \
  --query "ResultsByTime[*].{Date:TimePeriod.Start,Cost:Total.UnblendedCost.Amount}"

# Or: AWS Console → Billing → Cost Explorer → filter by Service = "AWS Glue"
# Expected after cleanup: charges stop accruing from deletion date
```

### 10.5 What Cleanup Does NOT Delete

These resources from Project 9.1 remain — they are not managed by 9.2's Terraform:
- S3 data lake bucket (bucket itself, raw/ data)
- Glue IAM role
- Glue Data Catalog database
- Glue Catalog tables (from Crawler in 9.1)

To delete these, run `terraform destroy` in `project_9.1_data_lake/terraform/`.

---

## QUICK REFERENCE CARD

```
DEPLOY:
  terraform apply -var="data_lake_bucket=X" -var="glue_role_arn=Y" -var="database_name=Z"

RUN JOB:
  aws glue start-job-run --job-name handson-etl-job

MONITOR:
  aws glue get-job-run --job-name handson-etl-job --run-id RUN_ID --query "JobRun.JobRunState"

VERIFY OUTPUT:
  aws s3 ls s3://BUCKET/processed/orders/ --recursive

DESTROY:
  terraform destroy -var="data_lake_bucket=X" -var="glue_role_arn=Y" -var="database_name=Z"

COST: ~$0.15 per 10-min run | G.1X = $0.44/DPU-hour | NOT free tier
```
