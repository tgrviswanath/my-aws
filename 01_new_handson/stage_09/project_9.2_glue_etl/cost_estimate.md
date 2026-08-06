# Cost Estimate — Project 9.2: AWS Glue ETL

## Glue Pricing (us-east-1, as of 2024)

| Resource | Price | Notes |
|----------|-------|-------|
| Glue ETL job (DPU-hour) | $0.44 / DPU-hour | Minimum 2 DPU, 10-min minimum |
| Glue Crawler | $0.44 / DPU-hour | Typically 1 DPU |
| Glue Catalog | $1.00 / 100K objects/month | First 1M objects free |
| Glue DataBrew | $1.00 / DPU-hour | Different from ETL |
| Glue Studio Visual | $0.44 / DPU-hour | Same as ETL jobs |
| Glue Development Endpoint | $0.44 / DPU-hour | For interactive development |

**Worker types (ETL jobs):**
| Worker | vCPUs | RAM | Price/hour |
|--------|-------|-----|----------|
| Standard | 4 | 16 GB | $0.44 × 2 DPU = $0.88 |
| G.1X | 4 | 16 GB | $0.44 × 2 DPU = $0.88 |
| G.2X | 8 | 32 GB | $0.44 × 4 DPU = $1.76 |
| G.4X | 16 | 64 GB | $0.44 × 8 DPU = $3.52 |
| G.025X (Flex) | 1 | 4 GB | $0.44 × 0.5 DPU = $0.22 |

---

## Free Tier

**Glue has NO free tier.**

Every job run incurs charges immediately:
- Minimum billing: 10 minutes per job run
- Minimum workers: 2 (for Standard/G.1X)

---

## Scenario Estimates

### Single Job Run (this learning project)
| Item | Duration | Monthly Cost |
|------|----------|-------------|
| 1 Glue ETL job (2 DPU × G.1X) | 10 min (minimum) | $0.15 |
| 1 Glue Crawler run | 10 min (1 DPU) | $0.07 |
| Glue Catalog (tables) | 5 tables | $0.00 (free) |
| S3 storage (test data) | < 1 GB | $0.02 |
| **Total** | | **~$0.24 per run** |

### Daily ETL Job (small dataset, 30 min/run)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Daily ETL (2 DPU × G.1X × 30 min × 30 days) | 30 hours DPU | $13.20 |
| Daily Crawler (1 DPU × 10 min × 30 days) | 5 hours | $2.20 |
| Glue Catalog | 50 tables | $0.00 |
| S3 storage (10 GB processed data) | 10 GB | $0.23 |
| **Total** | | **~$15.63/month** |

### Production ETL (hourly, 1 hour runs, 8 workers)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Hourly ETL (16 DPU × G.1X × 1hr × 24hr × 30 days) | 11,520 DPU-hours | $5,068.80 |
| Crawlers (hourly) | 720 DPU-hours | $316.80 |
| Glue Catalog | 1,000 tables | $0.00 |
| **Total** | | **~$5,385/month** |

---

## Cost Optimization Strategies

### 1. Use Flex Execution (G.025X) for Non-Urgent Jobs
```bash
aws glue create-job \
  --name "customers-csv-to-parquet-flex" \
  --worker-type "G.025X" \
  --number-of-workers 2 \
  # Cost: 50% less than G.1X for same data
```

### 2. Job Bookmarks Prevent Reprocessing
```bash
# With bookmark: only processes new files (saves DPU-hours)
"--job-bookmark-option": "job-bookmark-enable"
```

### 3. Optimize with Pushdown Predicates
```python
# Only read new partitions — avoid full S3 scan
push_down_predicate = "year='2024' and month='01' and day='15'"
raw_dyf = glueContext.create_dynamic_frame.from_catalog(
    database="myapp_db",
    table_name="raw_customers",
    push_down_predicate=push_down_predicate
)
```

### 4. Auto Scaling (Glue 3.0+)
```bash
aws glue create-job \
  --name "my-job" \
  --auto-scaling-enabled  # Scales workers based on actual data volume
```

---

## Glue vs EMR vs Databricks Cost Comparison

| Service | 2 DPU, 1 hour | 16 DPU, 1 hour |
|---------|--------------|----------------|
| AWS Glue | $0.88 | $7.04 |
| EMR on EC2 (r5.xlarge) | ~$0.60 | ~$2.50 |
| Databricks (DBU pricing) | ~$0.50 | ~$2.00 |

**Glue is most expensive per DPU-hour** but includes:
- No cluster management
- Built-in Glue Catalog integration
- Job Bookmarks
- Automatic schema evolution

---

## Total

| Scenario | Per Run | Monthly (daily) | Annual |
|----------|---------|-----------------|--------|
| Learning (1-2 runs) | $0.24 | — | ~$3-5 total |
| Daily small ETL (30 min) | $0.51 | ~$15.63 | ~$188 |
| Hourly large ETL | ~$179/day | ~$5,385 | ~$64,620 |

**For this learning project:** Budget $5-20 total for all test runs.

---

## Cleanup

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DATA_BUCKET="glue-etl-data-${ACCOUNT_ID}"
SCRIPTS_BUCKET="glue-etl-scripts-${ACCOUNT_ID}"

# Cancel any running jobs first
RUNNING_JOBS=$(aws glue get-job-runs \
  --job-name "customers-csv-to-parquet" \
  --query 'JobRuns[?JobRunState==`RUNNING`].Id' \
  --output text)

for RUN_ID in $RUNNING_JOBS; do
  aws glue batch-stop-job-run \
    --job-name "customers-csv-to-parquet" \
    --job-run-ids "$RUN_ID"
done

# Delete Glue resources
aws glue delete-job --job-name "customers-csv-to-parquet" 2>/dev/null
aws glue delete-crawler --name "customers-processed-crawler" 2>/dev/null
aws glue delete-database --name "myapp_db" 2>/dev/null

# Delete S3 data
aws s3 rm s3://${DATA_BUCKET} --recursive
aws s3 rb s3://${DATA_BUCKET}
aws s3 rm s3://${SCRIPTS_BUCKET} --recursive
aws s3 rb s3://${SCRIPTS_BUCKET}

# Delete IAM role
aws iam detach-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
aws iam delete-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-name GlueS3Access
aws iam delete-role --role-name AWSGlueServiceRoleDefault

echo "Cleanup complete — billing stops when jobs are deleted"
echo "Note: Charges for running jobs stop when job run completes, not on deletion"
```

**Important billing note:** Glue charges per DPU-second of actual job execution. Deleting the job doesn't cancel charges for already-completed runs.
