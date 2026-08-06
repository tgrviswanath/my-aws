# Project 9.7 — Data Quality Validation

## What This Does

Implements automated data quality gates using Great Expectations. Validates processed
order data after each Glue ETL job. If checks fail, the pipeline stops, bad records
are quarantined in S3, and an SNS alert fires. If checks pass, dbt runs next.

## Architecture

```
Glue ETL Job: SUCCEEDED
    │  EventBridge rule triggers
    ▼
Lambda: handson-data-quality-check
    │  Runs Great Expectations on processed/orders/ Parquet
    │
    ├── PASS → pipeline continues to dbt
    │          report saved to data-quality/reports/
    │
    └── FAIL → SNS alert to email
               bad records → quarantine/orders/
               exit code 1 → pipeline STOPS
```

## Validation Checks (10 total)

| Check | Type | Threshold |
|-------|------|-----------|
| Row count >= 1 | Completeness | Hard fail if 0 rows |
| order_id not null | Completeness | 100% |
| customer_id not null | Completeness | 100% |
| amount not null | Completeness | 100% |
| order_date not null | Completeness | 100% |
| order_id unique | Uniqueness | 100% |
| amount between 0.01–10,000 | Validity | 100% |
| product in known list | Validity | 99% (1% tolerance) |
| order_date matches %Y-%m-%d | Validity | 100% |
| mean(amount) between 10–200 | Statistical | Always checked |

## Pipeline Input / Output

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/processed/orders/*.parquet` — columns: order_id, customer_id, product, amount, order_date |
| **PASS output** | `data-quality/reports/TIMESTAMP.json` — validation summary |
| **FAIL output** | `quarantine/orders/DATE/` — bad records + `SNS email alert` |

## Quick Start

```powershell
# Install
pip install great-expectations pandas pyarrow s3fs

# Create dirty test data
python -c "import pandas as pd; pd.DataFrame({'order_id':['ORD-001','ORD-002',None,'ORD-001'],'customer_id':['C1','C2','C3','C4'],'product':['Widget A','Widget B','Unknown','Widget C'],'amount':[29.99,-5.00,49.99,19.99],'order_date':['2024-01-15','2024-01-15','2024-01-16','2024-01-16']}).to_parquet('/tmp/test.parquet',index=False)"

# Run validation (expect FAILURE — demonstrates detection)
$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
# Exit code: 1 (FAILED — 3 checks catch null, duplicate, negative)
```

## AWS Resources

| Resource | Name | Cost |
|----------|------|------|
| Lambda | `handson-data-quality-check` | ✅ Free tier |
| SNS Topic | `handson-data-quality-alerts` | ✅ Free tier |
| EventBridge Rule | `handson-glue-job-success` | ✅ Free tier |
| IAM Role | `handson-quality-lambda-role` | ✅ Free |
| S3 reports | `data-quality/reports/` | ~$0.01/month |
| Great Expectations | local library | ✅ Free (open source) |

## Lessons Learned

- **Fail fast**: catch bad data immediately after ETL, not weeks later at the dashboard
- **`mostly=0.99`**: allows 1% new/unknown products without false positives
- **Quarantine, don't delete**: bad records kept for investigation + recovery
- **`sys.exit(1)`**: enables Airflow, CI/CD, and bash scripts to detect failure
- **Statistical mean check**: catches subtle data drift that row-level checks miss
- **Great Expectations vs dbt tests**: GX for pipeline validation; dbt tests for model validation

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
