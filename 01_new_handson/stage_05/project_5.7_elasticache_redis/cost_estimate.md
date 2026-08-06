# Project 5.7 — Cost Estimate: ElastiCache Redis

## Free Tier

| Resource | Free Tier |
|----------|-----------|
| ElastiCache | ❌ **No free tier** |
| EC2 t2/t3.micro (for testing) | ✅ 750 hours/month (first 12 months) |
| CloudWatch metrics | ✅ Free (included with ElastiCache) |

⚠️ **ElastiCache has no free tier.** Charges begin immediately upon cluster creation. The cluster in this project costs approximately **$0.017/hour = $0.41/day = ~$12.40/month**.

---

## Pricing Breakdown (us-east-1)

### Node Pricing

| Node Type | On-Demand Hourly | Monthly (24/7) |
|-----------|-----------------|----------------|
| cache.t3.micro | $0.017/hour | ~$12.41 |
| cache.t3.small | $0.034/hour | ~$24.82 |
| cache.t3.medium | $0.068/hour | ~$49.64 |
| cache.r6g.large | $0.154/hour | ~$112.42 |

**This project uses:** `cache.t3.micro` = **$0.017/hour**

### Data Transfer

| Transfer | Rate |
|----------|------|
| Within same AZ | Free |
| Cross-AZ (replica reads) | $0.01/GB |
| To internet | Standard rates |

### Backup Storage

| Backup | Rate |
|--------|------|
| First backup equal to cluster storage | Free |
| Additional backup storage | $0.085/GB/month |

For dev with no backups enabled: **$0.00**

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| 1× cache.t3.micro, no replica, 24/7 | **~$12.41/month** |
| 1× cache.t3.micro, 8h/day (dev hours) | **~$3.97/month** |
| 1 primary + 1 replica (production) | **~$24.82/month** |
| Multi-AZ with failover (2 nodes) | **~$24.82/month** |

---

## Cleanup

Delete the cluster immediately after this project to stop billing:

```bash
# Delete ElastiCache cluster
aws elasticache delete-cache-cluster \
  --cache-cluster-id "my-redis-dev" \
  --region us-east-1

# Monitor deletion
aws elasticache describe-cache-clusters \
  --cache-cluster-id my-redis-dev \
  --region us-east-1 \
  --query 'CacheClusters[0].CacheClusterStatus' \
  --output text

# After ~5-10 minutes, delete subnet group
aws elasticache delete-cache-subnet-group \
  --cache-subnet-group-name my-redis-subnet-group \
  --region us-east-1
```

After deletion: **$0.00/month**

---

## Cost Tips

- Delete ElastiCache clusters when not in use — there is no "pause" option like App Runner
- For dev/test workloads, consider using a local Redis container (`docker run -d redis:7-alpine`) instead of ElastiCache — costs $0
- ElastiCache Reserved Instances offer up to 55% discount for 1-year commitment — worth it for production
- cache.t3.micro has 0.5GB RAM — appropriate for small caches up to ~300MB of data; monitor `FreeableMemory`
- Use `OBJECT ENCODING key` and `DEBUG OBJECT key` to check memory usage per key type when optimizing
- For production, always use at least 1 replica and enable Multi-AZ — the extra $12/month is worth the HA guarantee
