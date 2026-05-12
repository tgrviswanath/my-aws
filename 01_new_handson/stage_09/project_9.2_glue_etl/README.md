# Project 9.2 — Glue ETL Pipeline

## What This Does
Builds an ETL pipeline using AWS Glue: extract raw CSV/JSON data from S3, transform it (clean, enrich, aggregate), and load the results as optimized Parquet files back to S3 for Athena queries.

## Pipeline
```
S3 raw/ (CSV/JSON)
  → Glue Job (PySpark)
    → Clean nulls, fix types, deduplicate
    → Enrich (join with reference data)
    → Aggregate (daily summaries)
  → S3 processed/ (Parquet, partitioned)
    → Athena queries
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
# Upload Glue script to S3
aws s3 cp src/etl_job.py s3://YOUR_BUCKET/scripts/etl_job.py
# Run the job
aws glue start-job-run --job-name handson-etl-job
```

## Lessons Learned
- Glue DPU: 1 DPU = 4 vCPU + 16 GB RAM — use minimum needed
- Glue bookmarks: track processed files — avoid reprocessing on reruns
- Dynamic frames vs DataFrames: DynamicFrame handles schema inconsistencies better
- Pushdown predicates: filter at S3 level before loading into Spark — faster
- Glue Studio: visual ETL builder — good for learning, generates PySpark code

## Code

### `src/etl_job.py` — AWS Glue PySpark ETL job

```bash
# Upload script to S3 (required before running the Glue job)
aws s3 cp src/etl_job.py s3://my-data-lake/scripts/etl_job.py

# Run the Glue job
aws glue start-job-run --job-name handson-etl-job

# Monitor job status
aws glue get-job-run --job-name handson-etl-job --run-id <run-id>
```

What it does: reads CSV from `s3://bucket/raw/`, cleans nulls, fixes types, deduplicates, adds partition columns (year/month/day), writes Parquet to `s3://bucket/processed/`.
