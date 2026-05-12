# Project 7.4 — Athena Log Analytics

## What This Does
Uses Amazon Athena to run SQL queries directly against log files stored in S3 — CloudTrail audit logs, ALB access logs, and VPC Flow Logs. No infrastructure to manage, pay per query.

## Logs Analyzed
| Log Type | S3 Location | What It Shows |
|----------|-------------|---------------|
| CloudTrail | s3://bucket/AWSLogs/ACCOUNT/CloudTrail/ | Every API call made in your account |
| ALB Access Logs | s3://bucket/AWSLogs/ACCOUNT/elasticloadbalancing/ | Every HTTP request to your ALB |
| VPC Flow Logs | s3://bucket/AWSLogs/ACCOUNT/vpcflowlogs/ | Every network connection in your VPC |

## Key Queries
- Top 10 API callers (CloudTrail)
- Failed login attempts (CloudTrail)
- Slowest API endpoints (ALB)
- Top source IPs (ALB + VPC Flow)
- Rejected network connections (VPC Flow)
- Cost by service (CloudTrail + Cost Explorer)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output athena_query_url
```

## Lessons Learned
- Athena charges $5 per TB scanned — always use partition pruning (WHERE year=2024 AND month=01)
- Partition projection: Athena auto-discovers partitions without MSCK REPAIR TABLE
- Columnar formats (Parquet/ORC) are 10x cheaper to query than JSON/CSV
- Use LIMIT in exploratory queries to avoid scanning full datasets
- Workgroups: set per-query data scan limits to prevent runaway costs

## Code

### `queries/cloudtrail_queries.sql` — Athena queries for CloudTrail logs

```bash
# Run via AWS CLI
aws athena start-query-execution \
  --query-string "$(cat queries/cloudtrail_queries.sql)" \
  --query-execution-context Database=cloudtrail_logs \
  --result-configuration OutputLocation=s3://my-athena-results/
```

### `queries/alb_queries.sql` — Athena queries for ALB access logs

```bash
aws athena start-query-execution \
  --query-string "$(cat queries/alb_queries.sql)" \
  --query-execution-context Database=alb_logs \
  --result-configuration OutputLocation=s3://my-athena-results/
```

Queries included: top IPs by request count, 5xx error analysis, slow requests (>1s), geographic distribution.
