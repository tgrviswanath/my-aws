# Architecture — Project 9.6 dbt Transformation Pipeline

## dbt Model Lineage

```
Source: raw.orders (S3 → Glue Catalog)
    │
    ▼
staging/stg_orders.sql  (view — clean raw data)
    │
    ▼
marts/fct_orders.sql    (incremental table — business logic)
    │
    ├── Tests run after each model:
    │   ├── not_null: order_id, customer_id, amount
    │   ├── unique: order_id
    │   └── accepted_values: order_status, order_tier
    │
    ▼
Athena table: handson_data_lake.fct_orders
    │
    ▼
BI tools / Grafana / Redshift Spectrum
```

## Materialization Types

```
view (default):
  CREATE OR REPLACE VIEW fct_orders AS SELECT ...
  No storage cost — query runs every time
  Use for: staging models, simple transformations

table:
  CREATE TABLE fct_orders AS SELECT ...
  Stored in S3 as Parquet
  Use for: frequently queried models

incremental:
  INSERT INTO fct_orders SELECT ... WHERE order_date > last_run
  Only processes new/changed rows
  Use for: large fact tables, append-only data

ephemeral:
  Not materialized — inlined as CTE
  Use for: intermediate calculations
```

## dbt Test Types

```
Generic tests (built-in):
  - not_null
  - unique
  - accepted_values
  - relationships (foreign key check)

Custom tests (SQL files in tests/):
  SELECT order_id FROM fct_orders
  WHERE amount < 0
  -- Fails if any negative amounts found

dbt-utils tests:
  - expression_is_true
  - recency (data freshness)
  - equal_rowcount
```
