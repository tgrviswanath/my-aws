# Project 9.9 — Redshift Data Warehouse

## What This Does

Deploys Amazon Redshift Serverless as an OLAP data warehouse. Loads processed Parquet
data from S3 via the COPY command, runs sub-second analytical SQL, and enables BI
tool connectivity via JDBC/ODBC on port 5439.

## Architecture

```
S3: processed/orders/*.parquet (from Glue ETL / dbt)
    │  COPY command (parallel bulk load, IAM role auth)
    ▼
Redshift Serverless
  Namespace: handson-namespace  |  DB: analytics
  Workgroup: handson-workgroup  |  8 RPU base ($0.36/hr)
    ├── analytics.fact_orders   DISTKEY(customer_id) SORTKEY(order_date,region)
    └── analytics.dim_date      DISTSTYLE ALL SORTKEY(full_date)
    │
    ├── Python (psycopg2): setup / load / query / report
    ├── Redshift Data API: queries without VPN/tunnel
    └── BI Tools: Tableau, Power BI, QuickSight (JDBC port 5439)
```

## Pipeline Input / Output

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/processed/orders/*.parquet` — columns: order_id, customer_id, order_date, product_id, quantity, unit_price, total_amount, status, region |
| **Setup output** | `analytics.fact_orders` table (DISTKEY/SORTKEY columnar) + `analytics.dim_date` (~4018 rows) |
| **Load output** | N rows in fact_orders (from COPY command) |
| **Query 1** | Daily revenue last 30 days (joined with dim_date) |
| **Query 2** | Top 10 products by revenue (last 3 months) |
| **Query 3** | Top 20 customers by lifetime value |
| **Query 4** | Revenue by region with cancellation rate |

## Quick Start

```powershell
pip install psycopg2-binary boto3

# Set connection env vars (after workgroup is created)
$env:REDSHIFT_HOST     = "handson-workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com"
$env:REDSHIFT_USER     = "admin"
$env:REDSHIFT_PASSWORD = "Admin@1234!"
$env:REDSHIFT_DB       = "analytics"
$env:S3_BUCKET         = "handson-data-lake-YOUR_ACCOUNT_ID"
$env:IAM_ROLE_ARN      = "arn:aws:iam::ACCOUNT:role/handson-redshift-role"

# Create tables + load + report
python code\redshift_operations.py setup
python code\redshift_operations.py load
python code\redshift_operations.py report
```

## AWS Resources

| Resource | Name | Cost |
|----------|------|------|
| Serverless Namespace | `handson-namespace` | ❌ ~$0.36/hr (8 RPU) |
| Serverless Workgroup | `handson-workgroup` | Included in namespace |
| IAM Role | `handson-redshift-role` | ✅ Free |
| Security Group | `handson-redshift-sg` | ✅ Free |
| S3 storage | < 1 GB results | ✅ Free tier |

## Key Concepts

| Concept | Explanation |
|---------|-------------|
| **DISTKEY** | Distribute rows to nodes by this column — reduces JOIN network traffic |
| **SORTKEY** | Sort rows on disk — range queries skip irrelevant blocks |
| **DISTSTYLE ALL** | Replicate small dimension tables to every node |
| **COPY command** | Parallel bulk load from S3 — much faster than INSERT |
| **VACUUM** | Re-sort rows after COPY, reclaim deleted space |
| **ANALYZE** | Update column statistics for query planner |
| **Redshift Spectrum** | Query S3 directly from Redshift without loading |
| **Data API** | Run queries via AWS API — no VPN/tunnel needed |

## Data Lake vs Warehouse

| | Data Lake (S3+Athena) | Data Warehouse (Redshift) |
|-|----------------------|--------------------------|
| Query speed | Seconds–minutes | Sub-second |
| BI tools | ❌ No JDBC | ✅ JDBC/ODBC |
| Cost (low volume) | Cheaper | Expensive ($0.36/hr) |
| Cost (high volume) | Expensive (TB scans) | Fixed cluster cost |
| Schema | Schema-on-read | Schema-on-write |

## Full Guide

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
