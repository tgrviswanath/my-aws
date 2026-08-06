# Cost Estimate — RDS MySQL Database

> **Region:** us-east-1 (US East - N. Virginia)
> **Scenario:** db.t2.micro or db.t3.micro, Single-AZ, 20 GB storage, running 24/7

---

## Free Tier

AWS Free Tier for new accounts (first 12 months):

| Resource | Free Tier Allowance | Notes |
|----------|--------------------|----|
| db.t2.micro hours | 750 hours/month | Enough for 1 instance running 24/7 |
| RDS storage (gp2) | 20 GB/month | Exactly matches minimum provisioned storage |
| I/O requests | 20,000,000/month | Standard usage |
| Backup storage | 100% of DB storage | 20 GB backup storage free |

> ⚠️ **Free tier applies only to db.t2.micro**, NOT db.t3.micro. If you use db.t3.micro, all hours are billed.

**Free Tier result:** ~$0.00/month for db.t2.micro within limits.

---

## Detailed Cost Breakdown

### RDS Instance — db.t2.micro

| Period | Cost/hour | Monthly (24/7) | Notes |
|--------|-----------|---------------|-------|
| Free Tier (months 1–12) | $0.00 | **$0.00** | 750 hrs/month free |
| After Free Tier | $0.017/hour | **~$12.50/month** | 730 hrs × $0.017 |

### RDS Instance — db.t3.micro (no free tier)

| Period | Cost/hour | Monthly (24/7) | Notes |
|--------|-----------|---------------|-------|
| Any time | $0.017/hour | **~$12.50/month** | Not covered by free tier |
| Savings Plan (1yr) | ~$0.011/hour | **~$8.03/month** | ~35% savings |

> **Note:** db.t3.micro has the same price as db.t2.micro but better CPU performance (burstable, credits). db.t2.micro is older architecture.

### Multi-AZ Pricing

| Configuration | Multiplier | Monthly cost (t3.micro) |
|--------------|-----------|------------------------|
| Single-AZ | 1× | ~$12.50/month |
| Multi-AZ | 2× | ~$25.00/month |

---

### RDS Storage — gp2

| Period | Cost | Notes |
|--------|------|-------|
| Free Tier (months 1–12) | $0.00 | 20 GB free |
| After Free Tier | $0.115/GB/month | 20 GB × $0.115 = **$2.30/month** |

### Storage Auto-Scaling

If storage autoscaling triggers (you set max 100 GB):
- Every GB added costs $0.115/month
- You only pay for what's actually provisioned after autoscaling

### gp2 vs gp3 Storage

| Type | Cost | IOPS | Throughput |
|------|------|------|-----------|
| gp2 | $0.115/GB/month | 3 IOPS/GB (min 100) | 128-250 MB/s |
| gp3 | $0.115/GB/month | 3,000 IOPS baseline (free) | 125 MB/s (free) |

For MySQL: gp3 is the better choice (more baseline IOPS for same price).

---

### Automated Backups Storage

| Storage amount | Cost |
|---------------|------|
| Up to 100% of DB size | Free |
| Exceeding 100% of DB size | $0.095/GB/month |

For a 20 GB database: first 20 GB of backup storage is free.

---

### Data Transfer

| Type | Cost |
|------|------|
| Data IN to RDS | Free |
| Data transfer between EC2 and RDS (same AZ) | Free |
| Data transfer between EC2 and RDS (different AZ) | $0.01/GB each way |
| Data OUT to internet | $0.09/GB (first 1 GB free) |

**Best practice:** Put your EC2 and RDS in the same Availability Zone to eliminate cross-AZ data transfer costs.

---

## Total Cost Summary

### During Free Tier (Months 1–12) — db.t2.micro

| Resource | Monthly Cost |
|----------|-------------|
| db.t2.micro (750 hrs/month) | $0.00 |
| Storage 20 GB gp2 | $0.00 |
| Automated backups (≤ 20 GB) | $0.00 |
| Data transfer (same AZ) | $0.00 |
| **Total** | **$0.00/month** |

### After Free Tier — db.t2.micro

| Resource | Monthly Cost |
|----------|-------------|
| db.t2.micro (24/7) | $12.50 |
| Storage 20 GB gp2 | $2.30 |
| Automated backups (≤ 20 GB) | $0.00 |
| Data transfer | ~$0.00–$1.00 |
| **Total** | **~$14.80/month** |

### db.t3.micro (any time, no free tier)

| Resource | Monthly Cost |
|----------|-------------|
| db.t3.micro (24/7) | $12.50 |
| Storage 20 GB gp3 | $2.30 |
| Automated backups | $0.00 |
| Data transfer | ~$0.00–$1.00 |
| **Total** | **~$14.80/month** |

---

## Cost Optimization Tips

1. **Stop the RDS instance when not in use** — RDS supports stopping instances for up to 7 days (then auto-starts). While stopped, only storage costs apply (~$2.30/month)
2. **Use Reserved Instances** — 1-year commitment: ~35% savings; 3-year: ~60% savings
3. **Delete snapshots you don't need** — Manual snapshots are NOT covered by the 100% free backup storage rule
4. **Right-size after profiling** — db.t3.micro is often more than enough for low-traffic apps

---

## Cleanup

Delete ALL RDS resources to stop charges:

### CLI Cleanup

```bash
# Delete RDS instance (no final snapshot for dev cleanup)
aws rds delete-db-instance \
  --db-instance-identifier mydb \
  --skip-final-snapshot \
  --delete-automated-backups

# Wait for deletion
aws rds wait db-instance-deleted --db-instance-identifier mydb

# Delete manual snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier mydb \
  --query 'DBSnapshots[*].DBSnapshotIdentifier' \
  --output text | xargs -I {} \
  aws rds delete-db-snapshot --db-snapshot-identifier {}

# Delete subnet group
aws rds delete-db-subnet-group --db-subnet-group-name mydb-subnet-group

# Delete security group
aws ec2 delete-security-group --group-name rds-mysql-sg

echo "✅ All RDS resources deleted — charges will stop"
```

### Console Cleanup

1. RDS → Databases → `mydb` → Actions → Delete
   - Uncheck "Create final snapshot"
   - Uncheck "Retain automated backups"
   - Type `delete me` to confirm
2. RDS → Snapshots → delete any manual snapshots
3. RDS → Subnet groups → delete `mydb-subnet-group`
4. EC2 → Security Groups → delete `rds-mysql-sg`

After cleanup, verify in AWS Billing → Cost Explorer that no RDS charges appear in the next billing period.
