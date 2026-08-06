# Project 9.6 — dbt Transformation Pipeline

## What This Does

Uses dbt Core (free, open source) to transform raw orders data in Athena into clean,
tested, documented analytical tables. dbt is the industry standard for the "T" in ELT.

## Model Lineage

```
Source: handson_data_lake.orders  (raw CSV → Glue Catalog from Project 9.1)
    │
    │  {{ source('raw', 'orders') }}
    ▼
stg_orders  (VIEW)             models/staging/stg_orders.sql
    │  Clean: cast types, normalize case, filter nulls
    │
    │  {{ ref('stg_orders') }}
    ▼
fct_orders  (INCREMENTAL TABLE) models/marts/fct_orders.sql
    │  Business logic: unit_price, order_tier segmentation
    │  Tests: not_null, unique, accepted_values (schema.yml)
    ▼
Athena queries → BI dashboards / Redshift Spectrum
```

## Files

| File | Purpose |
|------|---------|
| `models/staging/stg_orders.sql` | Staging: clean raw orders → VIEW |
| `models/marts/fct_orders.sql` | Mart: business logic → INCREMENTAL TABLE |
| `models/marts/schema.yml` | Tests + docs for fct_orders |

## Pipeline Input / Output

| | Detail |
|-|--------|
| **Input** | `handson_data_lake.orders` (Glue table over S3 raw CSV) |
| **stg_orders output** | VIEW — cleaned, cast, normalized (product_name, order_status, order_amount_usd) |
| **fct_orders output** | TABLE — adds unit_price_usd, order_tier; incremental merge on order_id |

## Quick Start

```powershell
# 1. Install
pip install dbt-athena-community

# 2. Configure connection
# Create ~/.dbt/profiles.yml (see GUIDE.md Phase 2)

# 3. Go to dbt project
cd dbt_project

# 4. Create project files
# Create dbt_project.yml, models/staging/schema.yml, packages.yml (see GUIDE.md Phase 3)

# 5. Install packages and test connection
dbt deps
dbt debug

# 6. Run models
dbt run

# 7. Test data quality
dbt test

# 8. View documentation
dbt docs generate && dbt docs serve
```

## AWS Resources Used

| Resource | Name | Cost |
|----------|------|------|
| Athena Workgroup | `handson-dbt` | ~$0/month (per query) |
| S3 Staging Bucket | `handson-dbt-staging-ACCOUNT` | ~$0.01/month |
| Glue Data Catalog | `handson_data_lake` | ✅ Free |
| dbt Core | local tool | ✅ Free |

## Key Concepts

- **`source()`** — references raw tables outside dbt (shows in lineage graph)
- **`ref()`** — references another dbt model (builds execution order DAG)
- **`is_incremental()`** — guards WHERE clause for incremental runs only
- **`materialized='incremental'`** — only processes new/changed rows
- **`unique_key='order_id'`** — merge strategy key (upsert)
- **schema.yml tests** — `not_null`, `unique`, `accepted_values` run after every build

## Cost

~$0.01/session | dbt Core is 100% free

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
