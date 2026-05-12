# Architecture — Project 9.4 Spark Processing on EMR

## EMR Serverless Architecture

```
S3 raw/ (input data)
    │
    │ aws emr-serverless start-job-run
    ▼
EMR Serverless Application: handson-spark
    │
    │ Provisions compute on demand (no idle cluster)
    ▼
┌──────────────────────────────────────────────────┐
│              Spark Job Execution                  │
│                                                    │
│  Driver (1 node, 2 vCPU, 4 GB)                   │
│    └── Coordinates the job                        │
│                                                    │
│  Executors (auto-scaled, up to 20 vCPU)           │
│    ├── Executor 1: processes partition 1          │
│    ├── Executor 2: processes partition 2          │
│    └── Executor N: processes partition N          │
└──────────────────────────────────────────────────┘
    │
    ▼
S3 processed/ (Parquet output)
    │
    ▼
Athena queries results
```

## EMR Serverless vs EMR on EC2

```
EMR Serverless:
  ✅ No cluster to manage
  ✅ Pay per job (vCPU-hour + GB-hour)
  ✅ Auto-scales workers
  ✅ Auto-stops when idle
  ❌ Less control over Spark config
  ❌ Cold start (~30s)

EMR on EC2:
  ✅ Full Spark configuration control
  ✅ Persistent cluster (no cold start)
  ✅ Spot instances (60-90% cheaper)
  ❌ Pay even when idle
  ❌ Cluster management overhead
  ❌ Much more expensive for infrequent jobs
```

## Spark Adaptive Query Execution (AQE)

```python
spark = SparkSession.builder \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

# AQE automatically:
# - Coalesces small partitions after shuffle
# - Converts sort-merge joins to broadcast joins when possible
# - Handles data skew automatically
```
