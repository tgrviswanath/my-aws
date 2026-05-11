# Architecture — Project 7.4 Athena Log Analytics

## Query Flow

```
S3 (log files)
  ├── CloudTrail logs (JSON, partitioned by year/month/day)
  ├── ALB access logs (text, partitioned by year/month/day)
  └── VPC Flow Logs (text, partitioned by year/month/day)
        │
        │ Glue Data Catalog (schema + partition metadata)
        ▼
  Amazon Athena
  (serverless SQL engine — reads S3 directly)
        │
        │ Query results → S3 results bucket
        ▼
  You (console, CLI, or BI tool)
```

## Partition Pruning (Cost Optimization)

```sql
-- BAD: scans ALL data (expensive)
SELECT * FROM cloudtrail_logs WHERE eventname = 'DeleteBucket';

-- GOOD: scans only Jan 2024 (cheap)
SELECT * FROM cloudtrail_logs
WHERE year = '2024' AND month = '01'
  AND eventname = 'DeleteBucket';
```

## Cost Formula

```
Cost = (GB scanned) × $0.005

Examples:
  1 GB scanned  = $0.005
  100 GB scanned = $0.50
  1 TB scanned  = $5.00

With partition pruning: scan 1 day instead of 1 year
  = 1/365 of the cost
```
