# Project 9.8 — Schema Evolution & Partitioning

## What This Does

Solves three real data engineering problems:
1. **Schema evolution** — add columns to Parquet files without breaking existing readers
2. **Partition pruning** — query only relevant partitions for 100–10,000x cost savings
3. **File compaction** — merge small files into large ones for faster Athena queries

## Demo Input → Output

| Demo | Input | Output |
|------|-------|--------|
| Schema evolution | v1 (4-col) + v2 (6-col) Parquet in S3 | Merged 5-row DataFrame, NaN for v1 missing cols |
| Schema Registry | Avro schema JSON strings | `handson-registry` / `orders-schema` v1 + v2 |
| Partition projection | Glue table config | Athena auto-discovers partitions, no MSCK REPAIR |
| Compaction | Many small Parquet files | One optimized 128 MB+ Parquet file |

## Schema Evolution Rules

```
✅ SAFE:   Add nullable field with default  →  {"name":"product","type":["null","string"],"default":null}
❌ UNSAFE: Rename a field
❌ UNSAFE: Change field type
❌ UNSAFE: Add required field without default
```

## Quick Start

```powershell
pip install boto3 pyarrow pandas s3fs

$env:DATA_LAKE_BUCKET = "handson-data-lake-YOUR_ACCOUNT_ID"
python src\schema_evolution_demo.py

# Expected output:
# Writing v1 schema data...  (3 rows, 4 cols)
# Writing v2 schema data...  (2 rows, 6 cols — product + discount_pct added)
# Reading merged schema...   (5 rows, all 6 cols, NaN for v1 missing cols)
```

## AWS Resources

| Resource | Name | Free Tier |
|----------|------|-----------|
| Glue Schema Registry | `handson-registry` | ✅ 10M versions/month |
| Glue Schema | `orders-schema` (v1 + v2) | ✅ Included |
| Glue Database | `handson_schema_demo` | ✅ 1M objects/month |
| Glue Table | `orders_partitioned` | ✅ Included |
| S3 demo files | `schema-demo/year=2024/month=01/` | ✅ 5 GB/month |

## Partition Projection Config (Glue table)

```
projection.enabled=true
projection.year.type=integer  projection.year.range=2023,2030
projection.month.type=integer projection.month.range=1,12
projection.day.type=integer   projection.day.range=1,31
storage.location.template=s3://BUCKET/orders/year=${year}/month=${month}/day=${day}
```

Effect: Athena knows all valid year/month/day combinations automatically.
No `MSCK REPAIR TABLE` needed when new partitions are added to S3.

## Key Lessons

- Parquet stores schemas by column NAME not position — merge is automatic and safe
- New nullable fields = zero impact on v1 consumers (they get null/NaN)
- NEVER rename or change type — add new columns with better names alongside old ones
- Partition by columns you filter on: date is ideal, user_id is terrible
- Target Parquet file size: 128 MB – 1 GB (avoids the "small files" problem)
- Partition projection eliminates the daily `MSCK REPAIR TABLE` manual step

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
