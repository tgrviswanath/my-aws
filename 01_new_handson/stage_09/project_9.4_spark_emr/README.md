# Project 9.4 — Spark Processing on EMR Serverless

## What This Does

Runs a distributed PySpark job on AWS EMR Serverless. Reads large order CSV files from S3,
computes product revenue aggregates and customer lifetime value, and writes Parquet output
back to S3. Pay only for compute time — no idle cluster charges.

## Architecture

```
S3: raw/orders/*.csv   (input — any size CSV files)
    │
    │  aws emr-serverless start-job-run
    ▼
EMR Serverless: handson-spark  (emr-6.15.0 / Spark 3.4)
    │  Driver: 2 vCPU, 4 GB  |  Max: 20 vCPU, 40 GB  |  Auto-stop: 15 min
    │  src/spark_job.py runs on cluster
    │
    ├──▶ S3: processed/spark/product_monthly/year=YYYY/month=M/*.snappy.parquet
    └──▶ S3: processed/spark/customer_clv/*.snappy.parquet
```

## Resources Created

| Resource | Name | Type |
|----------|------|------|
| EMR Serverless App | `handson-spark` | emr-6.15.0, SPARK |
| IAM Role | `handson-emr-serverless-role` | Trust: emr-serverless.amazonaws.com |
| S3 object | `scripts/spark_job.py` | Uploaded from src/ |

## Quick Start (CLI — PowerShell)

```powershell
# Set variables
$BUCKET   = "your-data-lake-bucket"
$ROLE_ARN = "arn:aws:iam::ACCOUNT:role/handson-emr-serverless-role"
$APP_ID   = "app-XXXXXXXXXXXXXXXXXXXXXXXX"   # from create-application

# Upload script
aws s3 cp src\spark_job.py "s3://$BUCKET/scripts/spark_job.py"

# Start app, then submit job
aws emr-serverless start-application --application-id $APP_ID
aws emr-serverless start-job-run `
  --application-id $APP_ID `
  --execution-role-arn $ROLE_ARN `
  --job-driver "{`"sparkSubmit`":{`"entryPoint`":`"s3://$BUCKET/scripts/spark_job.py`",`"entryPointArguments`":[`"--input`",`"s3://$BUCKET/raw/orders/`",`"--output`",`"s3://$BUCKET/processed/spark/`"]}}"
```

## Source Files

| File | Purpose |
|------|---------|
| `src/spark_job.py` | PySpark job: reads CSV → cleans → aggregates → writes Parquet (2 outputs) |
| `docs/architecture.md` | EMR Serverless vs EC2, Spark internals, AQE, partitioning |
| `steps.md` | Quick-reference CLI commands (PowerShell) |
| `steps_awsconsoleui.md` | Console UI walkthrough (all steps) |
| `verify.md` | End-to-end verification checklist + CLI commands |
| `cost_estimate.md` | Detailed cost breakdown with formula |

## Pipeline Input / Output

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/raw/orders/*.csv` — columns: order_id, customer_id, product, amount, order_date |
| **Output 1** | `processed/spark/product_monthly/` — Parquet, partitioned year/month, per-product revenue |
| **Output 2** | `processed/spark/customer_clv/` — Parquet, flat, per-customer lifetime value |

## Lessons Learned

- **EMR Serverless** = no cluster management, pay per job run (~$0.07/run for small data)
- **Driver vs Executor**: Driver coordinates, Executors process data partitions in parallel
- **AQE** (Adaptive Query Execution): Spark auto-coalesces small partitions after shuffle
- **Parquet**: 10x smaller than CSV, 10x cheaper to query in Athena (columnar + compression)
- **Partitioning**: `year=YYYY/month=M/` structure lets Athena skip irrelevant data
- **Cold start**: ~30–60s for EMR Serverless to provision workers (use initial_capacity to reduce)
- **Auto-stop**: application stops billing after 15 min idle — set this always

## Cost

| Activity | Cost |
|----------|------|
| Single job run (~10 min) | ~$0.07 |
| Learning session (10 runs) | ~$0.70 |

> **Always stop/delete the application after learning. See GUIDE.md Section 10.**

## Full Guide

For the complete 10-section implementation guide (Console UI + CLI, Code Deep Dive,
Verification, Screenshots, Cleanup):

**→ See [GUIDE.md](GUIDE.md)**

---

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription with required permissions | IAM user or role |
| Configuration | Resource settings | Region, names, sizes |
| Source Data | Files or code to deploy | Application source, data files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed and running services | AWS Console / CLI |
| Endpoints | Service URLs and connection strings | Resource overview page |
| Logs | Execution and audit logs | CloudWatch Logs |

## Quick Start
`ash
# Configure AWS CLI
aws configure

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Create resource group
aws ec2 describe-regions --output table
`

## Lessons Learned
- Always tag AWS resources for cost tracking and organization
- Use IAM roles instead of access keys wherever possible
- Delete resources after learning to avoid unexpected charges
- Enable CloudWatch logging for all services in production
- Use the free tier for all lab exercises to minimize cost
