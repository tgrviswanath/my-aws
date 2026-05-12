# Architecture — Project 9.1 Data Lake Architecture

## S3 Zone Strategy

```
S3 Bucket: handson-data-lake-ACCOUNTID
    ├── raw/           ← original data, never modified
    │   └── orders/year=2024/month=01/day=15/orders.csv
    ├── processed/     ← cleaned, Parquet format, partitioned
    │   └── orders/year=2024/month=01/orders.parquet
    ├── curated/       ← business-ready aggregates
    │   └── orders_daily/year=2024/month=01/daily.parquet
    ├── scripts/       ← Glue ETL scripts
    └── temp/          ← temporary files (expire after 7 days)
```

## Query Flow

```
Data arrives in raw/
    │
    │ Glue Crawler (daily at 6am)
    ▼
Glue Data Catalog
    └── Database: handson_data_lake
          └── Table: orders (schema auto-discovered)
                └── Partitions: year=2024/month=01/...
    │
    │ Athena SQL query
    ▼
SELECT * FROM orders WHERE year=2024 AND month=01
    │
    │ Partition pruning: only reads Jan 2024 data
    ▼
Results in seconds (not minutes)
```

## Lake Formation Access Control

```
Lake Formation (optional — adds column/row-level security)
    ├── Grant: data-engineers → full access to processed/
    ├── Grant: analysts → read-only access to curated/
    └── Grant: ml-team → read access to processed/ (no PII columns)
```
