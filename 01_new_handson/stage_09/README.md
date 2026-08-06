# Stage 9 — Data Engineering & Analytics

Build a complete, production-grade data platform on AWS: raw data lands in a
medallion data lake, flows through automated ETL, real-time streaming, distributed
Spark compute, SQL transformations, quality gates, schema management, and lands in
a columnar data warehouse — all orchestrated by Airflow.

This is the stack used at scale by data-driven companies. Each project is independently
deployable, but they compose into a single end-to-end pipeline across all nine projects.

---

## Projects at a Glance

| # | Project | Core Concept | Key Services | Difficulty | Cost/Session |
|---|---------|-------------|--------------|-----------|-------------|
| 9.1 | Data Lake Architecture | Medallion zones, Glue Catalog, Lake Formation | S3, Glue, Athena, Lake Formation | ⭐⭐ | ~$0.09 |
| 9.2 | Glue ETL Pipeline | Serverless PySpark: CSV → Parquet | Glue ETL, S3, Athena | ⭐⭐ | ~$0.15/run |
| 9.3 | Kinesis Streaming | Real-time event processing, DLQ, bisect retry | Kinesis, Lambda, DynamoDB, SQS | ⭐⭐⭐ | ~$0.03 |
| 9.4 | Spark on EMR Serverless | Distributed compute, AQE, window functions | EMR Serverless, S3, IAM | ⭐⭐⭐ | ~$0.07/run |
| 9.5 | Airflow Orchestration | DAGs, sensors, retries, XCom, MWAA | MWAA, Glue, SNS, Airflow | ⭐⭐⭐ | $0 (Docker) |
| 9.6 | dbt Transformations | ELT, incremental models, data tests | dbt Core, Athena, Glue | ⭐⭐ | ~$0.01 |
| 9.7 | Data Quality (GX) | Expectation suites, quarantine, pipeline gates | Lambda, SNS, EventBridge, GX | ⭐⭐⭐ | ~$0.01 |
| 9.8 | Schema Evolution | Safe column adds, partition projection, registry | Glue Schema Registry, S3, Parquet | ⭐⭐ | ~$0.01 |
| 9.9 | Redshift Warehouse | OLAP, DISTKEY/SORTKEY, COPY, VACUUM | Redshift Serverless, S3, psycopg2 | ⭐⭐⭐ | ~$0.36/hr |

---

## Recommended Learning Order

Work through the projects in number order — each one builds on the previous:

```
9.1 → 9.2 → 9.3 → 9.4 → 9.5 → 9.6 → 9.7 → 9.8 → 9.9
```

**Why this order:**

- **9.1 first** — creates the S3 bucket, Glue database, IAM role, and Athena workgroup
  that every subsequent project reuses. Do not skip it.
- **9.2 after 9.1** — Glue ETL reads the raw zone created in 9.1 and writes to `processed/`.
- **9.3 in parallel** — Kinesis is independent of 9.1/9.2 (separate Terraform), but
  understanding the data model from 9.1/9.2 makes the events make sense.
- **9.4 after 9.2** — Spark reads from `raw/orders/` (created by 9.1/9.2 sample data).
- **9.5 after 9.2, 9.4, 9.6** — Airflow orchestrates Glue, dbt, and quality checks.
  Build the pieces first, then wire them together in Airflow.
- **9.6 after 9.1** — dbt reads from the Glue catalog table `handson_data_lake.orders`.
- **9.7 after 9.2** — Great Expectations validates `processed/orders/` Parquet output.
- **9.8 standalone** — can be done any time after 9.1 (uses same S3 bucket).
- **9.9 last** — COPY loads data from `processed/orders/` produced by 9.2 and 9.6.

---

## Standard File Structure Per Project

Every project follows the same layout:

```
project_9.X_name/
├── GUIDE.md                      ← Complete 10-section walkthrough (START HERE)
├── README.md                     ← Quick overview, architecture, cost, teardown
├── steps.md                      ← Condensed CLI commands reference
├── steps_awsconsoleui.md         ← Step-by-step Console UI guide
├── verify.md                     ← Verification checklist + CLI checks
├── cost_estimate.md              ← Detailed cost breakdown
├── src/ or code/                 ← Source code (Python, SQL)
├── terraform/                    ← Infrastructure as code (if applicable)
└── docs/
    └── architecture.md           ← Deep-dive: resource names, diagrams, key design decisions
```

**Exception — 9.2 has a 4-part split guide** instead of a single GUIDE.md:

```
project_9.2_glue_etl/
├── GUIDE_PART1_overview_architecture.md   ← Architecture + concepts + prerequisites
├── GUIDE_PART2_console_ui.md              ← Console UI implementation
├── GUIDE_PART3_cli_terraform.md           ← CLI + Terraform + code annotations
├── GUIDE_PART4_verification_cleanup.md    ← Verify + screenshots + cleanup
└── steps_awsconsoleui.md                  ← Standalone Console UI guide (improved template)
```

---

## Cross-Project Dependencies

| Project | Depends On | What It Needs |
|---------|-----------|--------------|
| 9.1 | None | Foundation project — must be deployed first |
| 9.2 | 9.1 | S3 bucket, IAM role (`handson-glue-role`), Glue database |
| 9.3 | None | Independent Terraform stack |
| 9.4 | 9.1 (data) | `raw/orders/` CSV files from 9.1 sample data |
| 9.5 | 9.2, 9.6 | Triggers `handson-etl-job` (9.2) and calls `dbt run` (9.6) |
| 9.6 | 9.1 | Reads `handson_data_lake.orders` Glue table |
| 9.7 | 9.2 | Validates `processed/orders/` Parquet from 9.2 ETL output |
| 9.8 | 9.1 (bucket) | Uses same S3 bucket for Parquet demo files |
| 9.9 | 9.2 or 9.4 | COPY loads from `processed/orders/` Parquet |

**9.5 Airflow is the integration project** — it wires 9.2, 9.6, and 9.7 into a single
scheduled pipeline. Build those three first.

**9.9 Redshift depends on data produced by 9.2** (and optionally 9.4 and 9.6).
The COPY command reads from `s3://BUCKET/processed/orders/`.


---

## End-to-End Pipeline Flow

```
External Data
    │  CSV files uploaded to S3 (manual or DMS)
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  9.1 DATA LAKE                                                       │
│  S3: raw/ → processed/ → curated/ → archive/                        │
│  Glue Catalog: dl_raw, dl_processed, dl_curated                     │
│  Lake Formation: column/row access control                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  9.2 GLUE ETL   │ │ 9.3 KINESIS  │ │  9.4 SPARK EMR   │
│  raw/*.csv      │ │ handson-     │ │  raw/orders/     │
│  → processed/   │ │ events       │ │  → processed/    │
│  orders/Parquet │ │ stream →     │ │  spark/product_  │
│  + orders_daily/│ │ Lambda →     │ │  monthly/        │
│  aggregates     │ │ DynamoDB     │ │  + customer_clv/ │
└────────┬────────┘ └──────────────┘ └──────────────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────────┐ ┌──────────────────────────────────────┐
│  9.7 DATA       │ │  9.6 dbt                              │
│  QUALITY (GX)   │ │  handson_data_lake.orders (Glue)      │
│  10 checks on   │ │  → stg_orders (VIEW)                  │
│  processed/     │ │  → fct_orders (INCREMENTAL TABLE)     │
│  orders/        │ │  + schema tests (schema.yml)          │
└────────┬────────┘ └──────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  9.5 AIRFLOW                                                         │
│  DAG: daily_data_pipeline  (schedule: 0 2 * * *)                    │
│  S3KeySensor → GlueJobOperator → PythonOp(dbt) → validate → SNS    │
│                                                                      │
│  DAG: orders_data_pipeline  (advanced reference)                    │
│  S3KeySensor → GlueJobOperator → validate → BashOp(dbt) → SNS      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┼
          │                │
          ▼                ▼
┌─────────────────┐ ┌──────────────────────────────────────┐
│  9.8 SCHEMA     │ │  9.9 REDSHIFT                         │
│  EVOLUTION      │ │  COPY from processed/orders/Parquet   │
│  v1+v2 Parquet  │ │  analytics.fact_orders                │
│  auto-merge     │ │  analytics.dim_date                   │
│  partition      │ │  Queries: revenue, CLV, regional      │
│  projection     │ │  BI tools via JDBC port 5439          │
└─────────────────┘ └──────────────────────────────────────┘
```

---

## Per-Project Summaries

### 9.1 — Data Lake Architecture

**What the code does (`code/data_lake_setup.py`):**
Creates S3 folder structure across 4 zones (`raw/`, `processed/`, `curated/`, `archive/`),
each with 5 domain sub-folders (`orders/`, `customers/`, `products/`, `inventory/`, `events/`).
Creates Glue databases (`dl_raw`, `dl_processed`, `dl_curated`, `dl_archive`),
registers S3 locations with Lake Formation, and creates a sample `dl_processed.orders`
Glue table (Parquet, partitioned by year/month/day).

| | Detail |
|-|--------|
| **Input** | `--bucket YOUR_BUCKET` CLI argument |
| **Output** | S3 zones, 4 Glue databases, 1 sample Glue table, Lake Formation registrations |
| **Key files** | `code/data_lake_setup.py`, `code/upload_sample_data.py`, `code/run_athena_query.py` |
| **Guide** | [GUIDE.md](project_9.1_data_lake/GUIDE.md) |

---

### 9.2 — Glue ETL Pipeline

**What the code does (`src/etl_job.py`):**
PySpark job on Glue workers. Reads raw CSVs from `s3://BUCKET/raw/orders/` as a
DynamicFrame. Drops nulls on `order_id`/`amount`, casts `amount` → DoubleType,
parses `order_date`, adds `year`/`month`/`day` partition columns, uppercases and
trims `product`, deduplicates on `order_id`, adds `processed_at` and `etl_job`
metadata columns. Then aggregates by year/month/day/product to produce a daily
summary. Writes two outputs: cleaned individual orders and daily aggregates.

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/raw/orders/*.csv` (order_id, customer_id, product, amount, order_date) |
| **Output 1** | `s3://BUCKET/processed/orders/year=YYYY/month=MM/*.parquet` |
| **Output 2** | `s3://BUCKET/processed/orders_daily/year=YYYY/month=MM/*.parquet` (aggregated) |
| **Job name** | `handson-etl-job` |
| **Key file** | `src/etl_job.py` |
| **Guide** | Split: GUIDE_PART1–4 (see file structure above) |

---

### 9.3 — Kinesis Real-Time Streaming

**What the code does:**
`src/producer.py` generates `ORDER_PLACED` events (order_id, customer_id, product,
quantity, amount, timestamp) and sends them to Kinesis stream `handson-events` using
`put_record()` with `PartitionKey=customer_id` for ordering. Sends 50 events at 0.05s
intervals by default.

`src/consumer_lambda.py` is triggered by the Kinesis event source mapping (batch=100,
bisect_on_error=true). Decodes base64 → JSON, aggregates by product within the batch,
then writes hourly totals to DynamoDB using `ADD` atomic operations. Revenue stored as
integer cents to avoid float precision errors.

| | Detail |
|-|--------|
| **Input** | `ORDER_PLACED` JSON events → Kinesis stream `handson-events` |
| **Output** | DynamoDB `handson-stream-aggregates`: pk=`PRODUCT#X` sk=`HOUR#YYYY-MM-DDTHH:00:00Z` |
| **DLQ** | `handson-kinesis-dlq` (SQS) for permanently failed records |
| **Key files** | `src/producer.py`, `src/consumer_lambda.py`, `terraform/main.tf` |
| **Guide** | [GUIDE.md](project_9.3_kinesis_streaming/GUIDE.md) |


---

### 9.4 — Spark on EMR Serverless

**What the code does (`src/spark_job.py`):**
PySpark job submitted to EMR Serverless app `handson-spark`. Reads CSVs from
`s3://BUCKET/raw/orders/` with `inferSchema=true`. Drops nulls on `order_id`/`amount`,
parses dates, casts `amount` to double, deduplicates. Computes two aggregations:
(1) product revenue by year/month (order_count, total_revenue, avg_order_value,
unique_customers) and (2) customer lifetime value (total_orders, lifetime_value,
first/last order dates). Also computes a per-customer running total using a Spark
window function. Writes two Parquet outputs. Uses AQE (Adaptive Query Execution)
for automatic partition coalescing.

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/raw/orders/*.csv` |
| **Output 1** | `s3://BUCKET/processed/spark/product_monthly/year=YYYY/month=M/*.parquet` |
| **Output 2** | `s3://BUCKET/processed/spark/customer_clv/*.parquet` |
| **EMR App** | `handson-spark` (emr-6.15.0, Spark 3.4) |
| **Key file** | `src/spark_job.py` |
| **Guide** | [GUIDE.md](project_9.4_spark_emr/GUIDE.md) |

---

### 9.5 — Airflow Orchestration

**What the code does:**
Two DAG files. `dags/daily_pipeline.py` defines `daily_data_pipeline` (scheduled
2am UTC daily). Tasks: `S3KeySensor` waits for raw orders file → `GlueJobOperator`
runs `handson-etl-job` → `PythonOperator` calls `dbt run` via subprocess → `PythonOperator`
validates quality via Athena row count query → `SnsPublishOperator` fires success or
failure notification based on `trigger_rule`.

`code/orders_dag.py` defines `orders_data_pipeline` (advanced reference) with exact
file match sensor, XCom push of file count/size, `on_failure_callback` on the DAG,
and BashOperator for dbt.

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/raw/orders/year=YYYY/month=MM/` (detected by S3KeySensor) |
| **Output** | Triggers: Glue ETL → dbt models → quality check → SNS notification |
| **Primary DAG ID** | `daily_data_pipeline` (dags/daily_pipeline.py) |
| **Advanced DAG ID** | `orders_data_pipeline` (code/orders_dag.py) |
| **Runtime** | Local Docker ($0) or Amazon MWAA (~$670/month) |
| **Key files** | `dags/daily_pipeline.py`, `code/orders_dag.py` |
| **Guide** | [GUIDE.md](project_9.5_airflow/GUIDE.md) |

---

### 9.6 — dbt Transformation Pipeline

**What the code does:**
Two dbt SQL models targeting Athena (via `dbt-athena-community`).

`models/staging/stg_orders.sql` materializes as a VIEW. Reads from
`{{ source('raw', 'orders') }}` (Glue table `handson_data_lake.orders`). Casts
`amount` → double, `quantity` → integer, `order_date` → date. Normalizes case:
`upper(trim(product))` → `product_name`, `lower(trim(coalesce(status,'unknown')))`
→ `order_status`. Filters `order_id IS NOT NULL AND amount > 0`.

`models/marts/fct_orders.sql` materializes as an INCREMENTAL TABLE (merge on
`order_id`). Adds `unit_price_usd` (amount/quantity), `order_tier`
(`high_value` ≥ $100, `medium_value` ≥ $50, else `low_value`), and
`_dbt_updated_at`. Incremental runs only process `order_date` newer than the
existing table max.

| | Detail |
|-|--------|
| **Input** | `handson_data_lake.orders` (Glue table over S3 raw CSV) |
| **stg_orders** | VIEW — cleaned, cast, normalized |
| **fct_orders** | INCREMENTAL TABLE — adds unit_price_usd, order_tier; merge on order_id |
| **Athena workgroup** | `handson-dbt` |
| **Key files** | `models/staging/stg_orders.sql`, `models/marts/fct_orders.sql` |
| **Guide** | [GUIDE.md](project_9.6_dbt/GUIDE.md) |

---

### 9.7 — Data Quality Validation

**What the code does (`src/validate_orders.py`):**
Loads Parquet from `s3://BUCKET/processed/orders/` into a pandas DataFrame using
PyArrow + s3fs. Creates a Great Expectations pandas datasource and runs exactly
**10 expectations** against the DataFrame:

1. `expect_table_row_count_to_be_between(min=1)` — at least 1 row
2. `expect_column_values_to_not_be_null("order_id")` — completeness
3. `expect_column_values_to_not_be_null("customer_id")`
4. `expect_column_values_to_not_be_null("amount")`
5. `expect_column_values_to_not_be_null("order_date")`
6. `expect_column_values_to_be_unique("order_id")` — uniqueness
7. `expect_column_values_to_be_between("amount", 0.01, 10000.0)` — validity
8. `expect_column_values_to_be_in_set("product", [...5 products...], mostly=0.99)`
9. `expect_column_values_to_match_strftime_format("order_date", "%Y-%m-%d")`
10. `expect_column_mean_to_be_between("amount", 10.0, 200.0)` — statistical

Exits with code 1 on failure (blocks Airflow/CI pipelines).

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/processed/orders/*.parquet` |
| **PASS output** | `data-quality/reports/TIMESTAMP.json` |
| **FAIL output** | SNS alert + `quarantine/orders/DATE/` + exit code 1 |
| **Check count** | Exactly 10 Great Expectations checks |
| **Key file** | `src/validate_orders.py` |
| **Guide** | [GUIDE.md](project_9.7_data_quality/GUIDE.md) |


---

### 9.8 — Schema Evolution & Partitioning

**What the code does (`src/schema_evolution_demo.py`):**
Demonstrates three Parquet schema evolution scenarios:

`write_v1_schema()` — writes 3 rows with 4 columns (order_id, customer_id, amount,
order_date) to `s3://BUCKET/schema-demo/year=2024/month=01/v1_orders.parquet`.

`write_v2_schema()` — writes 2 rows with 6 columns (adds `product` and `discount_pct`
as nullable fields) to the same S3 prefix as `v2_orders.parquet`.

`read_merged_schema()` — reads both files with PyArrow ParquetDataset (schema=None).
Parquet auto-merges schemas by column name: v1 rows get NaN for the two new columns.
Result: 5 rows, 6 columns.

`demonstrate_partition_pruning()` — prints cost comparison showing 10,000x savings
from year/month/day partitioning vs full table scan.

Also registers schema versions in Glue Schema Registry (`handson-registry`,
schema `orders-schema`) with safe/unsafe evolution rules documented.

| | Detail |
|-|--------|
| **Input** | v1 (4-col) + v2 (6-col) Parquet written to `schema-demo/year=2024/month=01/` |
| **Output** | Merged 5-row DataFrame, NaN for v1 missing columns |
| **Schema Registry** | `handson-registry` / `orders-schema` v1 + v2 |
| **Key file** | `src/schema_evolution_demo.py` |
| **Guide** | [GUIDE.md](project_9.8_schema_evolution/GUIDE.md) |

---

### 9.9 — Redshift Data Warehouse

**What the code does (`code/redshift_operations.py`):**
Four-command Python CLI using psycopg2 to operate a Redshift Serverless warehouse.

`setup` — creates schema `analytics`, fact table `analytics.fact_orders`
(DISTKEY on customer_id, SORTKEY on order_date+region, zstd/az64 encoding),
dimension table `analytics.dim_date` (DISTSTYLE ALL, ~4018 rows 2020–2030),
and populates dim_date using a recursive SQL CTE.

`load` — runs `COPY analytics.fact_orders FROM 's3://BUCKET/processed/orders/'`
with `FORMAT AS PARQUET`, then VACUUM SORT ONLY and ANALYZE.

`query` — runs 4 analytical queries: daily revenue last 30 days (with dim_date JOIN),
top 10 products by revenue, top 20 customers by lifetime value, revenue by region
with cancellation rate.

`report` — runs queries and prints formatted ASCII tables.

| | Detail |
|-|--------|
| **Input** | `s3://BUCKET/processed/orders/*.parquet` (from 9.2 Glue ETL) |
| **Namespace** | `handson-namespace` |
| **Workgroup** | `handson-workgroup` (8 RPU) |
| **Database** | `analytics` |
| **Tables** | `analytics.fact_orders`, `analytics.dim_date` |
| **Key file** | `code/redshift_operations.py` |
| **Guide** | [GUIDE.md](project_9.9_redshift/GUIDE.md) |

---

## Quick Verification Reference

| Project | CLI Command | Expected Output |
|---------|------------|----------------|
| 9.1 | `aws glue get-database --name dl_processed` | `"Name": "dl_processed"` |
| 9.1 | `aws s3 ls s3://BUCKET/raw/orders/` | Lists CSV files |
| 9.2 | `aws glue get-job-run --job-name handson-etl-job --run-id RUN_ID` | `"JobRunState": "SUCCEEDED"` |
| 9.2 | `aws s3 ls s3://BUCKET/processed/orders/ --recursive` | Parquet files listed |
| 9.3 | `aws kinesis describe-stream-summary --stream-name handson-events` | `"StreamStatus": "ACTIVE"` |
| 9.3 | `aws dynamodb scan --table-name handson-stream-aggregates` | Items with pk=`PRODUCT#...` |
| 9.4 | `aws emr-serverless get-job-run --application-id APP_ID --job-run-id RUN_ID` | `"state": "SUCCESS"` |
| 9.4 | `aws s3 ls s3://BUCKET/processed/spark/product_monthly/ --recursive` | Parquet files |
| 9.5 | `docker compose ps` (in airflow dir) | Services: healthy |
| 9.5 | Airflow UI → DAGs tab | `daily_data_pipeline` and `orders_data_pipeline` visible |
| 9.6 | `dbt run` | `Completed successfully` |
| 9.6 | `dbt test` | All tests passed |
| 9.7 | `python src\validate_orders.py` | `✅ PASSED — 10/10 checks` |
| 9.8 | `python src\schema_evolution_demo.py` | `Merged columns: [...6 cols...]` / `Total rows: 5` |
| 9.9 | `python code\redshift_operations.py report` | ASCII tables for 4 queries |

```powershell
# 9.3 — scan DynamoDB aggregates
aws dynamodb scan `
  --table-name handson-stream-aggregates `
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" `
  --output table

# 9.9 — verify table row count via Redshift Data API
aws redshift-data execute-statement `
  --workgroup-name handson-workgroup `
  --database analytics `
  --sql "SELECT COUNT(*) FROM analytics.fact_orders;"
```

---

## Key Concepts Map

| Concept | Project | Why It Matters |
|---------|---------|----------------|
| Medallion architecture (raw/processed/curated) | 9.1 | Universal data lake pattern at Netflix, Uber, Airbnb |
| Glue Crawler + Glue Catalog | 9.1 | Schema discovery + metadata store powering Athena |
| DynamicFrame + Job Bookmarks | 9.2 | Glue-native: handles bad CSV, prevents reprocessing |
| Parquet columnar format | 9.2, 9.4 | 10x smaller, 10x faster Athena queries than CSV |
| Partition pruning (year/month/day) | 9.2, 9.8 | Athena skips irrelevant data → lower cost |
| Kinesis shard capacity math | 9.3 | 1 shard = 1,000 rec/s or 1 MB/s — scale by adding shards |
| bisect_batch_on_function_error | 9.3 | Isolates bad records without stalling the stream |
| base64 decoding in Lambda | 9.3 | Kinesis always base64-encodes data in Lambda events |
| AQE (Adaptive Query Execution) | 9.4 | Spark auto-coalesces small partitions after shuffle |
| Window functions | 9.4 | Running totals, rankings without GROUP BY |
| DAG dependency syntax (>>, []) | 9.5 | Fan-out, fan-in task wiring in Airflow |
| Sensor reschedule mode | 9.5 | Releases worker slot between pokes — cheaper on MWAA |
| XCom for inter-task data | 9.5 | Pass small values between tasks (file count, sizes) |
| `source()` vs `ref()` | 9.6 | source = outside dbt; ref = another dbt model |
| Incremental materialization | 9.6 | Only processes new rows — efficient at scale |
| `is_incremental()` guard | 9.6 | WHERE clause added only on subsequent runs |
| Statistical mean check | 9.7 | Catches data drift that row-level checks miss |
| Schema evolution (add nullable) | 9.8 | Safe column addition — zero impact on v1 readers |
| Partition projection | 9.8 | Athena auto-discovers partitions, no MSCK REPAIR needed |
| DISTKEY vs DISTSTYLE ALL | 9.9 | DISTKEY for join columns; ALL for small dimension tables |
| SORTKEY + zone maps | 9.9 | Redshift skips irrelevant 1 MB blocks on range queries |
| COPY command | 9.9 | Parallel bulk load from S3 — far faster than INSERT |
| VACUUM + ANALYZE | 9.9 | Re-sort after COPY, update query planner statistics |


---

## Cost Summary

| Project | Free Tier? | Per Session | Monthly if Left Running |
|---------|-----------|-------------|------------------------|
| 9.1 Data Lake | Mostly ✅ | ~$0.09 | ~$1–2 (crawler + Athena) |
| 9.2 Glue ETL | ❌ | ~$0.15/run | ~$4.50 (daily trigger) |
| 9.3 Kinesis | ❌ | ~$0.03 | ~$10.80 (1 shard 24/7) |
| 9.4 Spark EMR | ❌ | ~$0.07/run | ~$2–3 (10 runs/day) |
| 9.5 Airflow | ✅ (Docker) | $0 | $0 (MWAA = ~$670/month) |
| 9.6 dbt | ✅ | ~$0.01 | ~$0.01 |
| 9.7 Data Quality | ✅ | ~$0.01 | ~$0.01 |
| 9.8 Schema Evolution | ✅ | ~$0.01 | ~$0.01 |
| 9.9 Redshift | ❌ | ~$0.36/hr | ~$260/month (8 RPU 24/7) |

**Always run `terraform destroy` and stop/delete AWS resources after each learning session.**

The two biggest cost risks:
- **Kinesis (9.3)**: charges $0.015/shard-hour whether or not records are sent.
  1 shard × 24h = $0.36/day. Always `terraform destroy` after the lab.
- **Redshift Serverless (9.9)**: 8 RPU base = $0.36/hr = ~$260/month.
  Delete the workgroup + namespace immediately after the lab.

---

## Complete Folder Structure

```
stage_09/
├── README.md                                    ← This file
├── project_9.1_data_lake.zip                    ← Stale zip (see note below)
├── project_9.1_data_lake_old.zip                ← Stale zip (see note below)
│
├── project_9.1_data_lake/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── steps_awsconsoleui.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── nextstep.md                              ← Updated: Stage 9 Completion Notes
│   ├── code/
│   │   ├── data_lake_setup.py                   ← S3 zones + Glue DB + Lake Formation
│   │   ├── upload_sample_data.py
│   │   ├── convert_to_parquet.py
│   │   └── run_athena_query.py
│   ├── data/
│   │   ├── sample_orders.csv
│   │   ├── sample_customers.csv
│   │   └── sample_products.csv
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   └── docs/
│       ├── architecture.md
│       └── data_dictionary.md
│
├── project_9.2_glue_etl/
│   ├── README.md
│   ├── steps.md
│   ├── steps_awsconsoleui.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── GUIDE_PART1_overview_architecture.md
│   ├── GUIDE_PART2_console_ui.md
│   ├── GUIDE_PART3_cli_terraform.md
│   ├── GUIDE_PART4_verification_cleanup.md
│   ├── src/
│   │   └── etl_job.py                           ← PySpark: CSV → Parquet, 2 outputs
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   └── docs/
│       └── architecture.md
│
├── project_9.3_kinesis_streaming/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── steps_awsconsoleui.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── src/
│   │   ├── producer.py                          ← Sends ORDER_PLACED to handson-events
│   │   └── consumer_lambda.py                   ← Lambda: aggregates → DynamoDB
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   └── docs/
│       └── architecture.md
│
├── project_9.4_spark_emr/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── steps_awsconsoleui.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── src/
│   │   └── spark_job.py                         ← PySpark: product_monthly + customer_clv
│   └── docs/
│       └── architecture.md
│
├── project_9.5_airflow/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── steps_awsconsoleui.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── dags/
│   │   └── daily_pipeline.py                    ← DAG: daily_data_pipeline
│   ├── code/
│   │   └── orders_dag.py                        ← DAG: orders_data_pipeline (advanced)
│   └── docs/
│       └── architecture.md
│
├── project_9.6_dbt/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── dbt_project/
│   │   ├── dbt_project.yml
│   │   └── models/
│   │       ├── staging/
│   │       │   ├── stg_orders.sql               ← VIEW: cleaned raw orders
│   │       │   └── schema.yml
│   │       └── marts/
│   │           ├── fct_orders.sql               ← INCREMENTAL TABLE: business logic
│   │           └── schema.yml
│   └── docs/
│       └── architecture.md
│
├── project_9.7_data_quality/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── src/
│   │   └── validate_orders.py                   ← 10 GX checks on processed/orders/
│   └── docs/
│       └── architecture.md
│
├── project_9.8_schema_evolution/
│   ├── GUIDE.md
│   ├── README.md
│   ├── steps.md
│   ├── verify.md
│   ├── cost_estimate.md
│   ├── src/
│   │   └── schema_evolution_demo.py             ← v1/v2 Parquet, merge, partition demo
│   └── docs/
│       └── architecture.md
│
└── project_9.9_redshift/
    ├── GUIDE.md
    ├── README.md
    ├── steps.md
    ├── steps_awsconsoleui.md
    ├── verify.md
    ├── cost_estimate.md
    ├── code/
    │   └── redshift_operations.py               ← setup/load/query/report CLI
    └── docs/
        └── architecture.md
```

---

## Stale Artifacts Note

Two zip files exist at the stage root and are intentionally kept as historical snapshots:

- `project_9.1_data_lake.zip` — snapshot of project 9.1 from an earlier build
- `project_9.1_data_lake_old.zip` — older snapshot, pre-Lake Formation additions

Both are outdated relative to the current `project_9.1_data_lake/` folder.
They are not used by any project or script. Do not unzip and run them — use the
live `project_9.1_data_lake/` folder instead.

---

## AWS Certification Alignment

| Project | DEA-C01 (Data Engineer) | SAA-C03 (Solutions Architect) | MLS-C01 (ML Specialty) |
|---------|------------------------|------------------------------|------------------------|
| 9.1 Data Lake | ✅ Core topic | ✅ S3 + Glue design | ✅ Feature storage |
| 9.2 Glue ETL | ✅ Core topic | ✅ Serverless ETL | — |
| 9.3 Kinesis | ✅ Core topic | ✅ Real-time ingestion | ✅ Online feature serving |
| 9.4 Spark EMR | ✅ Core topic | ✅ Big data compute | ✅ Training data prep |
| 9.5 Airflow/MWAA | ✅ Core topic | ✅ Orchestration patterns | — |
| 9.6 dbt | ✅ Transformation patterns | — | — |
| 9.7 Data Quality | ✅ Quality gates | — | ✅ Data validation |
| 9.8 Schema Evolution | ✅ Schema management | — | ✅ Feature versioning |
| 9.9 Redshift | ✅ Core topic | ✅ Warehouse design | ✅ Batch inference storage |

**DEA-C01** covers all 9 projects directly. If preparing for this exam, every
project here maps to exam domains: data ingestion (9.3), transformation (9.2, 9.4, 9.6),
orchestration (9.5), quality (9.7), storage (9.1, 9.8), and analytics (9.9).


You're right. Here's the same answer with full project names included:

---

**`code/` files — NOT needed for console UI learning:**

| Project | File | What it does | Needed? |
|---------|------|-------------|---------|
| **9.1 Data Lake** | `code/upload_sample_data.py` | Programmatically generates and uploads sample CSV to S3 | ❌ No — you manually upload CSV from the console |
| **9.1 Data Lake** | `code/data_lake_setup.py` | Creates S3 folders, Glue databases, Lake Formation setup via Python | ❌ No — you do all this step-by-step in the console |
| **9.1 Data Lake** | `code/run_athena_query.py` | Runs Athena queries via boto3 | ❌ No — you run queries directly in the Athena console |
| **9.1 Data Lake** | `code/convert_to_parquet.py` | Converts CSV to Parquet locally | ❌ No — Glue does this for you via the console |
| **9.5 Airflow** | `code/orders_dag.py` | A more complex duplicate of the DAG | ❌ No — redundant; `dags/daily_pipeline.py` is the actual DAG used |
| **9.9 Redshift** | `code/redshift_operations.py` | Creates tables and COPYs data into Redshift via Python | ❌ No — you do this in the Redshift Query Editor in the console |

---

**`src/` and `dags/` files — NEEDED even for console UI:**

| Project | File | What it does | Needed? |
|---------|------|-------------|---------|
| **9.2 Glue ETL** | `src/etl_job.py` | PySpark script that Glue actually runs — uploaded to S3 | ✅ Yes — Glue requires a script; no script = no job |
| **9.3 Kinesis Streaming** | `src/producer.py` | Sends test events to Kinesis — run locally | ✅ Yes — needed to generate test data for the stream |
| **9.3 Kinesis Streaming** | `src/consumer_lambda.py` | Lambda handler — paste into Lambda in console | ✅ Yes — this is the actual Lambda code |
| **9.4 Spark on EMR** | `src/spark_job.py` | Spark job uploaded to S3, submitted to EMR | ✅ Yes — EMR needs a script to run |
| **9.5 Airflow** | `dags/daily_pipeline.py` | Airflow DAG uploaded to S3, MWAA picks it up automatically | ✅ Yes — MWAA cannot work without a DAG file |
| **9.7 Data Quality** | `src/validate_orders.py` | Data quality checks — deployed as Glue job | ✅ Yes — Glue runs this script |
| **9.8 Schema Evolution** | `src/schema_evolution_demo.py` | Demonstrates schema changes — run locally or as Glue job | ✅ Yes — the demo won't work without it |

---

**Summary:** The `code/` folders in projects **9.1, 9.5, and 9.9** can be ignored entirely for console UI learning. Everything in the `src/` and `dags/` folders across all projects is still needed — those are the actual scripts that AWS services execute, and you can't replace them with console clicks alone.