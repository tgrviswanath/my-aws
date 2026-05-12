# Project 9.1 — Data Lake Architecture

## What This Does
Builds a modern data lake on AWS: raw data lands in S3, Glue Catalog provides the schema, Athena queries it with SQL, and Lake Formation controls access.

## Architecture
```
Data Sources → S3 (raw zone)
                → Glue Crawler (discover schema)
                  → Glue Data Catalog (metadata)
                    → Athena (SQL queries)
                    → Lake Formation (access control)
```

## S3 Zone Strategy
| Zone | Purpose | Format |
|------|---------|--------|
| raw/ | Original data, never modified | JSON, CSV, Parquet |
| processed/ | Cleaned, transformed | Parquet (partitioned) |
| curated/ | Business-ready, aggregated | Parquet |
| archive/ | Old data, rarely accessed | Parquet (Glacier) |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output data_lake_bucket
```

## Lessons Learned
- Parquet format: columnar, compressed — 10x cheaper to query in Athena than CSV
- Partitioning: `year=2024/month=01/day=15/` — Athena skips irrelevant partitions
- Glue Crawler: auto-discovers schema but runs on a schedule — not real-time
- Lake Formation: fine-grained access control (column-level, row-level filtering)
- Data lake vs data warehouse: lake = raw + flexible; warehouse = structured + fast queries

## Code

### `code/data_lake_setup.py` — Set up S3 data lake zones and Glue catalog

```bash
pip install boto3

# Set up the full data lake structure
python code/data_lake_setup.py --bucket my-data-lake-bucket

# Use a specific region
python code/data_lake_setup.py --bucket my-data-lake-bucket --region us-east-1
```

What it creates:
| S3 Prefix | Purpose |
|-----------|---------|
| `raw/` | Landing zone — raw data as-is from sources |
| `processed/` | Cleaned and transformed data (Parquet) |
| `curated/` | Business-ready aggregated data |
| `archive/` | Historical data (moved by lifecycle policy) |

Also creates:
- Glue databases: `raw_db`, `processed_db`, `curated_db`
- Registers S3 locations with Lake Formation
- Creates a sample Glue table for orders data
- Prints the data lake structure summary
