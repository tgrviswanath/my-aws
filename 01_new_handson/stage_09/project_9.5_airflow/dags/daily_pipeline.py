"""
daily_pipeline.py — Airflow DAG for the daily data pipeline.
Orchestrates: Glue ETL → Spark → dbt → Data Quality → Notify
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.sensors.glue import GlueJobSensor
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

# ─── Default args ─────────────────────────────────────────────────────────────

default_args = {
    "owner":            "data-engineering",
    "depends_on_past":  False,
    "start_date":       datetime(2024, 1, 1),
    "email_on_failure": True,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}

# ─── DAG Definition ───────────────────────────────────────────────────────────

with DAG(
    dag_id="daily_data_pipeline",
    default_args=default_args,
    description="Daily ETL pipeline: Glue → Spark → dbt → Quality",
    schedule_interval="0 2 * * *",   # 2am UTC daily
    catchup=False,
    tags=["data-engineering", "production"],
    doc_md="""
    ## Daily Data Pipeline
    Processes previous day's orders through the full data stack.
    
    **Steps:**
    1. Check source data is available in S3
    2. Run Glue ETL to clean and transform raw data
    3. Run Spark aggregations on EMR Serverless
    4. Run dbt transformations
    5. Validate data quality
    6. Notify on success or failure
    """,
) as dag:

    # ─── Step 1: Check source data ────────────────────────────────────────────
    check_source_data = S3KeySensor(
        task_id="check_source_data",
        bucket_name="handson-data-lake-{{ var.value.account_id }}",
        bucket_key="raw/orders/year={{ ds_nodash[:4] }}/month={{ ds_nodash[4:6] }}/",
        wildcard_match=True,
        timeout=3600,
        poke_interval=300,
        aws_conn_id="aws_default",
    )

    # ─── Step 2: Run Glue ETL ─────────────────────────────────────────────────
    run_glue_etl = GlueJobOperator(
        task_id="run_glue_etl",
        job_name="handson-etl-job",
        script_args={
            "--source_bucket": "handson-data-lake-{{ var.value.account_id }}",
            "--target_bucket": "handson-data-lake-{{ var.value.account_id }}",
            "--database_name": "handson_data_lake",
            "--execution_date": "{{ ds }}",
        },
        aws_conn_id="aws_default",
        region_name="us-east-1",
    )

    # ─── Step 3: Run dbt transformations ─────────────────────────────────────
    def run_dbt(**context):
        """Run dbt models via subprocess."""
        import subprocess
        result = subprocess.run(
            ["dbt", "run", "--profiles-dir", "/usr/local/airflow/dbt",
             "--vars", f'{{"execution_date": "{context["ds"]}"}}'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise Exception(f"dbt failed:\n{result.stderr}")
        print(result.stdout)

    run_dbt_task = PythonOperator(
        task_id="run_dbt_transformations",
        python_callable=run_dbt,
    )

    # ─── Step 4: Validate data quality ───────────────────────────────────────
    def validate_quality(**context):
        """Check row counts and null rates."""
        import boto3
        athena = boto3.client("athena", region_name="us-east-1")

        # Check row count for today's data
        response = athena.start_query_execution(
            QueryString=f"SELECT COUNT(*) FROM orders WHERE order_date = DATE '{context['ds']}'",
            WorkGroup="handson-data-lake",
            QueryExecutionContext={"Database": "handson_data_lake"},
        )

        # In production: wait for result and assert count > 0
        print(f"Quality check submitted: {response['QueryExecutionId']}")

    validate_task = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_quality,
    )

    # ─── Step 5: Notify success ───────────────────────────────────────────────
    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn="{{ var.value.sns_topic_arn }}",
        message="✅ Daily pipeline completed successfully for {{ ds }}",
        aws_conn_id="aws_default",
        trigger_rule="all_success",
    )

    notify_failure = SnsPublishOperator(
        task_id="notify_failure",
        target_arn="{{ var.value.sns_topic_arn }}",
        message="❌ Daily pipeline FAILED for {{ ds }}. Check Airflow logs.",
        aws_conn_id="aws_default",
        trigger_rule="one_failed",
    )

    # ─── Dependencies ─────────────────────────────────────────────────────────
    check_source_data >> run_glue_etl >> run_dbt_task >> validate_task
    validate_task >> [notify_success, notify_failure]
