# Cost Estimate — Project 9.6 dbt Transformation Pipeline

> Pricing based on us-east-1 as of 2024.
> **dbt Core is 100% free and open source — only AWS query costs apply.**

---

## dbt Core vs dbt Cloud

| Option | Cost | Use For |
|--------|------|---------|
| **dbt Core (this project)** | **$0** | Local development, CI/CD pipelines |
| dbt Cloud Developer | $50/seat/month | Team collaboration, managed scheduler |
| dbt Cloud Team | $100/seat/month | Advanced features, SLA support |

> Always use **dbt Core** for learning. dbt Cloud adds no features needed for this project.

---

## AWS Costs (Athena + S3)

### Athena Query Cost

```
Athena pricing: $5.00 per TB of data scanned

For this project's data sizes:
  1,000-row CSV    (~200 KB)  = $0.000001 per query
  100,000-row CSV  (~20 MB)   = $0.0001   per query
  1 GB dataset                = $0.005    per query

dbt run = 2 Athena queries (stg_orders + fct_orders)
  On 1,000 rows:  2 × $0.000001 = $0.000002
  On 100K rows:   2 × $0.0001   = $0.0002
  On 1 GB:        2 × $0.005    = $0.01
```

### S3 Staging Cost

```
Athena writes query results to s3_staging_dir
Each result file: ~1–50 KB (small SQL queries)

Cost:
  Storage: $0.023/GB/month
  For 100 dbt runs × 50 KB results = 5 MB → $0.00012/month

Lifecycle policy (7 days expiry) keeps this near $0.
```

### Per-Session Estimate

| Scenario | Athena Queries | Cost |
|----------|---------------|------|
| Learning session (10 runs × 1,000 rows) | 20 queries | ~$0.00004 |
| Daily CI run (1 run × 100K rows) | 2 queries | ~$0.0002 |
| Daily CI run (1 run × 1 GB) | 2 queries | ~$0.01 |
| Monthly (30 runs × 1 GB) | 60 queries | ~$0.30 |

**Typical learning session: < $0.01 total**

---

## Free Tier Coverage

| Service | Free Tier | This Project |
|---------|-----------|-------------|
| dbt Core | ✅ Always free | Always free |
| Athena | ❌ No free tier | ~$0.00004–$0.01/run |
| S3 (< 5 GB) | ✅ 5 GB/month | < 1 MB staging results |
| Glue Data Catalog (< 1M objects) | ✅ 1M objects free | < 10 table definitions |
| IAM | ✅ Free | Free |

---

## Cost Control: Athena Workgroup Query Limit

The Athena workgroup `handson-dbt` has a per-query scan limit:

```hcl
# From terraform/main.tf:
bytes_scanned_cutoff_per_query = 1073741824  # 1 GB hard limit
```

If a dbt model accidentally scans > 1 GB, Athena kills the query.
This prevents runaway costs from accidental full-table scans.

---

## Cleanup to Stop All Costs

```powershell
# Remove dbt output tables (stops Glue catalog storage)
# Drop VIEW and TABLE via Athena
aws athena start-query-execution --query-string "DROP VIEW IF EXISTS handson_data_lake.stg_orders" ...
aws athena start-query-execution --query-string "DROP TABLE IF EXISTS handson_data_lake.fct_orders" ...

# Delete S3 staging (stops S3 storage cost)
aws s3 rm s3://handson-dbt-staging-ACCOUNT --recursive
aws s3api delete-bucket --bucket handson-dbt-staging-ACCOUNT

# Delete Athena workgroup
aws athena delete-work-group --work-group handson-dbt --recursive-delete-option
```

After cleanup: **$0.00/month ongoing cost**.

---

## Total

**Estimated lab cost: .00 â€“ .00** depending on usage.

| Scenario | Duration | Cost |
|---------|---------|------|
| Learning session | 2-4 hours | .00 â€“ .00 |
| Left running overnight | 12 hours | .50 â€“ .00 |
| Monthly (if not cleaned up) | 30 days |  â€“  |

**Recommendation:** Delete all resources immediately after the lab session.
