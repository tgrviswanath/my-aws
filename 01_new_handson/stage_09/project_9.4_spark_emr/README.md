# Project 9.4 — Spark Processing on EMR

## What This Does
Runs distributed data processing jobs using Apache Spark on Amazon EMR. Processes large datasets that are too big for a single machine — partitioned across a cluster of EC2 instances.

## Architecture
```
S3 (input data)
  → EMR Cluster (Spark)
    → Driver node coordinates
    → Worker nodes process partitions in parallel
  → S3 (output Parquet)
    → Athena queries
```

## When to Use EMR vs Glue
| Scenario | Use |
|----------|-----|
| Large datasets (> 100 GB) | EMR |
| Complex ML pipelines | EMR |
| Custom Spark config needed | EMR |
| Simple ETL, managed | Glue |
| Serverless, no cluster management | Glue |
| Cost-sensitive small jobs | Glue |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
# Submit Spark job
aws emr add-steps --cluster-id $CLUSTER_ID --steps file://spark_step.json
```

## Lessons Learned
- EMR on EC2: cheapest but requires cluster management
- EMR Serverless: no cluster to manage, pay per job — best for learning
- Spot instances: 60-90% cheaper for worker nodes — use for non-critical jobs
- Bootstrap actions: install custom packages on all nodes at startup
- EMR Studio: Jupyter notebooks connected to EMR — great for exploration
