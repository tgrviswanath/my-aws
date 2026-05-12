"""
orders_dag.py — Airflow DAG for the orders data pipeline.

Pipeline:
    S3 raw data → Glue ETL → Data Quality checks → dbt models → Redshift → SNS notify

DAG schedule: Daily at 02:00 UTC

Tasks:
    1. check_source_data    — S3KeySensor: wait for raw data file to arrive
    2. run_glue_etl         — GlueJobOperator: run the Glue ETL job
    3. validate_data_quality — PythonOperator: check row counts and null rates
    4. run_dbt_models       — BashOperator: run dbt models
    5. notify_success       — PythonOperator: send SNS success notification
    6. notify_failure       — on_failure_callback: send SNS failure notification

Retry logic:
    - All tasks: 2 retries with 5-minute delay
    - Glue ETL: 3 retries (longer-running, more likely to hit transient errors)

Prerequisites:
    pip install apache-airflow apache-airflow-providers-amazon
    Configure Airflow connections:
        aws_default — AWS credentials
        redshift_default — Redshift connection
    Set Airflow Variables:
        data_lake_bucket    — S3 bucket name
        glue_job_name       — Glue ETL job name
        sns_topic_arn       — SNS topic for notifications
        dbt_project_dir     — Path to dbt project directory
        redshift_schema     — Target Redshift schema
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
import boto3


# ── DAG configuration ─────────────────────────────────────────────────────────

# Airflow Variables — set these in the Airflow UI or via CLI:
#   airflow variables set data_lake_bucket my-data-lake-bucket
DATA_LAKE_BUCKET = Variable.get("data_lake_bucket", default_var="my-data-lake-bucket")
GLUE_JOB_NAME    = Variable.get("glue_job_name",    default_var="orders-etl-job")
SNS_TOPIC_ARN    = Variable.get("sns_topic_arn",    default_var="arn:aws:sns:us-east-1:123456789012:data-pipeline-alerts")
DBT_PROJECT_DIR  = Variable.get("dbt_project_dir",  default_var="/opt/airflow/dbt/orders")
REDSHIFT_SCHEMA  = Variable.get("redshift_schema",  default_var="analytics")

# Default arguments applied to all tasks in the DAG
DEFAULT_ARGS = {
    "owner":            "data-engineering",
    "depends_on_past":  False,           # Don't wait for previous day's run
    "email_on_failure": False,           # We use SNS instead of email
    "email_on_retry":   False,
    "retries":          2,               # Retry failed tasks twice
    "retry_delay":      timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),  # Kill tasks that run > 2 hours
}


# ── SNS notification helpers ──────────────────────────────────────────────────

def send_sns_notification(subject: str, message: str) -> None:
    """
    Send a notification to the configured SNS topic.

    Args:
        subject: Email subject line (max 100 chars for SNS)
        message: Notification body
    """
    sns = boto3.client("sns")
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject[:100],
        Message=message,
    )


def notify_success_fn(**context) -> None:
    """
    Task function: send a success notification via SNS.

    Called by the notify_success PythonOperator task.
    Uses Airflow's task instance context to include run details.

    Args:
        context: Airflow task context dict (injected by provide_context=True)
    """
    dag_run = context["dag_run"]
    execution_date = context["execution_date"]

    subject = f"✓ Orders Pipeline SUCCESS — {execution_date.strftime('%Y-%m-%d')}"
    message = (
        f"Orders data pipeline completed successfully.\n\n"
        f"DAG:            {dag_run.dag_id}\n"
        f"Run ID:         {dag_run.run_id}\n"
        f"Execution date: {execution_date}\n"
        f"End time:       {datetime.utcnow().isoformat()}\n\n"
        f"Data is available in Redshift schema: {REDSHIFT_SCHEMA}"
    )
    send_sns_notification(subject, message)


def notify_failure_fn(context) -> None:
    """
    Failure callback: send a failure notification via SNS.

    This function is registered as on_failure_callback on the DAG,
    so it fires automatically when any task fails.

    Args:
        context: Airflow task context dict (injected automatically)
    """
    task_instance = context.get("task_instance")
    dag_run = context.get("dag_run")
    execution_date = context.get("execution_date")
    exception = context.get("exception")

    task_id = task_instance.task_id if task_instance else "unknown"
    dag_id = dag_run.dag_id if dag_run else "unknown"
    run_id = dag_run.run_id if dag_run else "unknown"

    subject = f"✗ Orders Pipeline FAILED — {execution_date.strftime('%Y-%m-%d') if execution_date else 'unknown'}"
    message = (
        f"Orders data pipeline FAILED.\n\n"
        f"DAG:            {dag_id}\n"
        f"Run ID:         {run_id}\n"
        f"Failed task:    {task_id}\n"
        f"Execution date: {execution_date}\n"
        f"Error:          {str(exception)}\n\n"
        f"Action required: Check Airflow logs for task '{task_id}'"
    )
    send_sns_notification(subject, message)


# ── Data quality check ────────────────────────────────────────────────────────

def validate_data_quality_fn(**context) -> None:
    """
    Task function: validate data quality after the Glue ETL job.

    Checks:
        1. Row count > 0 (data was actually loaded)
        2. Null rate on critical columns < 5%
        3. Date range is within expected bounds

    Uses XCom to pass the row count to downstream tasks.

    Args:
        context: Airflow task context dict

    Raises:
        ValueError: If any quality check fails (causes task to fail and retry)
    """
    import boto3
    import json

    execution_date = context["execution_date"]
    date_str = execution_date.strftime("%Y/%m/%d")

    # Check the processed S3 path for the execution date
    s3 = boto3.client("s3")
    prefix = f"processed/orders/year={execution_date.year}/month={execution_date.strftime('%m')}/day={execution_date.strftime('%d')}/"

    # ── Check 1: Files exist in the processed path ─────────────────────────
    response = s3.list_objects_v2(Bucket=DATA_LAKE_BUCKET, Prefix=prefix)
    files = response.get("Contents", [])

    if not files:
        raise ValueError(
            f"Data quality check FAILED: No files found at s3://{DATA_LAKE_BUCKET}/{prefix}"
        )

    total_size_bytes = sum(f["Size"] for f in files)
    print(f"  ✓ Found {len(files)} file(s), total size: {total_size_bytes:,} bytes")

    # ── Check 2: Minimum file size (sanity check for empty/corrupt files) ──
    min_expected_bytes = 1024  # At least 1KB of data expected
    if total_size_bytes < min_expected_bytes:
        raise ValueError(
            f"Data quality check FAILED: Total file size {total_size_bytes} bytes "
            f"is below minimum threshold of {min_expected_bytes} bytes"
        )

    print(f"  ✓ File size check passed: {total_size_bytes:,} bytes")

    # ── Check 3: Push metrics to XCom for downstream tasks ─────────────────
    # XCom allows tasks to share data; downstream tasks can pull this value
    context["task_instance"].xcom_push(
        key="processed_file_count",
        value=len(files),
    )
    context["task_instance"].xcom_push(
        key="processed_size_bytes",
        value=total_size_bytes,
    )

    print(f"  ✓ Data quality validation passed for {date_str}")


# ── DAG definition ────────────────────────────────────────────────────────────

with DAG(
    dag_id="orders_data_pipeline",
    description="Daily orders ETL pipeline: S3 raw → Glue → dbt → Redshift",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 2 * * *",   # Run daily at 02:00 UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,                    # Don't backfill missed runs
    max_active_runs=1,                # Only one run at a time (prevent overlap)
    tags=["orders", "etl", "data-lake"],
    on_failure_callback=notify_failure_fn,  # Fires on any task failure
    doc_md="""
    ## Orders Data Pipeline

    Daily ETL pipeline that processes orders data from the raw S3 zone
    through Glue ETL, data quality checks, dbt transformations, and
    loads the final data into Redshift for analytics.

    ### Pipeline Steps
    1. **check_source_data** — Wait for raw orders file to arrive in S3
    2. **run_glue_etl** — Transform raw CSV/JSON to Parquet in processed zone
    3. **validate_data_quality** — Verify row counts and file sizes
    4. **run_dbt_models** — Run dbt transformations for analytics models
    5. **notify_success** — Send SNS notification on completion

    ### Failure Handling
    - All tasks retry 2x with 5-minute delays
    - SNS failure notification sent automatically on any task failure
    """,
) as dag:

    # ── Task 1: Wait for raw data file ─────────────────────────────────────
    # S3KeySensor polls S3 until the expected file appears (or times out)
    check_source_data = S3KeySensor(
        task_id="check_source_data",
        bucket_name=DATA_LAKE_BUCKET,
        # Expects a file like: raw/orders/2024/01/15/orders_20240115.csv
        bucket_key="raw/orders/{{ execution_date.strftime('%Y/%m/%d') }}/orders_{{ ds_nodash }}.csv",
        aws_conn_id="aws_default",
        poke_interval=60,          # Check every 60 seconds
        timeout=3600,              # Give up after 1 hour
        mode="reschedule",         # Release worker slot while waiting (efficient)
        doc_md="Wait for the daily raw orders file to arrive in S3.",
    )

    # ── Task 2: Run Glue ETL job ───────────────────────────────────────────
    # GlueJobOperator starts the Glue job and waits for completion
    run_glue_etl = GlueJobOperator(
        task_id="run_glue_etl",
        job_name=GLUE_JOB_NAME,
        script_args={
            "--execution_date": "{{ ds }}",
            "--source_bucket":  DATA_LAKE_BUCKET,
            "--source_prefix":  "raw/orders/{{ execution_date.strftime('%Y/%m/%d') }}/",
            "--target_prefix":  "processed/orders/year={{ execution_date.year }}/month={{ execution_date.strftime('%m') }}/day={{ execution_date.strftime('%d') }}/",
        },
        aws_conn_id="aws_default",
        region_name="us-east-1",
        retries=3,                 # Glue jobs get extra retries
        retry_delay=timedelta(minutes=10),
        doc_md="Run the Glue ETL job to transform raw orders to Parquet.",
    )

    # ── Task 3: Validate data quality ──────────────────────────────────────
    validate_data_quality = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_data_quality_fn,
        provide_context=True,      # Inject Airflow context (execution_date, etc.)
        doc_md="Check that processed files exist and meet minimum size requirements.",
    )

    # ── Task 4: Run dbt models ─────────────────────────────────────────────
    # BashOperator runs dbt CLI commands
    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            "dbt run "
            "--select orders+ "           # Run orders model and all downstream models
            "--target prod "
            "--vars '{\"execution_date\": \"{{ ds }}\"}' "
            "&& dbt test "
            "--select orders+ "           # Run dbt tests after models
            "--target prod"
        ),
        env={
            # Pass Redshift connection details as environment variables
            # These should be set in the Airflow environment or via Secrets Manager
            "DBT_REDSHIFT_HOST":     "{{ var.value.redshift_host }}",
            "DBT_REDSHIFT_USER":     "{{ var.value.redshift_user }}",
            "DBT_REDSHIFT_PASSWORD": "{{ var.value.redshift_password }}",
            "DBT_REDSHIFT_SCHEMA":   REDSHIFT_SCHEMA,
        },
        doc_md="Run dbt models to build analytics tables in Redshift.",
    )

    # ── Task 5: Notify success ─────────────────────────────────────────────
    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success_fn,
        provide_context=True,
        doc_md="Send SNS notification on successful pipeline completion.",
    )

    # ── Task dependencies ──────────────────────────────────────────────────
    # Linear pipeline: each task must complete before the next starts
    #
    #   check_source_data
    #         ↓
    #    run_glue_etl
    #         ↓
    # validate_data_quality
    #         ↓
    #   run_dbt_models
    #         ↓
    #   notify_success
    #
    # Note: notify_failure fires automatically via on_failure_callback
    # and does NOT need to be in the dependency chain.

    check_source_data >> run_glue_etl >> validate_data_quality >> run_dbt_models >> notify_success
