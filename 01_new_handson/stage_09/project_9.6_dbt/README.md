# Project 9.6 — dbt Transformation Pipeline

## What This Does
Uses dbt (data build tool) to transform raw data in Athena/Redshift into clean, tested, documented analytical models. dbt is the standard tool for the "T" in ELT.

## dbt Project Structure
```
dbt_project/
├── models/
│   ├── staging/          ← clean raw data (1:1 with source tables)
│   │   ├── stg_orders.sql
│   │   └── stg_customers.sql
│   ├── intermediate/     ← business logic
│   │   └── int_order_items.sql
│   └── marts/            ← final analytical tables
│       ├── fct_orders.sql
│       └── dim_customers.sql
├── tests/                ← data quality tests
├── macros/               ← reusable SQL snippets
└── dbt_project.yml
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| Model | A SQL SELECT statement that becomes a table/view |
| Materialization | table, view, incremental, ephemeral |
| Test | Assert data quality (not null, unique, accepted values) |
| Source | Reference to raw data tables |
| Ref | Reference to another dbt model (builds DAG) |
| Macro | Reusable Jinja SQL function |

## How to Run
```bash
pip install dbt-athena-community
cd dbt_project
dbt run          # build all models
dbt test         # run all tests
dbt docs generate && dbt docs serve  # view documentation
```

## Lessons Learned
- dbt is SQL-first — no Python needed for transformations
- Incremental models: only process new/changed rows — much faster than full refresh
- `ref()` function builds the dependency DAG automatically
- dbt tests: `not_null`, `unique`, `accepted_values`, `relationships` — run after every build
- dbt docs: auto-generated documentation with lineage graph — share with stakeholders
