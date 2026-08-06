# Architecture — Project 9.6 dbt Transformation Pipeline

## Resources

| Resource | Name | Notes |
|----------|------|-------|
| dbt Core | local tool | Free, runs on your machine |
| Athena Workgroup | `handson-dbt` | 1 GB scan limit per query |
| S3 Staging Bucket | `handson-dbt-staging-ACCOUNT` | Query results, 7-day expiry |
| Glue Database (source) | `handson_data_lake` | Created by Project 9.1 |
| Glue Table (source) | `orders` | Crawled from S3 raw/orders/ |
| Glue Table (dbt output) | `stg_orders` | Created by dbt — VIEW |
| Glue Table (dbt output) | `fct_orders` | Created by dbt — TABLE |

---

## Model Lineage (Full Pipeline)

```
External Source (outside dbt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
S3: s3://handson-data-lake-ACCOUNT/raw/orders/*.csv
    │   (raw CSV from upstream system)
    │
    ▼ [Glue Crawler — Project 9.1]
Glue Table: handson_data_lake.orders
    │   (schema: order_id, customer_id, product,
    │    status, amount, quantity, order_date — all STRING)

dbt Models (this project)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    │  {{ source('raw', 'orders') }}
    ▼
models/staging/stg_orders.sql        [VIEW]
    │  Clean: cast types, normalize case, filter nulls
    │  Output schema:
    │    order_id        STRING
    │    customer_id     STRING
    │    product_name    STRING   ← upper(trim(product))
    │    order_status    STRING   ← lower(trim(coalesce(status,'unknown')))
    │    order_amount_usd DOUBLE  ← cast(amount as double)
    │    quantity        INTEGER  ← cast(quantity as integer)
    │    order_date      DATE     ← cast(order_date as date)
    │    order_year      INTEGER  ← year(order_date)
    │    order_month     INTEGER  ← month(order_date)
    │    _loaded_at      TIMESTAMP
    │
    │  {{ ref('stg_orders') }}
    ▼
models/marts/fct_orders.sql          [INCREMENTAL TABLE, merge on order_id]
    │  Business logic + metrics
    │  Output schema:
    │    order_id         STRING
    │    customer_id      STRING
    │    product_name     STRING
    │    order_status     STRING
    │    order_date       DATE
    │    order_year       INTEGER
    │    order_month      INTEGER
    │    order_amount_usd DOUBLE
    │    quantity         INTEGER
    │    unit_price_usd   DOUBLE   ← amount / nullif(quantity, 0)
    │    order_tier       STRING   ← CASE WHEN amount >= 100 THEN 'high_value' ...
    │    _dbt_updated_at  TIMESTAMP
    │
    │  Tests (schema.yml):
    │    order_id:          not_null + unique
    │    customer_id:       not_null
    │    order_amount_usd:  not_null + expression >= 0
    │    order_status:      accepted_values [pending,processing,shipped,delivered,cancelled,unknown]
    │    order_tier:        accepted_values [high_value,medium_value,low_value]
    ▼
Athena query engine
    → BI dashboards
    → Redshift Spectrum
    → Downstream dbt models (if any)
```

---

## Materialization Types

```
view (stg_orders):
  CREATE OR REPLACE VIEW stg_orders AS
    SELECT <cleaned columns> FROM handson_data_lake.orders
    WHERE order_id IS NOT NULL AND amount > 0

  On each query: re-runs the SQL live (no data stored)
  Cost: $0 storage | Athena cost on each query

incremental (fct_orders):
  First run:
    CREATE TABLE fct_orders WITH (format='PARQUET') AS
    SELECT <business logic columns> FROM stg_orders

  Subsequent runs:
    INSERT INTO fct_orders
    SELECT <business logic columns> FROM stg_orders
    WHERE order_date > (SELECT MAX(order_date) FROM fct_orders)
    -- Only new rows

  merge strategy:
    If order_id already in fct_orders → UPDATE existing row
    If order_id is new              → INSERT new row
    No duplicates regardless of re-runs

  Cost: S3 Parquet storage + Athena only on new rows
```

---

## Incremental Run Logic

```
Timeline: dbt run at Day 1, Day 2, Day 3

Day 1 (first run):
  is_incremental() = False
  WHERE clause: not added
  Reads: ALL rows from stg_orders
  fct_orders: 1,000 rows created

Day 2 (incremental run):
  is_incremental() = True
  WHERE clause added:
    WHERE order_date > (SELECT MAX(order_date) FROM fct_orders)
    -- MAX(order_date) = 2024-01-15 (from Day 1)
    -- So: only orders with order_date > 2024-01-15
  Reads: 50 new rows (Jan 16 orders only)
  fct_orders: merges 50 rows → 1,050 rows total

Day 3 (full refresh):
  dbt run --full-refresh
  is_incremental() FORCED = False
  Drops table + recreates from scratch
  Use when: schema changed, or need to reprocess all historical data
```

---

## dbt Test Execution

```
Each schema.yml test → Athena SQL query

not_null test on order_id:
  SELECT COUNT(*) FROM (
    SELECT order_id
    FROM handson_data_lake.fct_orders
    WHERE order_id IS NULL
  ) dbt_internal_test
  → Fails if count > 0

unique test on order_id:
  SELECT COUNT(*) FROM (
    SELECT order_id, COUNT(*) as n
    FROM handson_data_lake.fct_orders
    GROUP BY order_id
    HAVING COUNT(*) > 1
  ) dbt_internal_test
  → Fails if any order_id appears more than once

accepted_values on order_tier:
  SELECT COUNT(*) FROM (
    SELECT order_tier
    FROM handson_data_lake.fct_orders
    WHERE order_tier NOT IN ('high_value','medium_value','low_value')
  ) dbt_internal_test
  → Fails if any unexpected tier value found
```

---

## dbt in the Data Stack

```
Project 9.1: Data Lake    → S3 + Glue (raw data source for dbt)
Project 9.2: Glue ETL     → loads processed/ zone
Project 9.3: Kinesis      → real-time Lambda aggregates
Project 9.4: Spark/EMR    → heavy transformations
Project 9.5: Airflow      → orchestrates dbt run as pipeline task
Project 9.6: dbt          → SQL transforms + tests + docs (this project)

Airflow calls dbt:
  BashOperator: "dbt run --select orders+ --target prod"
  dbt creates: stg_orders VIEW + fct_orders TABLE in Athena
  Airflow then: runs quality checks, sends SNS notification
```

---

## profiles.yml Structure

```yaml
handson:                      # profile name — must match dbt_project.yml
  target: dev                 # default target
  outputs:
    dev:
      type: athena            # adapter (installed as dbt-athena-community)
      s3_staging_dir: s3://...  # WHERE Athena writes result files
      region_name: us-east-1
      database: awsdatacatalog  # always this for standard Athena
      schema: handson_data_lake # Glue database where dbt creates tables
      work_group: handson-dbt   # Athena workgroup for cost/access control
      threads: 4                # parallel model execution
```

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
