# Architecture — Project 9.1 Data Lake Architecture

## Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA LAKE ON AWS                                  │
│                                                                          │
│  ┌─────────────┐   ┌─────────────────────────────────────────────────┐ │
│  │   DATA      │   │              AMAZON S3                           │ │
│  │  SOURCES    │──▶│                                                  │ │
│  │             │   │  raw/          processed/   curated/   archive/  │ │
│  │ • App DB    │   │  (CSV/JSON)    (Parquet)    (Parquet)  (Glacier) │ │
│  │ • Files     │   │  as-is         typed        aggregated old data  │ │
│  │ • APIs      │   │                                                  │ │
│  │ • Streams   │   └──────────────────┬──────────────────────────────┘ │
│  └─────────────┘                      │                                 │
│                                       │ Glue Crawler                    │
│                                       │ (auto-discovers schema)         │
│                                       ▼                                 │
│                          ┌────────────────────────┐                    │
│                          │   AWS GLUE DATA         │                    │
│                          │      CATALOG            │                    │
│                          │  ┌──────────────────┐  │                    │
│                          │  │ Database: raw_db  │  │                    │
│                          │  │  Table: orders   │  │                    │
│                          │  │  Table: customers│  │                    │
│                          │  └──────────────────┘  │                    │
│                          └────────────┬───────────┘                    │
│                    ┌─────────────────┬┴─────────────────┐              │
│                    │                 │                   │              │
│           ┌────────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐    │
│           │ AMAZON ATHENA   │ │    LAKE      │ │  GLUE ETL JOBS  │    │
│           │                 │ │  FORMATION   │ │                 │    │
│           │ Serverless SQL  │ │              │ │ raw→processed   │    │
│           │ $5/TB scanned   │ │ Column-level │ │ CSV→Parquet     │    │
│           │ Partition prune │ │ Row-level    │ │ Data quality    │    │
│           │                 │ │ access ctrl  │ │                 │    │
│           └─────────────────┘ └─────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## S3 Zone Strategy

```
s3://handson-data-lake-123456789012/
│
├── raw/                               ← BRONZE LAYER
│   └── orders/
│       └── year=2024/
│           └── month=01/
│               └── day=15/
│                   └── orders.csv     ← Original file, never touched
│
├── processed/                         ← SILVER LAYER
│   └── orders/
│       └── year=2024/
│           └── month=01/
│               └── orders.parquet     ← Typed, compressed, monthly partition
│
├── curated/                           ← GOLD LAYER
│   └── daily_revenue/
│       └── year=2024/
│           └── month=01/
│               └── daily_revenue.parquet   ← Pre-aggregated for dashboards
│
├── archive/                           ← COLD STORAGE
│   └── orders_2022/                   ← Moved from raw after processing
│       └── ...                        ← Glacier: $0.004/GB vs $0.023/GB
│
└── athena-results/                    ← Athena writes query results here
    └── 2024/01/15/
        └── queryid.csv
```

### Zone Rules

| Zone | Modify? | Delete? | Format | Who writes |
|------|---------|---------|--------|-----------|
| raw/ | ❌ NEVER | ❌ NEVER | Any | Ingestion pipeline |
| processed/ | ✅ Overwrite partition | ⚠️ With care | Parquet | Glue ETL jobs |
| curated/ | ✅ Daily refresh | ✅ Old partitions | Parquet | Glue ETL jobs |
| archive/ | ❌ | ❌ | Any | S3 lifecycle policy |

---

## Query Flow with Partition Pruning

```
User runs:
  SELECT SUM(amount) FROM orders WHERE year='2024' AND month='01'

Athena execution:
  1. Read table definition from Glue Data Catalog
     └── Discovers: partition keys are year, month, day
     └── Discovers: S3 location is s3://bucket/raw/orders/

  2. Apply partition filter BEFORE reading any data
     └── Scans folder: raw/orders/year=2024/month=01/ ONLY
     └── Skips:        raw/orders/year=2023/ ← entire year skipped
     └── Skips:        raw/orders/year=2024/month=02/ through month=12/

  3. Read only the matching partition
     └── Data scanned: ~5 MB (one month)
     └── Without filter: ~60 MB (full year = 12x more expensive)

  4. Return result in ~2 seconds
```

**Cost impact:**
- Query without partition filter: scans 60 MB → costs $0.0003
- Query WITH partition filter: scans 5 MB → costs $0.000025
- Savings: 12x cheaper just by adding WHERE clause

---

## Glue Data Catalog Structure

```
AWS Glue Data Catalog (regional)
│
├── Database: raw_db
│   ├── Table: orders
│   │   ├── Column: order_id    STRING
│   │   ├── Column: customer_id STRING
│   │   ├── Column: amount      DOUBLE
│   │   ├── Column: order_date  STRING
│   │   ├── Partition: year     STRING
│   │   ├── Partition: month    STRING
│   │   ├── Partition: day      STRING
│   │   └── Location: s3://bucket/raw/orders/
│   │
│   └── Table: customers
│       ├── Column: customer_id STRING
│       ├── ...
│       └── Location: s3://bucket/raw/customers/
│
├── Database: dl_processed
│   └── Table: orders   (Parquet schema — typed columns)
│
└── Database: dl_curated
    └── Table: daily_revenue  (aggregated)
```

---

## Lake Formation Access Control

```
Lake Formation Permission Model

S3 Bucket (registered as data lake location)
│
└── Glue Data Catalog
    │
    ├── Database: raw_db
    │   ├── Grant: data-engineers → ALL (SELECT, INSERT, DROP, ALTER)
    │   └── Grant: analysts       → SELECT, DESCRIBE only
    │
    ├── Database: dl_processed
    │   ├── Grant: data-engineers → ALL
    │   ├── Grant: analysts       → SELECT, DESCRIBE
    │   └── Grant: ml-team        → SELECT (columns: exclude email, phone)
    │
    └── Database: dl_curated
        ├── Grant: analysts   → SELECT (all columns)
        └── Grant: dashboards → SELECT (aggregated only — no PII)
```

**Column-level security example:**
ML team can query `orders` but cannot see `customer_email` (PII):
```sql
-- ML team sees this:
SELECT order_id, product_id, amount, region FROM orders LIMIT 10;

-- ML team CANNOT run:
SELECT customer_id, email FROM customers;  -- AccessDenied
```

---

## IAM Role Relationships

```
Your IAM User/Role
    │ assumes
    ▼
handson-glue-role
    │ can access
    ├── S3: s3://handson-data-lake-*/*  (read/write)
    ├── Glue Data Catalog: all databases and tables
    ├── CloudWatch Logs: write crawler logs
    └── Lake Formation: register resources

AWS Glue Service
    │ uses
    ▼
handson-glue-role
    │ is trusted by
    └── glue.amazonaws.com  (service principal in trust policy)
```

---

## CSV vs Parquet — Technical Comparison

### Row-based (CSV)
```
Row 1: [order_id=ORD-001][customer_id=CUST-101][product_name=Widget A][amount=29.99][status=completed]
Row 2: [order_id=ORD-002][customer_id=CUST-102][product_name=Widget B][amount=49.99][status=completed]
Row 3: [order_id=ORD-003][customer_id=CUST-101][product_name=Widget C][amount=19.99][status=cancelled]

Query: SELECT SUM(amount) → Must read ALL columns of ALL rows
```

### Columnar (Parquet)
```
Column: order_id    → [ORD-001][ORD-002][ORD-003]... (compressed together)
Column: customer_id → [CUST-101][CUST-102][CUST-101]... (compressed together)
Column: amount      → [29.99][49.99][19.99]... (compressed together)
Column: status      → [completed][completed][cancelled]... (dictionary encoded)

Query: SELECT SUM(amount) → Reads ONLY the amount column
       → 1 column out of 5 = reads 20% of the data
```

**Parquet advantages:**
1. **Column pruning** — only read columns you SELECT
2. **Compression** — repeated values in a column compress 10-100x
3. **Predicate pushdown** — min/max stats skip row groups automatically
4. **Type preservation** — numbers stored as numbers, not strings

---

## Athena Workgroup Configuration

```
Workgroup: handson-data-lake
│
├── Result location: s3://handson-athena-results-xxx/results/
│   └── Results stored here after each query
│
├── Scan limit: 1 GB per query
│   └── Query cancelled if it would scan > 1 GB
│   └── Protects against SELECT * on huge tables
│
└── Encryption: SSE-S3
    └── Query results encrypted at rest
```

---

## S3 Lifecycle Policy Flow

```
Object created in raw/
    │
    │ After 90 days
    ▼
Object transitions to GLACIER
    │ Cost: $0.023/GB → $0.004/GB (83% savings)
    │ Retrieval time: 3-5 hours (Flexible) or 1-5 min (Expedited, more expensive)
    │
    │ Never auto-deleted (raw data kept indefinitely)

Object created in temp/
    │
    │ After 7 days
    ▼
Object permanently deleted
    └── Temp files from ETL jobs don't accumulate
```

---

## Data Lake vs Data Warehouse

| Dimension | Data Lake (this project) | Data Warehouse (Redshift) |
|-----------|--------------------------|--------------------------|
| Schema | Schema-on-read (discover at query time) | Schema-on-write (define before loading) |
| Data types | Any (structured, semi, unstructured) | Structured only |
| Storage | S3 (~$0.023/GB) | Redshift (~$0.25/GB) |
| Query engine | Athena (serverless, pay-per-query) | Redshift (always-on cluster) |
| Best for | Exploration, ML, raw data storage | Regular reports, dashboards |
| Latency | Seconds to minutes | Sub-second |
| Max scale | Unlimited (S3) | Petabytes with RA3 nodes |

**When to use a data lake:** Storing and exploring raw data, ML training data,
event logs, clickstream data, IoT sensor data.

**When to use a data warehouse:** Business dashboards that need sub-second
queries, scheduled reports, highly structured operational data.

**In practice:** Use both — data lake for storage and exploration, warehouse
for production reporting (load curated zone data into Redshift or Snowflake).

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
