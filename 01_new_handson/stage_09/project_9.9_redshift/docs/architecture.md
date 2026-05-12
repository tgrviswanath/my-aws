# Architecture — Project 9.9 Redshift Data Warehouse

## Data Warehouse Architecture

```
S3 processed/ (Parquet)
    │
    │ COPY command (bulk load — parallel, fast)
    ▼
Redshift Serverless
    ├── Namespace: handson-namespace
    │   └── Database: analytics
    │         ├── fct_orders (fact table)
    │         ├── dim_customers (dimension)
    │         └── orders_daily_summary (aggregate)
    │
    └── Workgroup: handson-workgroup
          └── 8 RPU base capacity (auto-scales)
    │
    ▼
BI Tools (QuickSight, Tableau, Power BI)
    └── Connect via JDBC/ODBC to Redshift endpoint
```

## Columnar Storage Advantage

```
Row-based (MySQL, PostgreSQL):
  Row 1: [ORD-001, CUST-101, Widget A, 29.99, 2024-01-15]
  Row 2: [ORD-002, CUST-102, Widget B, 49.99, 2024-01-15]

  Query: SELECT SUM(amount) FROM orders
  → Must read ALL columns for ALL rows
  → Slow for analytics

Columnar (Redshift, Parquet):
  amount column: [29.99, 49.99, 19.99, ...]
  
  Query: SELECT SUM(amount) FROM orders
  → Reads ONLY the amount column
  → 10-100x faster for analytics
  → Better compression (similar values together)
```

## Distribution and Sort Keys

```
DISTKEY (customer_id):
  Rows with same customer_id go to same node
  Benefit: JOINs on customer_id don't require data movement

SORTKEY (order_date):
  Rows sorted by order_date on disk
  Benefit: range queries (WHERE order_date BETWEEN ...) skip blocks

Example:
  SELECT * FROM fct_orders
  WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'
  → Redshift skips all blocks outside Jan 2024 (zone maps)
  → Much faster than full table scan
```

## Redshift Spectrum

```
Redshift cluster
    │
    │ External schema pointing to Glue catalog
    ▼
Redshift Spectrum
    │
    │ Queries S3 data directly (no COPY needed)
    ▼
S3 Parquet files

Use case: query historical data in S3 without loading it
Cost: $5 per TB scanned (same as Athena)
```
