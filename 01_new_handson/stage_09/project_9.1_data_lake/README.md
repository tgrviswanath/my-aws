# Project 9.1 — Data Lake Architecture on AWS

**Stage:** 09 — Data Engineering | **Level:** Beginner | **Est. Time:** 3–4 hours | **Cost:** ~$0.09

---

## What This Does

Builds a production-grade data lake on AWS using the medallion architecture:
raw data lands in S3, Glue Crawlers discover the schema automatically, Athena
queries it with SQL (no servers needed), and Lake Formation controls who can
access what.

This is the same pattern used by Netflix, Airbnb, and Uber at petabyte scale.

---

## Architecture

```
Data Sources
    │
    ▼
S3 Raw Zone (CSV, JSON, as-is)
    │  Glue Crawler (schema discovery)
    ▼
Glue Data Catalog (metadata: tables, columns, types)
    │
    ├──▶ Athena (serverless SQL queries)
    └──▶ Lake Formation (column/row-level access control)
         │
         ▼
    S3 Processed Zone (Parquet, partitioned)
         │
         ▼
    S3 Curated Zone (aggregated, business-ready)
```

## S3 Zone Strategy

| Zone | Purpose | Format | Partition |
|------|---------|--------|-----------|
| `raw/` | Original data — never modified | CSV, JSON | year/month/day |
| `processed/` | Cleaned + typed data | Parquet (Snappy) | year/month |
| `curated/` | Aggregated, business-ready | Parquet | year/month |
| `archive/` | Old raw data → Glacier after 90 days | Parquet | year |

---

## Quick Start (3 commands)

```bash
cd terraform
terraform init && terraform apply -auto-approve
BUCKET=$(terraform output -raw data_lake_bucket)
```

Then upload data, run the crawler, and query:

```bash
python code/upload_sample_data.py --bucket $BUCKET
aws glue start-crawler --name handson-raw-crawler
aws glue wait crawler-ready --crawler-name handson-raw-crawler
python code/run_athena_query.py --bucket $BUCKET --demo
```

---

## Files in This Project

```
project_9.1_data_lake/
├── GUIDE.md                     ← Complete 10-section implementation guide (START HERE)
├── README.md                    ← This file — quick overview
├── steps.md                     ← Condensed commands reference
├── verify.md                    ← Verification checklist and CLI checks
├── cost_estimate.md             ← Detailed cost breakdown
│
├── terraform/
│   ├── main.tf                  ← All AWS resources (S3, Glue, Athena, IAM)
│   ├── variables.tf             ← Configurable parameters with defaults
│   ├── outputs.tf               ← Exported values after apply
│   └── terraform.tfvars         ← Your variable overrides (gitignored)
│
├── code/
│   ├── data_lake_setup.py       ← Create S3 zones + Glue databases + Lake Formation
│   ├── upload_sample_data.py    ← Generate and upload partitioned sample data
│   ├── convert_to_parquet.py    ← Convert CSV → Parquet + show cost comparison
│   └── run_athena_query.py      ← Run SQL queries via Athena CLI wrapper
│
├── data/
│   ├── sample_orders.csv        ← 10-row e-commerce orders dataset
│   ├── sample_customers.csv     ← 5-row customer data
│   └── sample_products.csv      ← 8-row product catalog
│
└── docs/
    ├── architecture.md          ← Deep-dive architecture notes
    └── data_dictionary.md       ← Column definitions for all tables
```

---

## AWS Services Used

| Service | Role | Free Tier |
|---------|------|-----------|
| Amazon S3 | Storage for all zones | ✅ 5 GB free |
| AWS Glue Data Catalog | Schema/metadata store | ✅ 1M objects free |
| AWS Glue Crawler | Auto-discovers schema from S3 | ❌ $0.44/DPU-hour |
| Amazon Athena | Serverless SQL over S3 | ❌ $5/TB scanned |
| AWS Lake Formation | Access control layer | ✅ Free |
| AWS IAM | Roles and permissions | ✅ Free |

---

## Key Concepts Learned

- **Data lake vs data warehouse:** Lake = raw + flexible; warehouse = structured + fast
- **Parquet format:** Columnar, compressed — 10x cheaper to query in Athena than CSV
- **Partitioning:** `year=2024/month=01/day=15/` — Athena skips irrelevant partitions
- **Glue Crawler:** Auto-discovers schema but runs on a schedule — not real-time
- **Lake Formation:** Fine-grained access control (column-level, row-level filtering)
- **Lifecycle policies:** Auto-tier S3 objects to Glacier after 90 days (cost saving)
- **Immutable raw zone:** Never modify raw data — it's your audit trail

---

## Estimated Cost

| Activity | Cost |
|----------|------|
| 2-hour lab session | ~$0.09 |
| 3 Glue Crawler runs | ~$0.04 |
| Athena queries < 100 MB | ~$0.00 |
| S3 < 5 GB (free tier) | $0.00 |
| **Total** | **~$0.09** |

**Always run `terraform destroy` after the lab.**

---

## Teardown

```bash
# Empty buckets first (required before destroy)
BUCKET=$(terraform output -raw data_lake_bucket)
ATHENA_BUCKET=$(terraform output -raw athena_results_bucket)
aws s3 rm s3://$BUCKET --recursive
aws s3 rm s3://$ATHENA_BUCKET --recursive

# Destroy all infrastructure
cd terraform && terraform destroy -auto-approve
```

---

## 📖 Full Guide

For the complete 10-section beginner implementation guide covering:
Console → CLI → Terraform → Code Deep Dive → Verification → Cleanup

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
