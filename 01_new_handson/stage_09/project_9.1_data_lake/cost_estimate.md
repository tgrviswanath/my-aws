# Cost Estimate — Project 9.1 Data Lake Architecture

## Lab Session Cost (2-4 hours)

| Resource | Usage | Unit Price | Cost |
|----------|-------|-----------|------|
| S3 storage (raw + processed + curated) | < 5 GB | $0.023/GB/mo | **$0.00** (free tier) |
| S3 PUT requests | ~50 uploads | $0.005/1000 | **$0.00** |
| S3 GET requests (Athena reads) | ~100 requests | $0.0004/1000 | **$0.00** |
| Glue Crawler (3 manual runs) | 3 × 1 DPU × 2 min | $0.44/DPU-hr | **~$0.04** |
| Glue Data Catalog | < 1M objects | Free up to 1M | **$0.00** |
| Athena queries | < 100 MB scanned | $5/TB | **~$0.00** |
| Lake Formation | N/A | Free | **$0.00** |
| IAM roles/policies | N/A | Free | **$0.00** |
| CloudWatch Logs (Glue logs) | < 5 MB | $0.50/GB ingested | **$0.00** |
| **Total** | | | **~$0.04–0.09** |

---

## Free Tier Eligibility

| Service | Free Tier Allowance | This Project Uses |
|---------|--------------------|--------------------|
| S3 | 5 GB storage, 20,000 GET, 2,000 PUT | < 5 GB storage, ~200 requests |
| Glue Data Catalog | 1M objects, 1M requests/month | < 100 objects |
| CloudWatch Logs | 5 GB ingestion/month | < 1 MB |
| IAM | Always free | Yes |
| Lake Formation | Always free | Yes |

**Not free tier:** Glue Crawler DPU-hours and Athena query scans (no free tier).

---

## Monthly Cost (if left running)

**⚠️ Warning: These costs accrue if you don't destroy resources.**

| Resource | Always-on cost | Note |
|----------|---------------|------|
| S3 storage (10 GB data) | $0.23/mo | Grows as data accumulates |
| Glue Crawler (daily schedule) | ~$13.20/mo | $0.44/DPU × 1hr × 30 days |
| Athena (100 GB/mo queries) | $0.50/mo | Depends on query volume |
| **Total** | **~$14/mo** | If crawler runs daily on schedule |

**Key cost drivers:**
- **Glue Crawler** on daily schedule: $0.44 × 30 = $13.20/mo
  → Solution: disable schedule, run manually only when needed
- **Athena** without partition filters: 100x more expensive
  → Solution: always add WHERE year=... AND month=... in queries

---

## Cost Optimization Techniques

### 1. Use Parquet instead of CSV in processed/curated zones
```
CSV query (1 TB table, 3 columns selected):   $5.00
Parquet query (same data, same query):         $0.50
Savings: 90%
```

### 2. Always partition your data
```
SELECT SUM(amount) FROM orders               → scans all 1 TB  → $5.00
SELECT SUM(amount) FROM orders WHERE year=2024 → scans 250 GB → $1.25
  AND month=01                                 → scans 21 GB   → $0.10
  AND day=15                                   → scans 700 MB  → $0.003
```

### 3. Use Athena scan limit (already configured)
```hcl
bytes_scanned_cutoff_per_query = 1073741824  # 1 GB max
```
This cancels any query that would scan more than 1 GB, capping per-query cost at $0.005.

### 4. Disable Glue Crawler schedule for learning
```bash
# Remove schedule (run manually only)
aws glue update-crawler --name handson-raw-crawler --schedule ""
# This eliminates the $13.20/mo crawler cost
```

### 5. S3 Intelligent-Tiering for processed data
```
S3 Standard (processed/):  $0.023/GB/mo
S3 Intelligent-Tiering:    Auto-moves to cheaper tiers based on access pattern
  → Infrequent Access:     $0.0125/GB/mo (45% savings)
  → Archive Instant:       $0.004/GB/mo (83% savings)
```

### 6. Use S3 Select for large CSV files (before Glue migration)
```sql
-- Instead of Athena scanning the whole file, S3 Select filters server-side
SELECT * FROM S3Object WHERE order_date = '2024-01-15'
-- Cost: per-byte returned, not per-byte scanned
```

---

## Athena Cost Calculator

Use this formula to estimate query costs:

```
Cost = (bytes_scanned / 1,099,511,627,776) × $5.00
     = (bytes_scanned / 1 TB in bytes) × $5

Example:
  Query scans 500 MB CSV:
  Cost = (524,288,000 / 1,099,511,627,776) × $5 = $0.00238

  Same data in Parquet (10x smaller):
  Cost = (52,428,800 / 1,099,511,627,776) × $5 = $0.000238

  With partition filter (scans only 1 month = ~5% of data):
  Cost = (2,621,440 / 1,099,511,627,776) × $5 = $0.0000119
```

---

## Teardown to Stop All Costs

```bash
# 1. Empty S3 buckets (required before terraform destroy)
BUCKET=$(terraform output -raw data_lake_bucket)
ATHENA_BUCKET=$(terraform output -raw athena_results_bucket)
aws s3 rm s3://$BUCKET --recursive
aws s3 rm s3://$ATHENA_BUCKET --recursive

# 2. Destroy all Terraform-managed resources
cd terraform && terraform destroy -auto-approve

# 3. Verify no remaining costs
aws s3 ls | grep handson     # should be empty
aws glue list-crawlers       # should be empty
aws athena list-work-groups  # should show only 'primary' (built-in)
```

**After teardown cost: $0.00/month**

---

## Cleanup

`ash
# Delete all resources created in this project
# (Run after completing the lab to avoid unexpected charges)

# Delete Lambda functions
aws lambda list-functions --query 'Functions[*].FunctionName' --output text | \
  xargs -r -n1 aws lambda delete-function --function-name

# Delete S3 buckets (empty first)
aws s3 ls | awk '{print }' | grep "handson" | \
  xargs -r -I{} aws s3 rb s3://{} --force

# Delete CloudFormation stacks (if used)
aws cloudformation delete-stack --stack-name <stack-name>

# Verify cleanup - check for running resources
aws ec2 describe-instances --filters Name=instance-state-name,Values=running --output table
aws rds describe-db-instances --query 'DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}' --output table
`

**Cost after cleanup:** .00/month
