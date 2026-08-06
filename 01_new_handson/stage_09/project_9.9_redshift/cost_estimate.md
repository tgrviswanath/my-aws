# Cost Estimate — Project 9.9 Redshift Data Warehouse

> Pricing based on us-east-1 (N. Virginia) as of 2024.
> Source: https://aws.amazon.com/redshift/pricing/

---

## Redshift Serverless Pricing

```
Charge: per RPU-second while queries are RUNNING
  1 RPU = Redshift Processing Unit
  Rate:  $0.045 per RPU-hour  →  $0.0000125 per RPU-second

Base capacity: 8 RPU (minimum for Redshift Serverless)
  Running cost: 8 × $0.045 = $0.36/hour
  Idle cost:    $0.00 (Serverless scales to 0 when idle)
```

---

## Learning Session Estimate

| Activity | Duration | RPU | Cost |
|----------|----------|-----|------|
| Create workgroup | 0 min | 0 | $0.00 |
| `setup` (create tables) | ~30s | 8 | ~$0.001 |
| `load` (COPY 1,000 rows) | ~60s | 8 | ~$0.003 |
| `report` (4 queries) | ~2 min | 8 | ~$0.012 |
| Query Editor experiments | ~30 min | 8 | ~$0.18 |
| **2-hour lab total** | | | **~$0.20–$0.75** |

> Workgroup is idle between queries → charges stop. Only billed during actual query execution.

---

## Scenario Comparison

| Scenario | Sessions/month | Daily query time | Monthly cost |
|----------|---------------|-----------------|-------------|
| Learning (this guide) | 5 × 2hr | 2hr | ~$3 |
| Daily BI dashboard | 30 days × 2hr | 2hr | ~$18 |
| Heavy analytics | 30 days × 8hr | 8hr | ~$72 |
| Always-on (never paused) | 30 days × 24hr | 24hr | ~$259 |

---

## Free Tier

| Service | Free Tier | This Project |
|---------|-----------|-------------|
| Redshift Serverless | ❌ No free tier | Always charged |
| IAM | ✅ Free | Free |
| S3 (< 5 GB) | ✅ 5 GB/month | Free |
| Redshift Spectrum | ❌ $5/TB scanned | Minimal |

---

## vs Redshift Provisioned Cluster

| | Serverless | Provisioned (dc2.large ×1) |
|-|-----------|--------------------------|
| Min cost | $0 idle | ~$180/month always-on |
| Running cost | $0.36/hr | ~$0.25/hr (but always-on) |
| Setup | 5–10 min | 10–15 min |
| Management | None | Node type, count, resize |
| **Best for** | Variable workloads, learning | Steady production queries |

---

## Cost Control Tips

```powershell
# 1. Pause workgroup when not using (stops all charges immediately)
aws redshift-serverless update-workgroup `
  --workgroup-name handson-workgroup --base-capacity 0

# 2. Delete after learning (completely stops all charges)
aws redshift-serverless delete-workgroup --workgroup-name handson-workgroup
aws redshift-serverless delete-namespace --namespace-name handson-namespace

# 3. Use Athena for ad-hoc queries (much cheaper at low volume)
#    Athena: $0.000005 per query on 1 MB → use for exploration
#    Redshift: $0.36/hr → use for dashboards needing sub-second

# 4. Set RPU lower if possible (minimum is 8 for Serverless)
#    8 RPU is already the minimum for Serverless
```

---

## After Cleanup

After running the cleanup commands, cost drops to **$0.00/month**.
Only S3 storage remains: ~$0.023/GB/month for processed Parquet files.

---

## Total

**Estimated lab cost: .00 â€“ .00** depending on usage.

| Scenario | Duration | Cost |
|---------|---------|------|
| Learning session | 2-4 hours | .00 â€“ .00 |
| Left running overnight | 12 hours | .50 â€“ .00 |
| Monthly (if not cleaned up) | 30 days |  â€“  |

**Recommendation:** Delete all resources immediately after the lab session.
