# Cost Estimate — Project 9.9 Redshift Data Warehouse

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Redshift Serverless (8 RPU base) | 8 RPU × $0.36/RPU-hr × usage | Pay per use |
| Redshift Serverless (1 hr/day) | 8 × $0.36 × 30 days | ~$86 |
| Redshift storage | < 1 GB | ~$0.02 |
| **Total (1 hr/day usage)** | | **~$86/month** |

## Cost Reduction Tips
- Redshift Serverless scales to 0 when idle — only pay when running queries
- Pause workgroup when not using: `aws redshift-serverless update-workgroup --workgroup-name handson-workgroup --base-capacity 0`
- For learning: run queries for 1-2 hours, then pause
- Alternative: use Athena for ad-hoc queries (much cheaper for low volume)
