# Architecture — Project 9.8 Schema Evolution & Partitioning

## Resources

| Resource | Name | Notes |
|----------|------|-------|
| Glue Schema Registry | `handson-registry` | AVRO format |
| Glue Schema | `orders-schema` | v1 + v2, BACKWARD compatibility |
| Glue Database | `handson_schema_demo` | Demo database |
| Glue Table | `orders_partitioned` | Partition projection enabled |
| S3 Path (demo) | `schema-demo/year=2024/month=01/` | v1 + v2 Parquet files |
| S3 Path (prod) | `processed/orders/year=YYYY/month=MM/day=DD/` | Production partitions |

---

## Schema Evolution Rules

```
BACKWARD COMPATIBLE (safe — old consumers keep working):
  ✅ Add new NULLABLE field with default:
     {"name":"product","type":["null","string"],"default":null}
  ✅ Remove field that had a default value

BREAKING CHANGES (never do these in production):
  ❌ Rename field:          order_id → orderId
     Old consumers look for "order_id", find nothing, crash
  ❌ Change type:           amount: double → string
     Old consumers try math on a string, crash
  ❌ Add REQUIRED field:    {"name":"product","type":"string"}  ← no default!
     Old producers don't set this field, schema validation fails
  ❌ Remove required field: consumers that expect it get error

SAFE SCHEMA EVOLUTION EXAMPLE (v1 → v2 → v3):
  v1: {order_id, customer_id, amount, order_date}
  v2: {order_id, customer_id, amount, order_date, product=null, discount_pct=null}
  v3: {order_id, customer_id, amount, order_date, product, discount_pct, region=null}

If you MUST rename a field:
  v2: Add new_name alongside old_name (both populated)
  v3: Remove old_name once all consumers use new_name
  Takes: ~4 deployment cycles / 4 weeks
```

---

## Parquet Schema Merging

```
File 1 (v1):   [order_id, customer_id, amount, order_date]
File 2 (v2):   [order_id, customer_id, amount, order_date, product, discount_pct]

PyArrow merges schemas automatically (schema=None in ParquetDataset):
  → Union schema: [order_id, customer_id, amount, order_date, product, discount_pct]
  → File 1 rows: product=NaN, discount_pct=NaN  (missing columns → null)
  → File 2 rows: all 6 columns populated

Why this works:
  Parquet stores column metadata (name + type) in each file footer
  Reader discovers column set per file and fills gaps with null
  This is fundamentally different from CSV (no schema metadata → crash)
```

---

## Partition Strategy

```
RULE: Partition by columns you filter on most often

GOOD partitioning:
  Date-based:    year=YYYY/month=MM/day=DD
  Region:        country=US/state=CA/
  Both:          country=US/year=2024/month=01/

BAD partitioning:
  user_id:       user_id=CUST-000001/ ... user_id=CUST-999999/
    → 1M partitions → S3 LIST timeout → Glue Crawler takes hours
  
  event_type:    event_type=click/ event_type=purchase/
    → Only 3-5 values → very uneven partitions → no gain

QUERY PATTERN MATCHING:
  Common query: WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'
  → Partition by: year/month  (not day — adds unnecessary depth)

  Common query: WHERE country='US' AND year=2024 AND month=1
  → Partition by: country/year/month
```

---

## Partition Projection Configuration

```
WITHOUT partition projection (manual workflow):
  1. Glue ETL writes new partition to S3:
     s3://bucket/orders/year=2024/month=03/day=01/
  2. Must manually run: MSCK REPAIR TABLE orders;
     (or: aws glue get-partitions + aws glue batch-create-partition)
  3. Only now can Athena query the new partition
  Problem: engineers forget step 2 → analysts see incomplete data

WITH partition projection (automated):
  1. Glue ETL writes new partition to S3
  2. Done. Athena automatically queries it.
  Problem: none. Add partitions as fast as you can write S3 objects.

Configuration (from terraform/main.tf):
  "projection.enabled"        = "true"
  "projection.year.type"      = "integer"
  "projection.year.range"     = "2023,2030"
  "projection.month.type"     = "integer"
  "projection.month.range"    = "1,12"
  "projection.month.digits"   = "2"          ← zero-pad to 2 digits
  "projection.day.type"       = "integer"
  "projection.day.range"      = "1,31"
  "projection.day.digits"     = "2"
  "storage.location.template" = "s3://BUCKET/orders/year=${year}/month=${month}/day=${day}"
```

---

## Small Files Problem

```
Root cause:
  Kinesis Firehose default: flush every 60s or 128 MB (whichever first)
  At low volume: flush every 60s with 10 KB data
  24h × 60/hr = 1,440 tiny files per day
  After 1 year: 1,440 × 365 = 525,600 files

Query impact:
  Each Athena query must open every matching file
  525,600 files × 1 ms overhead = 525 seconds just opening files!
  Even a COUNT(*) takes minutes

Solution — compaction:
  Periodic Spark/Glue job reads all small files and writes one large file
  Target: 128 MB – 1 GB per Parquet file

  1,440 × 10 KB = 14.4 MB/day → 1 file of 14.4 MB
  525,600 × 10 KB/yr = 5.2 GB/yr → monthly compaction → 12 files of 433 MB

Compaction code (Spark):
  df = spark.read.parquet("s3://bucket/orders/year=2024/month=01/")
  df.coalesce(1).write.mode("overwrite").parquet("s3://bucket/orders-compacted/year=2024/month=01/")
```

---

## Glue Schema Registry — Compatibility Modes

| Mode | Can Add Fields | Can Remove | Can Change Type | Use When |
|------|---------------|-----------|----------------|---------|
| **BACKWARD** | ✅ nullable only | ✅ if has default | ❌ | Most streaming systems |
| FORWARD | ❌ | ❌ | ❌ | Very strict |
| FULL | ✅ nullable | ✅ both ways | ❌ | Maximum safety |
| NONE | anything | anything | anything | Development only |

> **Use BACKWARD** for production data streams (Kinesis, Kafka, MSK).
> Old consumers keep reading new data without code changes.

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
