# Architecture — Project 9.5 Airflow Data Orchestration

## DAG Execution Flow

```
Schedule: 0 2 * * * (2am UTC daily)
    │
    ▼
Airflow Scheduler triggers DAG: daily_data_pipeline
    │
    ▼
Task 1: check_source_data (S3KeySensor)
    │ Waits until raw/orders/year=YYYY/month=MM/ exists in S3
    │ Timeout: 1 hour, check every 5 minutes
    ▼
Task 2: run_glue_etl (GlueJobOperator)
    │ Starts Glue job, waits for completion
    │ Passes execution_date as argument
    ▼
Task 3: run_dbt_transformations (PythonOperator)
    │ Runs dbt models via subprocess
    ▼
Task 4: validate_data_quality (PythonOperator)
    │ Runs Great Expectations checks
    │ Fails pipeline if data quality issues found
    ▼
Task 5a: notify_success (SnsPublishOperator)  ← if all tasks succeeded
Task 5b: notify_failure (SnsPublishOperator)  ← if any task failed
```

## Local vs MWAA

```
Local Docker (for learning):
  docker compose up -d
  Open: http://localhost:8080
  Cost: $0
  Setup: 5 minutes

Amazon MWAA (for production):
  Fully managed, auto-scaling
  Cost: ~$670/month (mw1.small + 1 worker)
  Setup: 30 minutes + VPC config

Recommendation:
  Develop and test locally → deploy to MWAA for production
```

## Airflow Key Concepts

```
DAG (Directed Acyclic Graph):
  Python file defining tasks and dependencies
  task_a >> task_b  means task_b runs after task_a

Operator:
  Defines what a task does
  PythonOperator, BashOperator, GlueJobOperator, etc.

Sensor:
  Waits for a condition to be true
  S3KeySensor, HttpSensor, ExternalTaskSensor

XCom:
  Pass small data between tasks
  task_instance.xcom_push("key", "value")
  task_instance.xcom_pull(task_ids="task_a", key="key")
```
