# Architecture — Project 9.4 Spark Processing on EMR Serverless

## Resources Deployed

| Resource | Name | Notes |
|----------|------|-------|
| EMR Serverless App | `handson-spark` | emr-6.15.0, SPARK type |
| IAM Role | `handson-emr-serverless-role` | Trust: emr-serverless.amazonaws.com |
| S3 Script Object | `scripts/spark_job.py` | Uploaded from src/spark_job.py |

---

## Full Pipeline Architecture

```
S3: raw/orders/*.csv
    │
    │  start-job-run → entryPoint=s3://BUCKET/scripts/spark_job.py
    │                  entryPointArguments: --input ... --output ...
    ▼
EMR Serverless: handson-spark  (emr-6.15.0)
    │
    │  Docker containers provisioned on AWS-managed fleet
    │
    ├── DRIVER (1 node, 2 vCPU, 4 GB RAM)
    │   - Parses spark_job.py
    │   - Builds DAG (Directed Acyclic Graph of stages)
    │   - Sends tasks to executors
    │   - Collects results, writes output
    │
    └── EXECUTORS (auto-scaled, up to 20 vCPU total)
        - Each reads a partition of the CSV from S3
        - Applies map transformations (dropna, cast, withColumn)
        - Participates in shuffle for groupBy operations
        - Writes Parquet partitions to S3 in parallel
    │
    ├──▶ S3: processed/spark/product_monthly/year=YYYY/month=M/
    │       part-00000-*.snappy.parquet
    │       (partitioned Parquet — product+month revenue aggregates)
    │
    └──▶ S3: processed/spark/customer_clv/
            part-00000-*.snappy.parquet
            (flat Parquet — customer lifetime value)
```

---

## Spark Execution Plan (spark_job.py)

```
Stage 1 — Read + Clean (no shuffle, fully parallel per partition):
  Read CSV → filter nulls → cast types → add year/month → dedup

Stage 2 — Product Monthly Aggregates (requires shuffle):
  groupBy(year, month, product)
    → Hash each row's key → route to executor by hash
    → Each executor aggregates its assigned products
    → count, sum, avg, countDistinct per group

Stage 3 — Customer CLV Aggregates (requires shuffle):
  groupBy(customer_id)
    → Hash customer_id → route to executor
    → Each executor aggregates its assigned customers
    → count, sum, min, max per customer

Stage 4 — Write Output (parallel write, no shuffle):
  product_monthly → partitionBy(year, month) → Parquet
  customer_clv    → flat → Parquet
```

---

## Spark Adaptive Query Execution (AQE)

```python
# Enabled in spark_job.py:
.config("spark.sql.adaptive.enabled", "true")
.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

**What AQE does at runtime:**

| Phase | Without AQE | With AQE |
|-------|------------|---------|
| After groupBy shuffle | 200 partitions (Spark default) | Coalesces to 3–5 based on actual data size |
| Small dataset groupBy | 200 tiny tasks (~1 KB each) | 5 tasks (~40 KB each) |
| Execution time | Slow (200 task scheduling overheads) | Fast (5 tasks) |

---

## Hive-Style Partitioning (Output)

```
df_product_monthly.write.partitionBy("year", "month").parquet(...)

Creates:
  processed/spark/product_monthly/
    year=2024/
      month=1/
        part-00000-abc123.snappy.parquet   ← Jan 2024 data
      month=2/
        part-00000-def456.snappy.parquet   ← Feb 2024 data
      month=3/
        part-00000-ghi789.snappy.parquet   ← Mar 2024 data

Athena query:
  SELECT * FROM product_monthly WHERE year=2024 AND month=1
  → Athena reads ONLY year=2024/month=1/ folder
  → Skips all other partitions
  → 10x less data scanned → 10x cheaper

Without partitioning:
  Athena reads ALL data even for a single-month query
```

---

## EMR Serverless vs EMR on EC2

| Dimension | EMR Serverless | EMR on EC2 |
|-----------|---------------|-----------|
| Cluster management | ❌ None | ✅ Full control |
| Cold start | ~30–60s | ~8–15 min (cluster boot) |
| Idle cost | $0 (auto-stop) | $420/mo (3× m5.xlarge) |
| Cost model | Per vCPU-hr + GB-hr | Per EC2 instance-hr |
| Spot instances | ❌ Not available | ✅ 60–90% savings |
| Custom Spark config | Limited | Full YARN tuning |
| Best for | Infrequent jobs, learning | High-frequency, large-scale |

---

## IAM Trust Policy Explained

```json
{
  "Principal": { "Service": "emr-serverless.amazonaws.com" }
}
```

- `emr-serverless.amazonaws.com` — the EMR Serverless service assumes this role
  when running your job. This is NOT the same as `emr.amazonaws.com` (for EMR on EC2).
- The role is passed via `--execution-role-arn` in `start-job-run`
- When Spark reads S3 or writes Parquet, it uses THIS role's S3 permissions
- When Spark writes logs, it uses THIS role's CloudWatch Logs permissions

---

## DynamoDB Key Design for Output (Not Used Here)

For reference — this project writes to S3, not DynamoDB.
For real-time aggregates, see Project 9.3 (Kinesis → Lambda → DynamoDB).
For batch aggregates (this project), S3 Parquet → Athena is the right pattern.

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
