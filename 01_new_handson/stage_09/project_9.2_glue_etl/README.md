# Project 9.2 — AWS Glue ETL Pipeline

**Stage:** 09 — Data Engineering | **Level:** Beginner | **Est. Time:** 3–4 hours
**Cost:** ~$0.15 per run | **Depends on:** Project 9.1 (Data Lake)

---

## What This Does

Builds a serverless ETL pipeline that automatically transforms raw CSV order data
into clean, partitioned Parquet files — 10x faster to query and 90% cheaper in
Athena than the original CSV.

This is the `raw → processed` step every production data lake needs. Without it,
analysts query inconsistent CSV with wrong data types. With it, data arrives
clean, typed, and ready for business queries.

---

## Pipeline Architecture

```
S3: raw/orders/*.csv          Glue Job (PySpark)           S3: processed/orders/
┌─────────────────────┐      ┌─────────────────────────┐   ┌─────────────────────┐
│ year=2024/month=01/ │      │  EXTRACT                │   │ year=2024/month=01/ │
│   orders.csv        │─────▶│  read CSV + DynamicFrame│   │   part-0.parquet    │
│ (string types,      │      │                         │──▶│ (typed columns,     │
│  nulls possible,    │      │  TRANSFORM              │   │  compressed,        │
│  uncompressed)      │      │  dropna, cast types     │   │  partitioned)       │
└─────────────────────┘      │  dedup, add partitions  │   └─────────────────────┘
                             │  add processed_at       │
                             │                         │   S3: processed/orders_daily/
IAM Role                     │  LOAD                   │   ┌─────────────────────┐
handson-glue-role            │  write Parquet          │──▶│ daily aggregates    │
(from Project 9.1)           │  partitioned year/month │   │ by product          │
                             └─────────────────────────┘   └─────────────────────┘
Glue Bookmark                       ↑
tracks processed files        Glue Trigger
→ only new files next run     cron(0 2 * * ? *)
                              2am UTC daily
```

---

## Key Concepts

| Concept | What It Means |
|---------|--------------|
| **DynamicFrame** | Glue-native data structure — handles CSV with inconsistent columns |
| **Job Bookmark** | Tracks which S3 files were already processed — prevents reruns |
| **G.1X Worker** | 4 vCPU + 16 GB RAM — $0.44/DPU-hour, right-sized for < 1 GB data |
| **Parquet** | Columnar compressed format — 10x faster Athena queries, 70–80% smaller |
| **Partition pruning** | `WHERE year=2024 AND month=01` → Athena skips other months |
| **`transformation_ctx`** | Unique key per DynamicFrame — required for Bookmark tracking |

---

## Dependency: Project 9.1 Must Be Deployed First

This project reuses S3 bucket, IAM role, and Glue database from Project 9.1.

```bash
# Get required values from Project 9.1
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake\terraform
terraform output

# You need:
# data_lake_bucket = "handson-data-lake-YOUR_ACCOUNT_ID"
# glue_role_arn    = "arn:aws:iam::YOUR_ACCOUNT_ID:role/handson-glue-role"
# glue_database    = "handson_data_lake"
```

---

## Quick Start (Terraform — 3 steps)

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl\terraform

# 1. Initialize
terraform init

# 2. Deploy (replace with your values from Project 9.1)
terraform apply \
  -var="data_lake_bucket=handson-data-lake-YOUR_ACCOUNT_ID" \
  -var="glue_role_arn=arn:aws:iam::YOUR_ACCOUNT_ID:role/handson-glue-role" \
  -var="database_name=handson_data_lake"

# 3. Run the ETL job
aws glue start-job-run --job-name handson-etl-job
```

---

## Files in This Project

```
project_9.2_glue_etl/
│
├── README.md                              ← This file — quick overview
├── steps.md                               ← Condensed CLI commands reference
├── verify.md                              ← Verification checklist + CLI checks
├── cost_estimate.md                       ← DPU pricing breakdown
│
├── steps_awsconsoleui.md                  ← Complete Console UI guide (improved
│                                            template format with Decision Points,
│                                            Screenshots, Troubleshooting tables)
│
├── GUIDE_PART1_overview_architecture.md   ← Architecture, concepts, prerequisites
├── GUIDE_PART2_console_ui.md              ← Console UI implementation (detailed)
├── GUIDE_PART3_cli_terraform.md           ← CLI + Terraform + Code Deep Dive
├── GUIDE_PART4_verification_cleanup.md    ← Verify, Observations, Screenshots, Cleanup
│
├── src/
│   └── etl_job.py                         ← PySpark ETL script (runs inside Glue)
│
├── terraform/
│   ├── main.tf                            ← Glue job, trigger, S3 script upload
│   ├── variables.tf                       ← All configurable parameters
│   ├── outputs.tf                         ← Exported values after apply
│   └── terraform.tfvars                   ← Your values (fill in before applying)
│
└── docs/
    └── architecture.md                    ← Pipeline flow diagrams
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `src/etl_job.py` | The actual PySpark code that runs on Glue workers. Reads CSV → cleans → writes Parquet. |
| `terraform/main.tf` | Creates Glue job + daily trigger + uploads script to S3 in one `terraform apply`. |
| `terraform/variables.tf` | All tunable parameters: worker type, count, timeout, schedule, trigger activation. |
| `steps_awsconsoleui.md` | Step-by-step console guide with exact button names, decision tables, screenshot markers. |
| `GUIDE_PART3_cli_terraform.md` | Line-by-line explanation of every CLI flag and Terraform attribute. |

---

## AWS Services Used

| Service | Role | Free Tier? |
|---------|------|-----------|
| **AWS Glue** | ETL engine (managed Spark) | ❌ $0.44/DPU-hour |
| **S3** | Stores raw CSV + processed Parquet | ✅ 5 GB free |
| **Glue Data Catalog** | Table schema for Athena | ✅ 1M objects free |
| **Athena** | SQL queries on processed Parquet | ❌ $5/TB scanned |
| **CloudWatch Logs** | Job execution logs | ✅ 5 GB/month free |
| **IAM** | Glue service role | ✅ Free |

> ⚠️ **Glue is NOT free tier.** Every DPU-second of worker execution is billed.
> A 10-minute run costs ~$0.15. Always destroy after learning.

---

## Terraform Resources Created

```
aws_s3_object.etl_script          ← uploads src/etl_job.py to S3
aws_glue_job.etl                  ← handson-etl-job (Spark, G.1X x2)
aws_glue_trigger.daily            ← handson-etl-daily (CREATED, not activated)
```

### Terraform Workflow

```bash
terraform init                    # download AWS provider
terraform plan -var-file=terraform.tfvars   # preview changes
terraform apply -var-file=terraform.tfvars  # deploy (type yes)
terraform state list              # confirm 3 resources
terraform output                  # see job name, trigger name, S3 paths
terraform destroy -var-file=terraform.tfvars  # cleanup after learning
```

---

## Running and Monitoring the Job

```bash
# Start a job run
JOB_NAME=$(terraform output -raw glue_job_name)
RUN_ID=$(aws glue start-job-run --job-name $JOB_NAME --query "JobRunId" --output text)
echo "Run ID: $RUN_ID"

# Check status (poll every 30s)
aws glue get-job-run --job-name $JOB_NAME --run-id $RUN_ID \
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime,Error:ErrorMessage}"

# View logs in real-time
aws logs tail /aws-glue/jobs/output --follow

# Verify S3 output after job completes
BUCKET=$(cd terraform && terraform output -raw data_lake_bucket 2>/dev/null)
aws s3 ls s3://$BUCKET/processed/orders/ --recursive
```

---

## Verify ETL Output with Athena

```sql
-- Register new partitions (run after every ETL job)
MSCK REPAIR TABLE orders;

-- Query processed Parquet data
SELECT
    product,
    COUNT(*)         AS order_count,
    SUM(amount)      AS total_revenue,
    AVG(amount)      AS avg_order_value
FROM orders
WHERE year = '2024' AND month = '01'
GROUP BY product
ORDER BY total_revenue DESC;

-- Compare data quality: raw CSV vs processed Parquet
SELECT COUNT(*) FROM orders WHERE order_id IS NULL;
-- Expected: 0  (ETL removed nulls)
```

---

## Estimated Cost

| Scenario | Cost |
|----------|------|
| 1 manual test run (10 min, 2 × G.1X) | ~$0.15 |
| Daily scheduled runs × 30 days | ~$4.50/month |
| S3 storage for processed Parquet | ~$0.02/month |
| **Learning session (3–4 manual runs)** | **~$0.45–0.60** |

### Cost Breakdown

```
G.1X worker = 1 DPU = $0.44/DPU-hour
2 workers × 10 min = 2 × (10/60) DPU-hours = 0.33 DPU-hours = $0.15 per run

If trigger is ACTIVATED (daily): $0.15 × 30 = $4.50/month
If trigger stays CREATED (inactive): $0.00
```

**Keep `enable_trigger = false` in terraform.tfvars while learning.**

---

## Lessons Learned

- **`job.commit()` is not optional** — without it, bookmarks are never saved and the job reprocesses all files every run
- **`--TempDir` is not optional** — Glue will error without it; Spark needs this for shuffle operations
- **Job parameter keys must start with `--`** — `source_bucket` (no prefix) is silently ignored; use `--source_bucket`
- **STARTING state is billed** — Glue charges from worker allocation start, not when your code begins executing
- **Parquet is always smaller** — same data in Parquet = 70–80% smaller than CSV due to column compression
- **Partition pruning saves money** — `WHERE year=2024 AND month=01` makes Athena skip all other months
- **`transformation_ctx` must be unique** — duplicate values cause bookmark confusion; use a unique string per DynamicFrame
- **Minimum 2 workers** — Spark requires 1 driver + 1 executor; setting `num_workers = 1` causes job failure

---

## Cleanup

```bash
# 1. Destroy Terraform-managed resources
cd terraform
terraform destroy -var-file=terraform.tfvars

# 2. Remove processed output from S3 (optional — saves storage cost)
BUCKET=$(terraform output -raw data_lake_bucket 2>/dev/null)
aws s3 rm s3://$BUCKET/processed/ --recursive

# 3. Verify cleanup
aws glue get-job --job-name handson-etl-job 2>&1 | grep -i "not found"
# Expected: EntityNotFoundException

# Project 9.1 resources (S3 bucket, IAM role, Glue database) remain intact
# To clean those up: cd ../project_9.1_data_lake/terraform && terraform destroy
```

---

## 📖 Complete Guides

| Guide | Content |
|-------|---------|
| [steps_awsconsoleui.md](steps_awsconsoleui.md) | Console UI — step-by-step with decision tables and 23 screenshot markers |
| [GUIDE_PART1](GUIDE_PART1_overview_architecture.md) | Project overview, architecture diagram, all concepts explained |
| [GUIDE_PART2](GUIDE_PART2_console_ui.md) | Folder structure + detailed console walkthrough |
| [GUIDE_PART3](GUIDE_PART3_cli_terraform.md) | Full CLI commands + complete Terraform code with annotations |
| [GUIDE_PART4](GUIDE_PART4_verification_cleanup.md) | Verification, observations, screenshots guidance, cleanup |

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
