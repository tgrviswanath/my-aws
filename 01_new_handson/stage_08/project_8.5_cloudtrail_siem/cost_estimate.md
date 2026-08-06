# Cost Estimate — Project 8.5: CloudTrail + Athena SIEM

## CloudTrail Pricing

| Resource | Price | Notes |
|----------|-------|-------|
| Management events — first trail | **Free** | One trail per region is free |
| Management events — additional trails | $2.00 / 100K events | Beyond first trail |
| S3 Data events | $0.10 / 100K events | Per S3 read/write operation |
| Lambda Data events | $0.10 / 100K invocations | Per Lambda execution |
| CloudTrail Insights | $0.35 / 100K events analyzed | Optional anomaly detection |
| CloudTrail Lake | $0.005 / GB ingested | Alternative to S3+Athena |

## Athena Pricing

| Resource | Price | Notes |
|----------|-------|-------|
| Query cost | $5.00 / TB scanned | Billed per query |
| Cancelled queries | $5.00 / TB scanned (partial) | Minimum 10 MB per query |
| DDL/metadata queries | Free | CREATE TABLE, ALTER TABLE |

## S3 Storage

| Resource | Price | Notes |
|----------|-------|-------|
| S3 Standard storage | $0.023 / GB / month | For CloudTrail logs |
| S3 PUT requests | $0.005 / 1K requests | Log file writes |
| S3 GET requests | $0.0004 / 1K requests | Athena reads |

---

## Free Tier

- **CloudTrail**: First management events trail = completely free (ongoing, not time-limited)
- **Event history**: 90 days of management events — always free, no trail needed
- **S3**: First 5 GB/month storage (12 months)
- **Athena**: No free tier — every query costs $5/TB scanned

---

## Scenario Estimates

### Small Account (1 trail, management events only, occasional Athena queries)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| CloudTrail management events (1 trail) | Unlimited | **$0.00** (free) |
| S3 storage (30 MB/month logs) | 30 MB | $0.00 |
| Athena queries (10 queries × 50 MB each) | 500 MB = 0.0005 TB | $0.003 |
| CloudWatch Logs (1 GB/month) | 1 GB | $0.50 |
| **Total** | | **~$0.50/month** |

### Medium Account (1 trail + S3 data events, regular queries)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| CloudTrail trail | 1 (free) | $0.00 |
| S3 data events | 10M events/month | $10.00 |
| S3 log storage (5 GB/month) | 5 GB | $0.12 |
| Athena queries (100 queries × 500 MB) | 50 GB = 0.05 TB | $0.25 |
| CloudWatch Logs (5 GB) | 5 GB | $2.50 |
| **Total** | | **~$13/month** |

### Large Account (multi-region, high data events, automated queries)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Multi-region trails (4 regions) | 3 extra trails | ~$10 |
| S3 data events (100M events) | 100M | $100.00 |
| S3 log storage (100 GB) | 100 GB | $2.30 |
| Athena queries (1000 × 10 GB each) | 10 TB | $50.00 |
| CloudWatch Logs (50 GB) | 50 GB | $25.00 |
| **Total** | | **~$187/month** |

---

## Athena Cost Optimization

```sql
-- BAD: Scans entire table (expensive!)
SELECT * FROM cloudtrail_logs WHERE eventname = 'DeleteBucket';

-- GOOD: Use partition filters (scan only specific day)
SELECT * FROM cloudtrail_logs
WHERE year = '2024' AND month = '01' AND day = '15'
  AND eventname = 'DeleteBucket';
-- Scans ~100MB instead of TBs
```

**Additional optimization tips:**
1. Convert logs to Parquet (70% compression, 10x faster scans)
2. Enable Athena partition projection to auto-discover partitions
3. Use CloudTrail Lake instead for simpler SQL + lower cost at scale
4. Set S3 lifecycle rules to move old logs to Glacier

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Learning (management events only) | ~$0.50 | ~$6 |
| Production (+ data events) | ~$13 | ~$156 |
| Enterprise (multi-region + data) | ~$187 | ~$2,244 |

**For this learning project:** ~$0.50-5/month (management events only, occasional queries)

---

## Cleanup

```bash
# 1. Stop and delete trail
aws cloudtrail stop-logging --name "myapp-audit-trail"
aws cloudtrail delete-trail --name "myapp-audit-trail"

# 2. Delete S3 logs (removes storage costs)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
TRAIL_BUCKET="cloudtrail-logs-${ACCOUNT_ID}"
ATHENA_BUCKET="athena-results-${ACCOUNT_ID}"

aws s3 rm s3://${TRAIL_BUCKET} --recursive
aws s3 rb s3://${TRAIL_BUCKET}

aws s3 rm s3://${ATHENA_BUCKET} --recursive
aws s3 rb s3://${ATHENA_BUCKET}

# 3. Delete Athena workgroup
aws athena delete-work-group \
  --work-group "cloudtrail-siem" \
  --recursive-delete-option

# 4. Delete Glue database
aws glue delete-database --name cloudtrail_db 2>/dev/null

# 5. Delete CloudWatch logs
aws logs delete-log-group \
  --log-group-name "/aws/cloudtrail/myapp-audit"

# 6. Delete metric filter and alarm
aws logs delete-metric-filter \
  --log-group-name "/aws/cloudtrail/myapp-audit" \
  --filter-name "RootAccountLogin"
aws cloudwatch delete-alarms --alarm-names "CloudTrail-RootLogin"

echo "All resources cleaned up"
echo "Note: First trail is free so main savings come from S3 storage deletion"
```
