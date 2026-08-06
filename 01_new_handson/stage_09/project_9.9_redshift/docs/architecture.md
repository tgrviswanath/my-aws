# Architecture — Project 9.9 Redshift Data Warehouse

## Resources

| Resource | Name | Notes |
|----------|------|-------|
| Serverless Namespace | `handson-namespace` | DB: analytics, Admin: admin |
| Serverless Workgroup | `handson-workgroup` | 8 RPU base, VPC private |
| IAM Role | `handson-redshift-role` | S3ReadOnly + GlueConsole |
| Security Group | `handson-redshift-sg` | Inbound port 5439 from VPC |
| Table (fact) | `analytics.fact_orders` | DISTKEY(customer_id) SORTKEY(order_date,region) |
| Table (dim) | `analytics.dim_date` | DISTSTYLE ALL SORTKEY(full_date) |

---

## Full Pipeline

```
S3: processed/orders/*.parquet
    │  COPY command — parallel bulk load, IAM role auth
    │  FORMAT AS PARQUET, COMPUPDATE OFF, STATUPDATE ON
    ▼
Redshift Serverless: handson-workgroup
    │
    ├── analytics.fact_orders
    │     DISTKEY(customer_id): customer JOINs = no network transfer
    │     SORTKEY(order_date, region): date range queries skip blocks
    │     Encoding: zstd (strings) + az64 (numbers/dates)
    │
    └── analytics.dim_date
          DISTSTYLE ALL: replicated to every node
          SORTKEY(full_date): fast date JOINs
          ~4018 rows: 2020-01-01 to 2030-12-31
    │
    ├── Python redshift_operations.py (psycopg2)
    │     setup → load → query → report
    │
    ├── Redshift Data API (no VPN needed)
    │     aws redshift-data execute-statement ...
    │
    └── BI Tools via JDBC (port 5439)
          Tableau, Power BI, Amazon QuickSight
```

---

## Columnar Storage Advantage

```
Row storage (MySQL, PostgreSQL):
  Full row read for every query — wastes I/O on unneeded columns
  SELECT SUM(amount) → reads ALL 9 columns for ALL rows

Columnar storage (Redshift):
  Each column stored contiguously on disk
  SELECT SUM(total_amount) → reads ONLY total_amount bytes
  + Better compression: similar values are adjacent
  + 10–100x faster for analytics
  + Lower Redshift RPU consumption (less I/O = faster completion)
```

---

## Distribution Strategies

```
DISTKEY (customer_id) — used for fact_orders:
  Rows hashed by customer_id → routed to specific compute node
  All orders for CUST-007 → always on Node 2
  JOIN ON customer_id: data is already co-located → no network transfer

DISTSTYLE ALL — used for dim_date:
  Entire table replicated to EVERY compute node
  Any JOIN ON order_date = full_date: every node has local copy
  Use for: tables < 1M rows that are referenced in every query
  Cost: extra storage (table replicated N times for N nodes)

DISTSTYLE EVEN:
  Rows distributed round-robin
  Use when: no clear join column, or infrequently joined
  Best distribution for: staging tables, rarely joined facts
```

---

## SORTKEY and Zone Maps

```
SORTKEY (order_date, region):
  Rows physically sorted on disk: 2024-01-01 ... 2024-01-31 ... 2024-02-01 ...

  Redshift zone maps (metadata per 1MB block):
    Block 1: order_date = 2024-01-01 to 2024-01-05
    Block 2: order_date = 2024-01-06 to 2024-01-10
    ...

  Query: WHERE order_date BETWEEN '2024-01-10' AND '2024-01-15'
    → Redshift checks zone maps
    → Skips Block 1 (max date 2024-01-05 < 2024-01-10)
    → Reads only Block 2, Block 3 → much less I/O

Compound SORTKEY (order_date, region):
  Sort by order_date first, then region within same date
  Benefits queries with: WHERE order_date = X AND region = 'US'
  Less benefit for: WHERE region = 'US' (no date filter)
```

---

## COPY Command Internals

```
COPY analytics.fact_orders
FROM 's3://bucket/processed/orders/'
IAM_ROLE 'arn:...'
FORMAT AS PARQUET
COMPUPDATE OFF
STATUPDATE ON;

What happens:
  1. Redshift leader node lists all files in S3 prefix
  2. Files distributed across all compute nodes
  3. Each node reads its assigned files in parallel
  4. Parquet schema auto-mapped to table columns by name
  5. Data loaded into columnar storage with zstd/az64 encoding
  6. STATUPDATE: table statistics written to catalog
  
Speed: proportional to number of nodes × S3 file count
  8 RPU → ~2 compute nodes → 2x parallel read
  For 1 GB Parquet: typically 30–60 seconds
  For 1 TB Parquet: typically 5–15 minutes
```

---

## Redshift Spectrum

```
Without Spectrum:
  Historical data in S3 → must COPY into Redshift to query
  Problem: 5 years of history × 10 GB/day = 18 TB to load = expensive

With Spectrum:
  CREATE EXTERNAL SCHEMA spectrum FROM DATA CATALOG
  DATABASE 'handson_data_lake' IAM_ROLE 'arn:...'
  
  SELECT * FROM spectrum.orders WHERE year = 2020 LIMIT 100;
  → Reads S3 Parquet directly (no load needed)
  → Cost: $5/TB scanned (same as Athena)

Hybrid query (Redshift + S3):
  SELECT r.customer_id, r.lifetime_value, s.product
  FROM analytics.fact_orders_summary r     ← loaded in Redshift (fast)
  JOIN spectrum.orders_historical s ON ... ← reads S3 directly (no load)

Use case: recent 90 days in Redshift, all history in S3 via Spectrum
```

---

## Post-Load Operations

```
VACUUM SORT ONLY analytics.fact_orders;
  What: re-sorts rows by SORTKEY after bulk load
  Why:  COPY inserts in S3 file order, not SORTKEY order
  Cost: runs on cluster compute, uses RPU
  When: after every COPY that adds > 5% new rows

ANALYZE analytics.fact_orders;
  What: samples columns, updates statistics in system catalog
  Why:  query planner uses statistics to choose optimal join/sort strategy
  Without: planner may choose nested loop join when hash join is 100x faster
  When: after every COPY, and weekly on active tables

VACUUM DELETE ONLY analytics.fact_orders;
  What: reclaims storage from deleted/updated rows
  Why:  Redshift is append-only; deletes mark rows as deleted but don't free space
  When: after large DELETE or UPDATE operations
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
