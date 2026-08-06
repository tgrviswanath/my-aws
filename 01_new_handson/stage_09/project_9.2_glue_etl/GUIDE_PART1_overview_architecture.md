# Project 9.2 — AWS Glue ETL Pipeline
# Complete Hands-On Implementation Guide
# PART 1: Overview, Architecture & Prerequisites

---

## 1. PROJECT OVERVIEW

### Project Title
**AWS Glue ETL Pipeline — Raw CSV to Parquet Data Lake**

### Business / Problem Statement
A retail company collects daily order data in flat CSV files stored in S3. Analysts cannot
efficiently query these raw files with Athena because:
- CSV has no compression → slow and expensive to scan
- No partitioning → Athena scans the entire dataset for every query
- No data quality enforcement → nulls and bad types cause query failures
- Data arrives incrementally → reprocessing everything daily wastes compute

**Goal:** Build a serverless ETL pipeline with AWS Glue that automatically transforms raw
CSV orders into clean, partitioned Parquet files that Athena can query 10x faster at 90%
lower cost.

### Learning Objectives
After completing this project you will be able to:
- Create and configure an AWS Glue ETL Job with PySpark
- Write a PySpark script using Glue DynamicFrames and Spark DataFrames
- Understand Glue Job Bookmarks (incremental processing)
- Configure Glue Workers (G.1X, G.2X) and understand DPU pricing
- Schedule Glue jobs with Glue Triggers (cron schedule)
- Verify ETL output with Athena SQL queries
- Deploy the entire pipeline with Terraform IaC
- Monitor job runs via CloudWatch Logs and Glue metrics

---

## 2. ARCHITECTURE & CONCEPTS

### High-Level Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Glue ETL Pipeline                            │
│                                                                         │
│  S3 raw/orders/          Glue Job (PySpark)        S3 processed/        │
│  ┌──────────────┐        ┌──────────────────┐      ┌──────────────────┐ │
│  │ orders_01.csv│──────▶ │  1. EXTRACT      │      │processed/orders/ │ │
│  │ orders_02.csv│        │  read CSV from S3│      │  year=2024/      │ │
│  │ orders_03.csv│        │                  │      │    month=01/     │ │
│  └──────────────┘        │  2. TRANSFORM    │      │      part-0.parq │ │
│                          │  clean nulls     │─────▶│  year=2024/      │ │
│  IAM Role                │  fix data types  │      │    month=02/     │ │
│  ┌──────────────┐        │  dedup records   │      │      part-0.parq │ │
│  │AWSGlueService│        │  add partitions  │      └──────────────────┘ │
│  │Role          │        │                  │                            │
│  │+ S3 access   │        │  3. LOAD         │      Athena Queries        │
│  └──────────────┘        │  write Parquet   │      ┌──────────────────┐ │
│                          │  partitioned by  │      │SELECT product,   │ │
│  Glue Trigger            │  year/month      │      │SUM(amount)       │ │
│  ┌──────────────┐        └──────────────────┘      │FROM orders       │ │
│  │cron(0 2 * *)│                                   │GROUP BY product  │ │
│  │2am UTC daily│        Glue Job Bookmark           └──────────────────┘ │
│  └──────────────┘        tracks processed files                          │
│                          → only new files on next run                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services Involved

| Service | Role | Why Used |
|---------|------|----------|
| **AWS Glue** | ETL engine | Managed Spark — no cluster setup needed |
| **S3** | Raw + processed data store | Durable, cheap, integrates natively with Glue |
| **Glue Data Catalog** | Metadata store | Stores table schema for Athena to query |
| **Athena** | SQL query engine | Query Parquet output without loading into DB |
| **IAM** | Permissions | Glue needs role to read S3, write Catalog |
| **CloudWatch Logs** | Job monitoring | Captures Spark logs for debugging |

### Service Interaction Flow (Step by Step)
```
1. Glue Trigger fires at 2am UTC
2. Trigger starts Glue Job "handson-etl-job"
3. Glue Job reads PySpark script from S3 scripts/etl_job.py
4. Glue spins up 2 × G.1X workers (Spark cluster, ~2min startup)
5. Job reads CSV files from s3://bucket/raw/orders/
6. Glue Bookmark checked → only unprocessed files are read
7. PySpark transforms: dropna, cast types, add partition cols, dedup
8. Job writes Parquet to s3://bucket/processed/orders/year=X/month=Y/
9. Job commits Bookmark → tracks which files were processed
10. Glue Catalog updated → Athena can query the new partitions
11. Workers terminated → billing stops
12. CloudWatch Logs capture full Spark output
```

### Key Concepts Explained

**DynamicFrame vs DataFrame:**
```
DynamicFrame (Glue-native):            DataFrame (Spark-native):
- Handles schema inconsistencies       - Standard PySpark API
- Each row can have different fields   - Strict schema enforcement
- Use for raw data ingestion           - Use for transformations
- .toDF() converts to DataFrame        - More transformation functions
```

**Glue Job Bookmark (why it matters):**
```
Without bookmark:
  Day 1: processes files A, B, C         (3 files, fine)
  Day 2: processes files A, B, C, D, E   (reprocesses A,B,C = WASTE!)
  Day 3: processes A,B,C,D,E, F,G        (grows every day)

With bookmark ENABLED:
  Day 1: processes A, B, C → bookmark saved
  Day 2: processes only D, E  ← only NEW files
  Day 3: processes only F, G  ← always incremental
```

**Glue Worker Types:**
```
G.1X  → 4 vCPU + 16GB RAM  → $0.44/DPU-hour → standard ETL (this project)
G.2X  → 8 vCPU + 32GB RAM  → $0.88/DPU-hour → memory-heavy joins
G.4X  → 16 vCPU + 64GB RAM → $1.76/DPU-hour → very large datasets
G.8X  → 32 vCPU + 128GB RAM→ $3.52/DPU-hour → largest datasets

For this project: 2 × G.1X = 2 DPUs = $0.88/hour
A 10-minute run costs: $0.88 × (10/60) ≈ $0.15 per run
```

**Parquet vs CSV:**
```
CSV:
  - 100MB raw CSV with orders
  - Athena scans all 100MB for any query
  - No compression, no column pruning
  - Cost: $0.005 per query (scans full file)

Parquet (partitioned by year/month):
  - Same data = ~15MB compressed Parquet
  - Athena scans only relevant partitions
  - Column pruning: SELECT amount only reads amount column
  - Cost: $0.00075 per query = 85% savings
```

### Best Practices Followed in This Project
- Job Bookmarks enabled → incremental processing, no reruns of old data
- 2 workers minimum → Glue requires ≥2 for distributed execution
- G.1X workers → right-sized for small/medium datasets (< 10GB)
- Parquet + partitioning → 10x faster Athena queries
- `--enable-continuous-cloudwatch-log` → real-time log streaming
- `--enable-metrics` → Spark metrics in CloudWatch
- Timeout set to 60 min → prevents runaway jobs from burning cost
- Tags on all resources → cost allocation and resource management

---

## 3. PREREQUISITES

### 3.1 AWS Account Setup
- Active AWS account (free tier eligible for some resources)
- Root account or IAM user with sufficient permissions
- **Required region:** `us-east-1` (N. Virginia) — all commands use this region
- **Note:** Project 9.1 (Data Lake) must be deployed first — this project reuses its S3 bucket, IAM role, and Glue database

### 3.2 IAM Permissions Required
Your IAM user/role must have these permissions to deploy this project:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:*",
        "s3:*",
        "iam:GetRole",
        "iam:PassRole",
        "logs:*",
        "cloudwatch:*",
        "athena:*"
      ],
      "Resource": "*"
    }
  ]
}
```

> For a beginner account: attaching `AdministratorAccess` to your IAM user works,
> but in production always use least-privilege policies.

### 3.3 Dependency: Project 9.1 Must Be Deployed
This project reuses outputs from Project 9.1 (Data Lake):

| Output from 9.1 | Used in 9.2 |
|-----------------|-------------|
| `data_lake_bucket` | S3 bucket for raw + processed data |
| `glue_role_arn` | IAM role Glue job assumes |
| `glue_database` | Glue Catalog database name |

To get these values:
```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake\terraform
terraform output
# Copy: data_lake_bucket, glue_role_arn, glue_database
```

### 3.4 Required Software

| Tool | Version | Install Command |
|------|---------|----------------|
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |
| Terraform | >= 1.5 | `winget install Hashicorp.Terraform` |
| Git | latest | `winget install Git.Git` |
| VS Code | latest | `winget install Microsoft.VisualStudioCode` |
| Python | 3.8+ | Only needed to inspect the ETL script locally |

### 3.5 AWS CLI Configuration

```bash
# Configure CLI with your credentials
aws configure

# You will be prompted for:
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json

# Verify configuration works
aws sts get-caller-identity
# Expected output:
# {
#     "UserId": "AIDA...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

### 3.6 Environment Variables (Windows)

```powershell
# Set in PowerShell session (replace with your actual values from project 9.1)
$env:DATA_LAKE_BUCKET = "handson-data-lake-123456789012"
$env:GLUE_ROLE_ARN    = "arn:aws:iam::123456789012:role/handson-glue-role"
$env:DATABASE_NAME    = "handson_data_lake"
$env:AWS_REGION       = "us-east-1"

# Or set permanently via System Properties > Environment Variables
```

### 3.7 Estimated AWS Cost

| Scenario | Cost |
|----------|------|
| Single manual test run (10 min, 2 workers) | ~$0.15 |
| Daily scheduled runs for 30 days | ~$4.50 |
| S3 storage for processed Parquet | ~$0.02/month |
| **Total for this learning project** | **< $5** |

> **Free Tier:** AWS Glue is NOT included in the free tier. Every DPU-second is billed.
> Use `terraform destroy` after each session to avoid charges from scheduled triggers.
> Disable the Glue Trigger when not actively learning.
