# Steps — Project 9.2 Glue ETL Pipeline

> **Prerequisite:** Project 9.1 must be deployed. Get values with:
> ```bash
> cd ../project_9.1_data_lake/terraform && terraform output
> ```

---

## Phase 1 — Deploy

```bash
cd terraform

# Option A: Pass variables inline (replace with your values from Project 9.1)
terraform init
terraform apply \
  -var="data_lake_bucket=handson-data-lake-ACCOUNT_ID" \
  -var="glue_role_arn=arn:aws:iam::ACCOUNT_ID:role/handson-glue-role-ACCOUNT_ID" \
  -var="database_name=handson_data_lake"

# Option B: Use terraform.tfvars (fill in terraform/terraform.tfvars first)
terraform apply -var-file=terraform.tfvars

# Confirm 3 resources created
terraform state list
# Expected:
# aws_glue_job.etl
# aws_glue_trigger.daily
# aws_s3_object.etl_script

# Get outputs
terraform output
# Key outputs: glue_job_name, etl_script_s3_path, processed_output_path
```

---

## Phase 2 — Verify Script Was Uploaded to S3

```bash
BUCKET=$(terraform output -raw etl_script_s3_path | cut -d'/' -f3)

# Confirm script is in S3
aws s3 ls s3://$BUCKET/scripts/
# Expected: etl_job.py listed

# Confirm raw data exists to process (from Project 9.1)
aws s3 ls s3://$BUCKET/raw/orders/ --recursive | head -5
# Expected: orders.csv file(s) listed
```

---

## Phase 3 — Run ETL Job

```bash
JOB_NAME=$(terraform output -raw glue_job_name)
# Value: handson-etl-job

# Start job run
RUN_ID=$(aws glue start-job-run \
  --job-name $JOB_NAME \
  --query "JobRunId" --output text)

echo "Job run ID: $RUN_ID"

# Monitor status (poll every 30 seconds)
while true; do
  STATUS=$(aws glue get-job-run \
    --job-name $JOB_NAME \
    --run-id $RUN_ID \
    --query "JobRun.{State:JobRunState,Duration:ExecutionTime,Error:ErrorMessage}" \
    --output json)
  echo "$(date): $STATUS"
  STATE=$(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin)['State'])")
  [ "$STATE" = "SUCCEEDED" ] && echo "✅ Job succeeded!" && break
  [ "$STATE" = "FAILED" ]    && echo "❌ Job failed! Check logs." && break
  sleep 30
done
```

---

## Phase 4 — Verify Output

```bash
BUCKET=$(terraform output -raw etl_script_s3_path | cut -d'/' -f3)

# Check both output prefixes created by the ETL job
echo "=== Cleaned orders ==="
aws s3 ls s3://$BUCKET/processed/orders/ --recursive | head -10
# Expected: part-*.parquet files under year=XXXX/month=XX/

echo "=== Daily aggregates ==="
aws s3 ls s3://$BUCKET/processed/orders_daily/ --recursive | head -10
# Expected: part-*.parquet files under year=XXXX/month=XX/

# Verify Parquet files exist (not empty)
PARQUET_COUNT=$(aws s3 ls s3://$BUCKET/processed/orders/ --recursive | grep ".parquet" | wc -l)
echo "Parquet files created: $PARQUET_COUNT"
# Expected: > 0
```

---

## Phase 5 — Query with Athena

```bash
# Register new partitions in Glue Data Catalog
# (required when new year/month partitions are created)
QUERY_ID=$(aws athena start-query-execution \
  --query-string "MSCK REPAIR TABLE orders;" \
  --query-execution-context Database=handson_data_lake \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID
echo "Partitions registered"

# Query processed orders
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT product, COUNT(*) as orders, SUM(amount) as revenue FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 10;" \
  --query-execution-context Database=handson_data_lake \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID

aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" \
  --output table
# Expected: product names with order counts and revenue
```

---

## Phase 6 — View Job Logs

```bash
# View CloudWatch logs for the job run
aws logs tail /aws-glue/jobs/output --follow

# Or filter by job run ID
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --filter-pattern "$RUN_ID" \
  --query "events[*].message" \
  --output text

# Expected log lines:
# Reading raw orders data...
# Raw record count: 10
# Transforming data...
# Clean record count: 10
# Writing processed data to S3...
# ETL job complete!
```

---

## Phase 7 — Check Job Metrics (Console)

```
1. AWS Console → Glue → ETL Jobs → handson-etl-job
2. Click on a job run → "Run metrics" tab → see:
   - Execution time
   - DPU hours (cost indicator)
   - Records read / written
   - Shuffle read / write bytes
3. CloudWatch → Metrics → Glue → filter by job name
```

---

## Phase 8 — Test Bookmark (Run Again)

```bash
# Run the job a second time with same data
RUN_ID2=$(aws glue start-job-run \
  --job-name $JOB_NAME \
  --query "JobRunId" --output text)

# Wait for completion then check
aws glue get-job-run \
  --job-name $JOB_NAME \
  --run-id $RUN_ID2 \
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime}"

# Because bookmark is enabled, the second run processes 0 new records
# (same files — already bookmarked). Duration will be very short (~1-2 min).
```

---

## Screenshots to Take
- [ ] Terraform apply output showing 3 resources created
- [ ] Glue job `handson-etl-job` in console (Details tab showing script path, workers)
- [ ] Job run in RUNNING state (progress bar visible)
- [ ] Job run SUCCEEDED (Run history tab)
- [ ] Job metrics: DPU usage chart
- [ ] S3 `processed/orders/` showing `year=XXXX/month=XX/` partition structure
- [ ] S3 `processed/orders_daily/` showing daily aggregates
- [ ] CloudWatch logs showing ETL print statements
- [ ] Athena query returning results from processed data
- [ ] Second run: short duration confirming bookmark worked
