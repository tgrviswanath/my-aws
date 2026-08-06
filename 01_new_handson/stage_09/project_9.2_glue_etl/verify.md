# Verification & Validation — Project 9.2 Glue ETL Pipeline

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ETL Script in S3 | S3 → data lake bucket → scripts/ | `etl_job.py` object present |
| Glue Job | Glue → ETL Jobs | `handson-etl-job` listed |
| Job Script | Glue → ETL Jobs → `handson-etl-job` → Script tab | PySpark code visible |
| Job Details | Glue → ETL Jobs → `handson-etl-job` → Details tab | Workers: 2 × G.1X, Version: 4.0 |
| Job Arguments | Details tab → Job parameters | `--source_bucket`, `--target_bucket`, `--database_name`, `--TempDir` all present |
| Bookmark setting | Details tab → Advanced properties | Job bookmarks = **Enabled** |
| Job Run | Glue → ETL Jobs → `handson-etl-job` → Runs tab | Last run Status = **Succeeded** |
| Output — orders | S3 → bucket → processed/orders/ | Parquet files with `year=XXXX/month=XX/` partitions |
| Output — daily | S3 → bucket → processed/orders_daily/ | Parquet files with `year=XXXX/month=XX/` partitions |
| CloudWatch Logs | CloudWatch → Log Groups → `/aws-glue/jobs/output` | Log streams from job runs present |
| Daily Trigger | Glue → Triggers | `handson-etl-daily`, Type = SCHEDULED, Status = **CREATED** (not ACTIVATED) |

📸 Screenshot: Glue job `handson-etl-job` Details tab showing script S3 path, worker type, version  
📸 Screenshot: Job run Runs tab showing Succeeded status with execution time  
📸 Screenshot: S3 `processed/orders/` with year/month partition folders  
📸 Screenshot: S3 `processed/orders_daily/` with daily aggregates  
📸 Screenshot: CloudWatch log stream showing ETL print output  
📸 Screenshot: Athena query on processed data returning rows  

---

## 2. AWS CLI Verification

```bash
# Set variables from Terraform outputs
cd terraform
BUCKET=$(terraform output -raw etl_script_s3_path | sed 's|s3://||' | cut -d'/' -f1)
JOB_NAME=$(terraform output -raw glue_job_name)
# JOB_NAME = handson-etl-job

# 2.1 ETL script uploaded to S3
aws s3 ls s3://$BUCKET/scripts/etl_job.py
# Expected: file listed with size ~4KB

# 2.2 Confirm Glue job exists and is correctly configured
aws glue get-job \
  --job-name $JOB_NAME \
  --query "Job.{Name:Name,GlueVersion:GlueVersion,Workers:NumberOfWorkers,WorkerType:WorkerType,Timeout:Timeout,Retries:MaxRetries}"
# Expected:
# Name=handson-etl-job, GlueVersion=4.0, Workers=2, WorkerType=G.1X, Timeout=60, Retries=1

# 2.3 Confirm bookmark is enabled
aws glue get-job \
  --job-name $JOB_NAME \
  --query "Job.DefaultArguments" --output json | python3 -c "
import sys, json
args = json.load(sys.stdin)
bookmark = args.get('--job-bookmark-option', 'NOT SET')
print(f'Bookmark: {bookmark}')
assert bookmark == 'job-bookmark-enable', 'Bookmark not enabled!'
print('✅ Bookmark enabled')
"

# 2.4 Confirm raw data exists to process
aws s3 ls s3://$BUCKET/raw/orders/ --recursive | head -5
# Expected: orders.csv file(s) from Project 9.1

# 2.5 Start job run and wait for completion
RUN_ID=$(aws glue start-job-run \
  --job-name $JOB_NAME \
  --query "JobRunId" --output text)
echo "Job run ID: $RUN_ID"

for i in $(seq 1 30); do
  STATUS=$(aws glue get-job-run \
    --job-name $JOB_NAME \
    --run-id $RUN_ID \
    --query "JobRun.JobRunState" --output text)
  echo "[$i] Status: $STATUS"
  [ "$STATUS" = "SUCCEEDED" ] && break
  [ "$STATUS" = "FAILED"    ] && echo "❌ Check /aws-glue/jobs/error log group" && break
  sleep 30
done
# Expected: SUCCEEDED (typical runtime 5-10 minutes)

# 2.6 Verify processed/orders/ output
aws s3 ls s3://$BUCKET/processed/orders/ --recursive
# Expected: year=XXXX/month=XX/part-XXXXX.parquet files

# 2.7 Verify processed/orders_daily/ output
aws s3 ls s3://$BUCKET/processed/orders_daily/ --recursive
# Expected: year=XXXX/month=XX/part-XXXXX.parquet files
# Note: orders_daily/ contains aggregated data (one row per product per day)

# 2.8 Confirm Parquet files are non-empty
for PREFIX in "processed/orders" "processed/orders_daily"; do
  COUNT=$(aws s3 ls s3://$BUCKET/$PREFIX/ --recursive | grep ".parquet" | wc -l)
  echo "$PREFIX: $COUNT Parquet file(s)"
done
# Expected: > 0 for both

# 2.9 Query processed data with Athena (using correct database from Project 9.1)
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total_orders, ROUND(SUM(amount), 2) as total_revenue FROM orders;" \
  --query-execution-context Database=handson_data_lake \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID

aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[*].VarCharValue" --output table
# Expected: total_orders (count) and total_revenue (sum) — both > 0

# 2.10 Verify no nulls in key columns (data quality check)
NULL_QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM orders WHERE order_id IS NULL OR amount IS NULL;" \
  --query-execution-context Database=handson_data_lake \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $NULL_QUERY_ID

NULL_COUNT=$(aws athena get-query-results \
  --query-execution-id $NULL_QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue" --output text)
echo "Null rows: $NULL_COUNT"
[ "$NULL_COUNT" = "0" ] && echo "✅ No nulls — ETL cleaned data correctly" || echo "⚠️ Nulls found: $NULL_COUNT"

# 2.11 Verify job run metrics
aws glue get-job-run \
  --job-name $JOB_NAME \
  --run-id $RUN_ID \
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime,MaxDPU:MaxCapacity,Error:ErrorMessage}"
# Expected: State=SUCCEEDED, Duration ~300-600 seconds, MaxDPU=2.0, Error=null
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_glue_job.etl
# aws_glue_trigger.daily
# aws_s3_object.etl_script

terraform state show aws_glue_job.etl
# Shows:
#   name             = "handson-etl-job"
#   glue_version     = "4.0"
#   number_of_workers = 2
#   worker_type      = "G.1X"
#   timeout          = 60
#   max_retries      = 1
#   default_arguments contains --job-bookmark-option = "job-bookmark-enable"
#   default_arguments contains --source_bucket, --target_bucket, --database_name, --TempDir

terraform state show aws_glue_trigger.daily
# Shows: name="handson-etl-daily", type=SCHEDULED, enabled=false

terraform state show aws_s3_object.etl_script
# Shows: bucket, key="scripts/etl_job.py"

terraform output
# Expected: glue_job_name, glue_trigger_name, etl_script_s3_path,
#           processed_output_path, daily_aggregates_path, start_job_command

terraform plan -var-file=terraform.tfvars
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — ETL Output Validation

```bash
BUCKET=$(cd terraform && terraform output -raw etl_script_s3_path | sed 's|s3://||' | cut -d'/' -f1)

# 4.1 Partition structure (year/month — NOT year/month/day at the partition level)
echo "=== Partition directories (orders) ==="
aws s3 ls s3://$BUCKET/processed/orders/
# Expected: year=XXXX/ directories

echo "=== Month directories ==="
aws s3 ls s3://$BUCKET/processed/orders/year=2024/
# Expected: month=01/ month=02/ etc.

# 4.2 Confirm both outputs exist
for PREFIX in "processed/orders" "processed/orders_daily"; do
  echo "--- $PREFIX ---"
  aws s3 ls s3://$BUCKET/$PREFIX/ | head -3
done

# 4.3 Check CloudWatch logs for successful ETL completion markers
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --filter-pattern "ETL job complete" \
  --query "events[*].message" \
  --output text | head -5
# Expected: "ETL job complete!" log line

# 4.4 Verify no error logs
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/error \
  --filter-pattern "Exception" \
  --query "events[*].message" \
  --output text | head -10
# Expected: empty (no exceptions)

# 4.5 Verify trigger is CREATED (not ACTIVATED — saves cost)
aws glue get-trigger \
  --name handson-etl-daily \
  --query "Trigger.{Name:Name,State:State,Schedule:Schedule}"
# Expected: State=CREATED (not ACTIVATED)
```

---

## 5. Expected Successful Outputs

**terraform output:**
```
glue_job_name        = "handson-etl-job"
glue_trigger_name    = "handson-etl-daily"
etl_script_s3_path   = "s3://handson-data-lake-ACCOUNT_ID/scripts/etl_job.py"
processed_output_path = "s3://handson-data-lake-ACCOUNT_ID/processed/orders/"
daily_aggregates_path = "s3://handson-data-lake-ACCOUNT_ID/processed/orders_daily/"
start_job_command    = "aws glue start-job-run --job-name handson-etl-job"
cost_per_run_estimate = "~$0.15 USD (2 workers x G.1X x 10min / 60min x $0.44/DPU-hr)"
```

**get-job-run after success:**
```json
{
  "State": "SUCCEEDED",
  "Duration": 450,
  "MaxDPU": 2.0,
  "Error": null
}
```

**S3 processed/ output structure:**
```
processed/
├── orders/
│   └── year=2024/
│       └── month=01/
│           └── part-00000.parquet    ← cleaned individual orders
└── orders_daily/
    └── year=2024/
        └── month=01/
            └── part-00000.parquet    ← daily aggregates by product
```

**CloudWatch log output (from print statements in etl_job.py):**
```
Reading raw orders data...
Raw record count: 10
Transforming data...
Clean record count: 10
Writing processed data to S3...
ETL job complete!
  Orders written to: s3://handson-data-lake-ACCOUNT_ID/processed/orders/
  Daily aggregates:  s3://handson-data-lake-ACCOUNT_ID/processed/orders_daily/
```

**Athena query result:**
```
| total_orders | total_revenue |
|-------------|---------------|
| 10          | 349.90        |
```

---

## 6. Verification Checklist

- [ ] ETL script `etl_job.py` uploaded to `s3://{bucket}/scripts/etl_job.py`
- [ ] Glue job `handson-etl-job` exists, version=4.0, workers=2×G.1X
- [ ] Job bookmark = `job-bookmark-enable` in default_arguments
- [ ] Job arguments include: `--source_bucket`, `--target_bucket`, `--database_name`, `--TempDir`
- [ ] Job run completes with State = SUCCEEDED
- [ ] `processed/orders/` has Parquet files with `year=XXXX/month=XX/` partitions
- [ ] `processed/orders_daily/` has Parquet files with `year=XXXX/month=XX/` partitions
- [ ] Athena query on `handson_data_lake.orders` returns rows (not empty)
- [ ] No null values in `order_id` or `amount` columns (ETL cleaned data)
- [ ] CloudWatch log group `/aws-glue/jobs/output` has log entries for the run
- [ ] Trigger `handson-etl-daily` exists with State = CREATED (not ACTIVATED)
- [ ] Second job run (same data) completes quickly — bookmark skips reprocessing
- [ ] `terraform plan` shows no changes after successful deployment

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
