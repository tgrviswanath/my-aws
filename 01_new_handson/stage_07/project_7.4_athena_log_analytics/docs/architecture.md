# Architecture — Project 7.4 Athena Log Analytics

## Serverless Query Architecture

```
S3 (log files — already stored from CloudTrail/ALB/VPC)
    │
    │ No data movement needed — Athena reads S3 directly
    ▼
Glue Data Catalog
    └── Database: handson_logs
          ├── Table: cloudtrail_logs (partition projection)
          ├── Table: alb_logs (partition projection)
          └── Table: vpc_flow_logs (partition projection)
    │
    │ SQL query submitted
    ▼
Athena (serverless query engine)
    │ Reads only relevant S3 partitions (partition pruning)
    │ Parallel scan across S3 objects
    ▼
Results → S3 results bucket → Console / CLI / BI tool
```

## Partition Projection (no MSCK REPAIR needed)

```
Table parameter:
  projection.enabled = true
  projection.year.type = integer, range = 2023,2030
  projection.month.type = integer, range = 1,12, digits = 2
  projection.day.type = integer, range = 1,31, digits = 2

Query:
  SELECT * FROM cloudtrail_logs
  WHERE year = '2024' AND month = '01' AND day = '15'

Athena automatically maps to:
  s3://bucket/AWSLogs/ACCOUNT/CloudTrail/us-east-1/2024/01/15/
```

## Cost Control

```
Workgroup setting: bytes_scanned_cutoff_per_query = 1 GB
→ Query fails if it would scan > 1 GB
→ Prevents accidental full-table scans

Always use partition filters:
  WHERE year = '2024' AND month = '01'  ← scans 1 month
  (without filter: scans ALL years = 100x more expensive)
```
