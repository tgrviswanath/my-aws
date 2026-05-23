# Stage 9 — Data Engineering & Analytics

> Master modern data engineering on AWS: data lakes, ETL pipelines, real-time streaming, Spark on EMR, Airflow orchestration, dbt transformations, data quality, schema evolution, and Redshift analytics.

---

## Projects

| # | Project | Key Services | Difficulty |
|---|---------|-------------|-----------|
| 9.1 | Data Lake Architecture | S3, Glue Catalog, Athena, Lake Formation | ⭐⭐ |
| 9.2 | Glue ETL Pipeline | Glue Jobs, PySpark, S3, Athena | ⭐⭐⭐ |
| 9.3 | Real-time Streaming Pipeline | Kinesis Data Streams, Lambda, Firehose, S3 | ⭐⭐⭐ |
| 9.4 | Spark Processing on EMR | EMR, Apache Spark, S3, Athena | ⭐⭐⭐ |
| 9.5 | Airflow Data Orchestration | MWAA, Glue, EMR Serverless, SNS | ⭐⭐⭐⭐ |
| 9.6 | dbt Transformation Pipeline | dbt, Athena/Redshift, S3 | ⭐⭐⭐ |
| 9.7 | Data Quality Validation | Great Expectations, S3, CloudWatch | ⭐⭐⭐ |
| 9.8 | Schema Evolution & Partitioning | Glue Schema Registry, Athena, S3 | ⭐⭐⭐ |
| 9.9 | Redshift Data Warehouse | Redshift Serverless, S3 COPY, Redshift Data API | ⭐⭐⭐ |

---

## Folder Structure

```
stage_09/
├── project_9.1_data_lake/
│   ├── code/data_lake_setup.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.2_glue_etl/
│   ├── src/etl_job.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.3_kinesis_streaming/
│   ├── src/producer.py  |  consumer_lambda.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.4_spark_emr/
│   ├── src/spark_job.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.5_airflow/
│   ├── dags/daily_pipeline.py  |  code/orders_dag.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.6_dbt/
│   ├── dbt_project/models/staging/  |  marts/
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.7_data_quality/
│   ├── src/validate_orders.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_9.8_schema_evolution/
│   ├── src/schema_evolution_demo.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
└── project_9.9_redshift/
    ├── code/redshift_operations.py
    ├── terraform/main.tf
    ├── README.md  |  steps.md  |  verify.md ✅
```

---

## Data Pipeline Flow

```
Raw Data Sources
  → S3 raw zone (9.1)
    → Glue ETL / Spark EMR (9.2, 9.4)
      → S3 processed zone (Parquet, partitioned)
        → dbt transformations (9.6)
          → S3 curated zone / Redshift (9.9)
            → Athena / BI tools

Orchestration: Airflow MWAA (9.5)
Streaming: Kinesis → Lambda → S3 (9.3)
Quality gates: Great Expectations (9.7)
Schema control: Glue Schema Registry (9.8)
```

---

## Quick Start

```bash
# Start with data lake foundation
cd project_9.1_data_lake/terraform
terraform init && terraform apply
python code/data_lake_setup.py --bucket $(terraform output -raw data_lake_bucket)

# Then run ETL
cd ../project_9.2_glue_etl/terraform
terraform init && terraform apply
aws glue start-job-run --job-name handson-etl-job
```

---

## 7. Verification & Validation

Every project in Stage 9 has a `verify.md` covering:

- **AWS Console verification** — what to check and expected state for each resource
- **AWS CLI verification commands** — exact commands with expected outputs
- **Terraform state verification** — `terraform state list`, `terraform state show`, `terraform output`, `terraform plan`
- **Logs / monitoring checks** — Glue job run history, Kinesis metrics, Airflow DAG run status
- **Expected successful outputs** — exact JSON / text output to compare against
- **Health check procedures** — end-to-end data flow tests (upload → ETL → query)
- **Verification checklist** — checkbox list to tick off before marking project complete

### Quick Verification Reference

| Project | Key CLI Check | Expected Result |
|---------|--------------|-----------------|
| 9.1 Data Lake | `aws glue get-databases` | raw_db, processed_db, curated_db listed |
| 9.2 Glue ETL | `aws glue get-job-run --job-name handson-etl-job --run-id $ID` | State=SUCCEEDED |
| 9.3 Kinesis | `aws kinesis describe-stream-summary --stream-name handson-events` | Status=ACTIVE |
| 9.4 EMR | `aws emr describe-step --cluster-id $ID --step-id $STEP` | State=COMPLETED |
| 9.5 Airflow | `aws mwaa get-environment --name handson-airflow` | Status=AVAILABLE |
| 9.6 dbt | `dbt test` | All tests passed |
| 9.7 Data Quality | `python src/validate_orders.py` | All checks PASSED (clean data) |
| 9.8 Schema | `aws glue list-schema-versions --schema-id ...` | v1 and v2 AVAILABLE |
| 9.9 Redshift | `python code/redshift_operations.py report` | Analytics report printed |

---

## Key Lessons

- **Parquet over CSV**: 10x cheaper to query in Athena, 5x smaller on disk — always convert
- **Partition pruning**: `WHERE year='2024' AND month='01'` skips irrelevant S3 files — 100x faster
- **Glue bookmarks**: prevent reprocessing already-seen files on reruns — idempotency
- **Kinesis vs SQS**: Kinesis = ordered, replayable, multiple consumers; SQS = simpler, cheaper
- **dbt ref()**: builds dependency DAG automatically — never hardcode table names
- **Fail fast on quality**: catch bad data at ingestion, not at the dashboard
- **Schema evolution**: add optional fields only — never rename or delete columns
- **Redshift COPY**: bulk load from S3 — 100x faster than row-by-row INSERT

---

## Certification Alignment

| Cert | Relevant Projects |
|------|------------------|
| AWS Data Engineer Associate | 9.1, 9.2, 9.3, 9.4, 9.5, 9.9 |
| AWS Solutions Architect Professional | 9.1, 9.3, 9.5 |
| AWS Developer Associate | 9.3 |
