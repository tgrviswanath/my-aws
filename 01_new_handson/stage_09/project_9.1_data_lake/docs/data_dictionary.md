# Data Dictionary — Project 9.1 Data Lake

This document defines every column in every table in the data lake. In production,
this would be maintained alongside schema changes and versioned in git.

---

## Table: `orders` (raw and processed zones)

| Column | Type | Zone | Description | Example | Notes |
|--------|------|------|-------------|---------|-------|
| order_id | STRING | raw, processed | Unique order identifier | `ORD-00123` | Primary key; format: ORD-NNNNN |
| customer_id | STRING | raw, processed | Customer identifier | `CUST-101` | Foreign key to `customers` table |
| product_name | STRING | raw | Product name as entered | `Widget A` | Use product_id in processed zone |
| product_id | STRING | processed | Normalised product identifier | `PROD-001` | Foreign key to `products` table |
| amount | DOUBLE | raw | Order total in USD | `29.99` | Raw field — may include tax |
| total_amount | DOUBLE | processed | Order subtotal, tax excluded | `27.99` | Cleaned from `amount` |
| unit_price | DOUBLE | processed | Price per unit | `29.99` | From product catalog at order time |
| quantity | INT | processed | Number of units | `1` | Derived from amount / unit_price |
| order_date | STRING | raw | Order date as received | `2024-01-15` | ISO format YYYY-MM-DD |
| order_date | DATE | processed | Parsed order date | `2024-01-15` | Cast from raw string |
| status | STRING | raw, processed | Order status | `completed` | Enum: pending, completed, cancelled |
| region | STRING | processed | Fulfilment region | `US-EAST` | Derived from customer address |
| year | STRING | all | Partition key — year | `2024` | Extracted from order_date |
| month | STRING | all | Partition key — month | `01` | Zero-padded (01–12) |
| day | STRING | raw | Partition key — day | `15` | Zero-padded (01–31) |

### Status Values
| Value | Meaning |
|-------|---------|
| `pending` | Order placed, not yet shipped |
| `completed` | Order delivered successfully |
| `cancelled` | Order cancelled before delivery |

---

## Table: `customers` (raw and processed zones)

| Column | Type | Zone | Description | Example |
|--------|------|------|-------------|---------|
| customer_id | STRING | raw, processed | Unique customer identifier | `CUST-101` |
| name | STRING | raw | Full name as entered | `Alice Smith` |
| first_name | STRING | processed | Parsed first name | `Alice` |
| last_name | STRING | processed | Parsed last name | `Smith` |
| email | STRING | raw, processed | Email address | `alice@example.com` |
| country | STRING | raw, processed | 2-letter ISO country code | `US` |
| signup_date | STRING/DATE | raw/processed | Customer registration date | `2023-06-01` |
| is_active | BOOLEAN | processed | Whether customer is active | `true` |

---

## Table: `products` (raw and processed zones)

| Column | Type | Zone | Description | Example |
|--------|------|------|-------------|---------|
| product_id | STRING | raw, processed | Unique product identifier | `PROD-001` |
| product_name | STRING | raw, processed | Display name | `Widget A` |
| category | STRING | raw, processed | Product category | `Electronics` |
| unit_price | DOUBLE | raw, processed | Current list price in USD | `29.99` |
| in_stock | BOOLEAN | raw, processed | Inventory availability | `true` |
| created_date | STRING/DATE | raw/processed | Date product was added | `2023-01-01` |

---

## Table: `daily_revenue` (curated zone only)

This is an aggregated table created by a Glue ETL job from the processed orders.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| order_date | DATE | The day of orders | `2024-01-15` |
| total_orders | INT | Count of orders placed | `45` |
| completed_orders | INT | Count of completed orders | `38` |
| total_revenue | DOUBLE | Sum of completed order amounts | `1523.45` |
| avg_order_value | DOUBLE | Average order amount | `40.09` |
| top_product | STRING | Best-selling product of the day | `Widget B` |
| year | STRING | Partition key | `2024` |
| month | STRING | Partition key | `01` |

---

## Partition Strategy

All tables in processed/ and curated/ zones are partitioned using Hive-style paths:

```
processed/orders/year=2024/month=01/day=15/orders.parquet
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^
                 Partition columns
```

**Why partitioning matters for Athena cost:**

| Query | Partitions scanned | Data scanned | Athena cost |
|-------|--------------------|-------------|-------------|
| `SELECT * FROM orders` | ALL | 100% | $1.00 (1 TB table) |
| `WHERE year='2024'` | 1 year | ~25% | $0.25 |
| `WHERE year='2024' AND month='01'` | 1 month | ~2% | $0.02 |
| `WHERE year='2024' AND month='01' AND day='15'` | 1 day | ~0.07% | $0.0007 |

**Rule of thumb:** Always add partition filters in your WHERE clause.

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| S3 bucket | `{project}-data-lake-{account_id}` | `handson-data-lake-123456789012` |
| S3 zone prefix | lowercase, no hyphens | `raw/`, `processed/` |
| S3 partition | `{key}={value}` (Hive-style) | `year=2024/month=01/day=15` |
| Glue database | `{project}_{zone}` or `dl_{zone}` | `dl_raw`, `dl_processed` |
| Glue table | lowercase, underscores | `orders`, `daily_revenue` |
| IAM role | `{project}-glue-role` | `handson-glue-role` |
| Glue crawler | `{project}-{zone}-crawler` | `handson-raw-crawler` |
| Athena workgroup | `{project}-data-lake` | `handson-data-lake` |

---

## Zone Data Quality Rules

| Zone | Rule | Enforced By |
|------|------|------------|
| raw/ | Never delete or modify | S3 bucket policy + versioning |
| raw/ | Files arrive as-is from source | Ingestion pipeline |
| processed/ | All columns typed (no string-everything) | Glue ETL / DQ checks |
| processed/ | Null rate < 5% for required fields | Glue DataBrew / custom checks |
| processed/ | Parquet format with Snappy compression | Conversion script |
| curated/ | Business definitions applied (e.g., revenue excludes cancellations) | ETL logic |
| curated/ | Aggregated — no row-level PII | Data governance policy |
