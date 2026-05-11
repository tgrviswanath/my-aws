# Steps — Project 9.4 Spark Processing on EMR

## Phase 1 — Use EMR Serverless (Recommended for Learning)

```bash
# Create EMR Serverless application
aws emr-serverless create-application \
  --name handson-spark \
  --type SPARK \
  --release-label emr-6.15.0

APP_ID=$(aws emr-serverless list-applications \
  --query "applications[?name=='handson-spark'].id" --output text)

# Upload Spark script
BUCKET="your-data-lake-bucket"
aws s3 cp src/spark_job.py s3://$BUCKET/scripts/spark_job.py
```

---

## Phase 2 — Submit Spark Job

```bash
# Create IAM role for EMR Serverless
# (see terraform/main.tf)

# Submit job
JOB_RUN_ID=$(aws emr-serverless start-job-run \
  --application-id $APP_ID \
  --execution-role-arn $EMR_ROLE_ARN \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://'$BUCKET'/scripts/spark_job.py",
      "entryPointArguments": [
        "--input", "s3://'$BUCKET'/raw/orders/",
        "--output", "s3://'$BUCKET'/processed/spark/"
      ],
      "sparkSubmitParameters": "--conf spark.executor.cores=2 --conf spark.executor.memory=4g"
    }
  }' \
  --query "jobRunId" --output text)

echo "Job run ID: $JOB_RUN_ID"
```

---

## Phase 3 — Monitor Job

```bash
# Check status
aws emr-serverless get-job-run \
  --application-id $APP_ID \
  --job-run-id $JOB_RUN_ID \
  --query "jobRun.{State:state,Duration:updatedAt}"

# View logs (after job completes)
aws s3 ls s3://$BUCKET/logs/applications/$APP_ID/jobs/$JOB_RUN_ID/
```

---

## Phase 4 — Query Results with Athena

```bash
# Run Glue Crawler on Spark output
aws glue start-crawler --name handson-raw-crawler

# Query product monthly data
aws athena start-query-execution \
  --query-string "SELECT product, SUM(total_revenue) as revenue FROM product_monthly GROUP BY product ORDER BY revenue DESC" \
  --work-group handson-data-lake \
  --query-execution-context Database=handson_data_lake \
  --query "QueryExecutionId" --output text
```

---

## Screenshots to Take
- [ ] EMR Serverless application created
- [ ] Spark job submitted and running
- [ ] Job completed successfully
- [ ] Output Parquet files in S3
- [ ] Athena query on Spark output
- [ ] Job metrics (vCPU-hours, memory-hours used)
