# Project 9.5 — Airflow Data Orchestration

## What This Does
Orchestrates the entire data pipeline using Apache Airflow on Amazon MWAA (Managed Workflows for Apache Airflow). DAGs define the pipeline as code — dependencies, retries, scheduling, and monitoring.

## Pipeline DAG
```
daily_data_pipeline (runs at 2am UTC)
  ├── check_source_data_available
  ├── run_glue_etl_job
  │     └── wait_for_glue_completion
  ├── run_spark_aggregations (depends on glue)
  │     └── wait_for_spark_completion
  ├── run_dbt_transformations (depends on spark)
  ├── validate_data_quality (depends on dbt)
  └── notify_success / notify_failure
```

## Services Used
- Amazon MWAA (Managed Airflow)
- Glue (ETL jobs)
- EMR Serverless (Spark jobs)
- S3 (DAG storage)
- SNS (notifications)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
# Upload DAGs to S3
aws s3 cp dags/ s3://YOUR_MWAA_BUCKET/dags/ --recursive
```

## Lessons Learned
- MWAA is expensive — use local Airflow (Docker) for development
- DAG file must be syntactically valid Python — errors prevent all DAGs from loading
- XCom: pass data between tasks (keep small — not for large datasets)
- Sensors: wait for external conditions (S3 file exists, Glue job complete)
- Task groups: organize complex DAGs visually
- Backfill: re-run historical dates — `airflow dags backfill -s 2024-01-01 -e 2024-01-31`
