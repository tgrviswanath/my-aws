# Architecture — Project 9.5 Airflow Data Orchestration

## Resources

| Resource | Name | Notes |
|----------|------|-------|
| Primary DAG | `daily_data_pipeline` | dags/daily_pipeline.py |
| Advanced DAG | `orders_data_pipeline` | code/orders_dag.py |
| MWAA Environment | `handson-airflow` | emr-2.8.1, mw1.small |
| IAM Role | `handson-mwaa-role` | Trust: airflow.amazonaws.com + airflow-env.amazonaws.com |
| S3 Bucket | `handson-mwaa-ACCOUNT` | DAG files, versioning enabled |

---

## DAG Execution Flow (daily_pipeline.py)

```
Schedule: 0 2 * * * (2am UTC every day)
Max active runs: 1 (no overlap)
Catchup: False (no backfill)

check_source_data  (S3KeySensor)
    │
    │  Polls: raw/orders/year=YYYY/month=MM/ every 5 min
    │  Timeout: 1 hour
    │  mode: reschedule (releases worker slot between pokes)
    │
    ▼
run_glue_etl  (GlueJobOperator)
    │
    │  Job: handson-etl-job
    │  Args: --source_bucket, --execution_date, --source_prefix, --target_prefix
    │  Retries: 2 with 5-min delay
    │  Waits for Glue status: SUCCEEDED → continue, FAILED → retry/fail
    │
    ▼
run_dbt_transformations  (PythonOperator)
    │
    │  Runs: subprocess.run(["dbt", "run", "--select", "orders+", ...])
    │  Then: dbt test (if run fails, task fails)
    │  Target: prod  |  Schema: analytics
    │
    ▼
validate_data_quality  (PythonOperator)
    │
    │  Checks: S3 files exist at processed/orders/year=YYYY/month=MM/day=DD/
    │  Checks: total_size > 1 KB
    │  Pushes XCom: processed_file_count, processed_size_bytes
    │
    ├──▶ notify_success  (SnsPublishOperator)
    │         trigger_rule="all_success"
    │         SNS topic: var.value.sns_topic_arn
    │
    └──▶ notify_failure  (SnsPublishOperator)
              trigger_rule="one_failed"
              Fires if ANY task above failed
```

---

## Advanced DAG Flow (orders_dag.py)

```
orders_data_pipeline  (dag_id)
    │
    │  on_failure_callback: notify_failure_fn
    │  (fires immediately on any task failure — no need for trigger_rule task)
    │
check_source_data  (S3KeySensor)
    │  bucket_key: "raw/orders/{{ execution_date.strftime('%Y/%m/%d') }}/orders_{{ ds_nodash }}.csv"
    │  Exact file match (not wildcard)
    ▼
run_glue_etl  (GlueJobOperator — retries=3)
    │  script_args include --execution_date, --source_bucket, --target_prefix
    ▼
validate_data_quality  (PythonOperator)
    │  xcom_push: processed_file_count, processed_size_bytes
    ▼
run_dbt_models  (BashOperator)
    │  dbt run --select orders+ && dbt test --select orders+
    │  env vars: DBT_REDSHIFT_HOST, DBT_REDSHIFT_PASSWORD (from Airflow Variables)
    ▼
notify_success  (PythonOperator → sns.publish())
    Sends: ✓ Orders Pipeline SUCCESS — YYYY-MM-DD + run details
```

---

## Airflow Components

```
┌──────────────────────────────────────────────────────┐
│               AIRFLOW COMPONENTS                     │
│                                                      │
│  Scheduler     ─── reads DAG files every 30s        │
│                ─── creates TaskInstance records      │
│                ─── triggers tasks based on deps      │
│                                                      │
│  Webserver     ─── serves the Airflow UI             │
│                ─── REST API for triggers/queries     │
│                                                      │
│  Worker        ─── executes task operators           │
│  (Celery)      ─── reports result to metadata DB     │
│                                                      │
│  Metadata DB   ─── PostgreSQL                        │
│  (postgres)    ─── stores DAG runs, task instances  │
│                ─── XCom values, Variables            │
│                                                      │
│  Message Queue ─── Redis (Celery broker)             │
│  (redis)       ─── task queue between scheduler/worker│
└──────────────────────────────────────────────────────┘
```

---

## Task Dependency Syntax

```python
# Linear chain:
A >> B >> C >> D

# Fan-out (B and C both run after A):
A >> [B, C]

# Fan-in (C runs after both A and B):
[A, B] >> C

# Mixed:
check >> run_glue >> validate
validate >> [notify_success, notify_failure]
```

---

## Sensor Modes

```python
# mode="poke" (default): worker held while waiting
S3KeySensor(mode="poke", poke_interval=60)
# Worker slot: HELD for entire wait period (expensive on MWAA)

# mode="reschedule": worker released between checks
S3KeySensor(mode="reschedule", poke_interval=300)
# Worker slot: RELEASED between pokes (cheaper — especially for MWAA)
# MWAA worker cost ~$0.49/hr — freeing it during 1hr wait saves ~$0.49
```

---

## Local Docker vs MWAA

| Aspect | Local Docker | MWAA |
|--------|-------------|------|
| Cost | $0 | ~$670/month |
| Setup | 5 min | 30 min + VPC |
| Airflow version | 2.8.1 (pinned) | 2.8.1 (AWS managed) |
| Scaling | 1 worker | Auto-scales |
| Access | localhost only | Team URL |
| Persistence | Volumes (local) | Managed by AWS |
| AWS IAM | Use local creds | MWAA execution role |
| Use for | Learning, dev | Production |

---

## IAM Trust Policy (Two Principals Required)

```json
{
  "Principal": {
    "Service": [
      "airflow.amazonaws.com",
      "airflow-env.amazonaws.com"
    ]
  }
}
```
- `airflow.amazonaws.com` — the MWAA service creates/manages environments
- `airflow-env.amazonaws.com` — the environment itself (workers, scheduler) reads S3, writes logs
- Both principals are required — using only one causes MWAA creation to fail

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
