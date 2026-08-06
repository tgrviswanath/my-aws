# Cost Estimate — Project 10.2: Disaster Recovery

## Component Costs (us-east-1 primary + us-west-2 DR)

### RDS

| Resource | Price | Notes |
|----------|-------|-------|
| Primary RDS Multi-AZ (db.t3.medium) | ~$73/month | Includes standby |
| Cross-region read replica (db.t3.medium) | ~$36/month | Separate instance |
| Cross-region replication data transfer | $0.02/GB | Primary → Replica |
| Automated backups (7 days) | ~$3/month | Snapshot storage |

### S3

| Resource | Price | Notes |
|----------|-------|-------|
| CRR data transfer | $0.02/GB | Per GB replicated |
| CRR PUT requests | $0.005/1K | Per replicated object |
| S3 Replication Time Control | $0.015/GB | Only if RTC enabled |
| DR bucket storage | $0.023/GB/month | Standard storage |

### Route 53

| Resource | Price | Notes |
|----------|-------|-------|
| Health check (standard) | $0.50/month | Per health check |
| Health check (HTTPS with SNI) | $1.00/month | For HTTPS endpoints |
| DNS queries | $0.40/million | For failover records |

---

## Free Tier

- Route 53 health checks: No free tier ($0.50-1.00/month each)
- RDS: 750 hours/month of db.t2.micro (single AZ) for 12 months — not Multi-AZ
- S3 CRR: No free tier for data transfer

---

## Scenario Estimates

### Minimal DR (Pilot Light)
| Resource | Monthly Cost |
|----------|-------------|
| Primary RDS Multi-AZ (db.t3.micro) | $24.82 |
| DR Read Replica (db.t3.micro) | $12.41 |
| S3 CRR (10 GB/month replication) | $0.20 |
| S3 Replication Time Control (10 GB) | $0.15 |
| Route 53 health check | $0.50 |
| Route 53 DNS queries (1M) | $0.40 |
| **Total** | **~$38.48/month** |

### Production DR Setup
| Resource | Monthly Cost |
|----------|-------------|
| Primary RDS Multi-AZ (db.r6g.large) | $186.30 |
| DR Read Replica (db.r6g.large, us-west-2) | $93.15 |
| RDS snapshot storage (100 GB) | $1.90 |
| S3 CRR + RTC (100 GB replication) | $3.65 |
| DR S3 bucket storage (500 GB) | $11.50 |
| Route 53 health checks × 3 | $3.00 |
| **Total** | **~$299.50/month** |

### Full Active/Active DR
| Resource | Monthly Cost |
|----------|-------------|
| Primary RDS (db.r6g.2xlarge, Multi-AZ) | $745 |
| DR RDS (db.r6g.2xlarge, Multi-AZ) | $745 |
| Aurora Global Database premium | Add ~30% | ~$200 |
| Data transfer (1 TB/month cross-region) | $20 |
| **Total** | **~$1,710/month** |

---

## DR Strategy Cost Comparison

| Strategy | RPO | RTO | Monthly Cost |
|----------|-----|-----|-------------|
| Backup & Restore (snapshots only) | Hours | Hours | ~$5 |
| Pilot Light (read replica, this project) | < 5 min | < 30 min | ~$38-300 |
| Warm Standby (scaled-down copy) | Seconds | Minutes | ~$500-1500 |
| Multi-Site Active/Active | Near-zero | Near-zero | ~$1,000-5,000 |

**Business justification:** Cost per minute of downtime (revenue loss) should exceed DR cost.

---

## Cost vs Downtime Analysis

```
If downtime costs your business $1,000/minute:
  DR Cost: $38/month = $0.05/minute of protection
  
If downtime occurs 1× per year and lasts 2 hours without DR:
  Revenue loss without DR: 120 min × $1,000 = $120,000
  DR annual cost: $38 × 12 = $456
  
ROI of DR: ($120,000 - $456) / $456 = 26,216%
```

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Learning/testing | ~$38 | ~$456 |
| Production SMB | ~$300 | ~$3,600 |
| Enterprise | ~$1,710 | ~$20,520 |

---

## Cleanup

```bash
PRIMARY_REGION="us-east-1"
DR_REGION="us-west-2"
PRIMARY_DB="myapp-prod-db"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete Route 53 failover records and health check
aws route53 delete-health-check --health-check-id $HEALTH_CHECK_ID
# (Also delete the CNAME records via change-resource-record-sets)

# Delete RDS read replica (no final snapshot needed for replica)
aws rds delete-db-instance \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --skip-final-snapshot \
  --region $DR_REGION

# Disable S3 replication
aws s3api delete-bucket-replication \
  --bucket "myapp-data-primary-${ACCOUNT_ID}"

# Empty and delete DR S3 bucket
aws s3 rm s3://myapp-data-dr-${ACCOUNT_ID} --recursive --region $DR_REGION
aws s3 rb s3://myapp-data-dr-${ACCOUNT_ID} --region $DR_REGION

# Delete replication IAM role
aws iam delete-role-policy \
  --role-name S3CrossRegionReplicationRole \
  --policy-name S3ReplicationPolicy
aws iam delete-role --role-name S3CrossRegionReplicationRole

# Remove Multi-AZ from primary RDS (cost saving if dev environment)
aws rds modify-db-instance \
  --db-instance-identifier $PRIMARY_DB \
  --no-multi-az \
  --apply-immediately \
  --region $PRIMARY_REGION

echo "DR cleanup complete"
echo "Largest cost savings: deleting read replica ($12-93/month)"
```
