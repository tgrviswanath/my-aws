# Steps — Project 9.2 Glue ETL Pipeline

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="data_lake_bucket=$(cd ../../project_9.1_data_lake/terraform && terraform output -raw data_lake_bucket)" \
  -var="glue_role_arn=$(cd ../../project_9.1_data_lake/terraform && terraform output -raw glue_role_arn)" \
  -var="database_name=$(cd ../../project_9.1_data_lake/terraform && terraform output -raw glue_database)"
```

---

## Phase 2 — Run ETL Job

```bash
JOB_NAME=$(terraform output -raw glue_job_name)

# Start job run
RUN_ID=$(aws glue start-job-run \
  --job-name $JOB_NAME \
  --query "JobRunId" --output text)

echo "Job run ID: $RUN_ID"

# Monitor progress
watch -n 10 "aws glue get-job-run \
  --job-name $JOB_NAME \
  --run-id $RUN_ID \
  --query 'JobRun.{State:JobRunState,Duration:ExecutionTime,Error:ErrorMessage}'"
```

---

## Phase 3 — Verify Output

```bash
BUCKET=$(cd ../../project_9.1_data_lake/terraform && terraform output -raw data_lake_bucket)

# Check processed files
aws s3 ls s3://$BUCKET/processed/orders/ --recursive

# Verify Parquet files created
aws s3 ls s3://$BUCKET/processed/orders/year=2024/month=01/

# Query with Athena
aws athena start-query-execution \
  --query-string "SELECT product, SUM(amount) as revenue FROM orders GROUP BY product ORDER BY revenue DESC" \
  --work-group handson-data-lake \
  --query-execution-context Database=handson_data_lake \
  --query "QueryExecutionId" --output text
```

---

## Phase 4 — View Job Metrics

```
1. AWS Console → Glue → Jobs → handson-etl-job
2. Click on a job run → see:
   - Duration
   - DPU hours used
   - Records read/written
   - Errors
3. CloudWatch → Metrics → Glue → see Spark metrics
```

---

## Screenshots to Take
- [ ] Glue job created in console
- [ ] Job run in progress (RUNNING state)
- [ ] Job completed successfully
- [ ] Processed Parquet files in S3
- [ ] Athena query on processed data returning results
- [ ] Job metrics showing DPU usage
