# Verification & Validation — Project 9.2 Glue ETL Pipeline

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Glue Job | Glue → ETL Jobs | `handson-etl-job` listed |
| Job Script | Glue → ETL Jobs → Script tab | PySpark script visible |
| Job Run | Glue → ETL Jobs → Run history | Last run Status = **Succeeded** |
| Output in S3 | S3 → data lake bucket → processed/ | Parquet files with year/month/day partitions |
| Glue Table | Glue → Tables → processed_db | `orders` table with Parquet format |
| Job Bookmarks | Glue → ETL Jobs → Job details | Bookmarks enabled |
| CloudWatch Logs | CloudWatch → Log Groups | `/aws-glue/jobs/output` log group |

📸 Screenshot: Glue job run history showing Succeeded status  
📸 Screenshot: S3 processed/ prefix with Parquet partitions  
📸 Screenshot: Athena query on processed table returning results

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm Glue job exists
aws glue get-job \
  --job-name handson-etl-job \
  --query "Job.{Name:Name,Role:Role,MaxDPU:MaxCapacity,Bookmarks:JobBookmarksEncryption}"
# Expected: job details returned

# 2.2 Upload ETL script to S3 (if not already done)
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
aws s3 cp src/etl_job.py s3://$BUCKET/scripts/etl_job.py
echo "Script uploaded"

# 2.3 Run the Glue job
RUN_ID=$(aws glue start-job-run \
  --job-name handson-etl-job \
  --query "JobRunId" --output text)
echo "Job run ID: $RUN_ID"

# 2.4 Monitor job status
for i in {1..20}; do
  STATUS=$(aws glue get-job-run \
    --job-name handson-etl-job \
    --run-id $RUN_ID \
    --query "JobRun.JobRunState" --output text)
  echo "Status: $STATUS"
  [ "$STATUS" = "SUCCEEDED" ] && break
  [ "$STATUS" = "FAILED" ] && echo "❌ Job failed!" && break
  sleep 30
done
# Expected: SUCCEEDED

# 2.5 Confirm Parquet output in S3
aws s3 ls s3://$BUCKET/processed/orders/ --recursive | head -10
# Expected: .parquet files with year=XXXX/month=XX/day=XX partitions

# 2.6 Verify output is queryable via Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total, SUM(amount) as revenue FROM processed_db.orders;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[*].VarCharValue" --output table
# Expected: total count and revenue sum

# 2.7 Check job run metrics
aws glue get-job-run \
  --job-name handson-etl-job \
  --run-id $RUN_ID \
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime,DPU:MaxCapacity,RowsRead:Statistics}"
# Expected: State=SUCCEEDED, Duration in seconds
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_glue_job.etl
# aws_iam_role.glue
# aws_iam_role_policy_attachment.glue_service
# aws_iam_role_policy.glue_s3

terraform state show aws_glue_job.etl
# Shows: name, role_arn, max_capacity, command.script_location

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — ETL Output Validation

```bash
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')

# Count output files
FILE_COUNT=$(aws s3 ls s3://$BUCKET/processed/orders/ --recursive | grep ".parquet" | wc -l)
echo "Parquet files created: $FILE_COUNT"
# Expected: > 0

# Verify partitioning structure
aws s3 ls s3://$BUCKET/processed/orders/ | head -5
# Expected: year=XXXX/ directories

# Verify no nulls in key columns via Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM processed_db.orders WHERE order_id IS NULL OR amount IS NULL;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
NULL_COUNT=$(aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue" --output text)
echo "Null rows: $NULL_COUNT"
[ "$NULL_COUNT" = "0" ] && echo "✅ No nulls in key columns" || echo "⚠️ Nulls found: $NULL_COUNT"
```

---

## 5. Expected Successful Outputs

**CLI — get-job-run:**
```json
{ "State": "SUCCEEDED", "Duration": 45, "DPU": 2.0 }
```

**Athena query on processed table:**
```
| total | revenue  |
|-------|----------|
| 1000  | 49823.50 |
```

**S3 output structure:**
```
processed/orders/year=2024/month=01/day=15/part-00000.parquet
processed/orders/year=2024/month=01/day=16/part-00000.parquet
```

---

## 6. Verification Checklist

- [ ] Glue job `handson-etl-job` exists
- [ ] ETL script uploaded to S3 scripts/ prefix
- [ ] Job run completes with State = SUCCEEDED
- [ ] Parquet files exist in processed/ with year/month/day partitions
- [ ] Athena query on processed_db.orders returns rows
- [ ] No null values in key columns (order_id, amount)
- [ ] Job bookmarks enabled (prevents reprocessing)
- [ ] CloudWatch logs for job run accessible
- [ ] `terraform plan` shows no changes
