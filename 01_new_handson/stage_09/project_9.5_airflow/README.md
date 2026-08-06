# Project 9.5 — Airflow Data Orchestration

## What This Does

Orchestrates the entire data pipeline using Apache Airflow. A DAG (Directed Acyclic Graph)
defines pipeline tasks as Python code — with dependencies, retries, scheduling, and
failure notifications. Run locally with Docker for free, or on Amazon MWAA for production.

## Pipeline DAG

```
Schedule: 0 2 * * * (2am UTC daily)

check_source_data (S3KeySensor)
    │  waits for raw/orders/YYYY/MM/DD/ to exist in S3
    ▼
run_glue_etl (GlueJobOperator)
    │  triggers handson-etl-job, waits for SUCCEEDED
    ▼
run_dbt_transformations (PythonOperator)
    │  runs: dbt run --select orders+ && dbt test
    ▼
validate_data_quality (PythonOperator)
    │  checks S3 output files exist and size > 1 KB
    │  pushes file_count + size_bytes to XCom
    ├──▶ notify_success (SnsPublishOperator) — trigger_rule="all_success"
    └──▶ notify_failure (SnsPublishOperator) — trigger_rule="one_failed"
```

## Two DAG Files

| File | DAG ID | Use |
|------|--------|-----|
| `dags/daily_pipeline.py` | `daily_data_pipeline` | Primary — deploy to MWAA |
| `code/orders_dag.py` | `orders_data_pipeline` | Advanced reference — XCom, callbacks, Variables |

## Runtime Options

| Option | Cost | Setup | Best For |
|--------|------|-------|---------|
| **Local Docker** | $0 | 5 min | Learning, development |
| Amazon MWAA mw1.small | ~$670/month | 30 min | Production team use |

> **Always start with Local Docker — identical Airflow API, zero cost.**

## Quick Start (Local Docker)

```powershell
# 1. Create directory
mkdir C:\airflow-local; cd C:\airflow-local
mkdir dags, logs, plugins

# 2. Get Docker Compose
Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml" -OutFile docker-compose.yaml
"AIRFLOW_UID=50000" | Out-File .env

# 3. Start Airflow
docker compose up airflow-init
docker compose up -d

# 4. Upload DAG
Copy-Item "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow\dags\daily_pipeline.py" .\dags\

# 5. Open UI
Start-Process "http://localhost:8080"
# Login: airflow / airflow
```

## Pipeline Input / Output

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/raw/orders/YYYY/MM/DD/*.csv` — daily orders file |
| **Task 2 Output** | `processed/orders/year=YYYY/month=MM/day=DD/` — Parquet (from Glue) |
| **Task 4 Output** | XCom: `processed_file_count`, `processed_size_bytes` |
| **Task 5 Output** | SNS notification to subscribed emails/SMS |

## Airflow Variables Required

| Key | Example Value |
|-----|---------------|
| `account_id` | `123456789012` |
| `sns_topic_arn` | `arn:aws:sns:us-east-1:123:data-pipeline-alerts` |
| `data_lake_bucket` | `handson-data-lake-123456789012` |
| `glue_job_name` | `handson-etl-job` |

## Lessons Learned

- `catchup=False` is almost always what you want — prevents hundreds of backfill runs
- `mode="reschedule"` on sensors releases worker slots between pokes — cheaper on MWAA
- `on_failure_callback` on the DAG fires on any task failure — single alerting point
- `Variable.get()` with `default_var` prevents DAG import errors when variable not set
- MWAA costs $22/day whether or not any DAGs run — always delete after learning
- Local Docker is 100% free and uses the exact same Airflow API as MWAA

## Full Guide

For the complete 10-section implementation guide (Console UI + CLI, Code Deep Dive,
Verification, Screenshots, Cleanup):

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
