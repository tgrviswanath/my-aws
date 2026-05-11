# Cost Estimate — Project 9.2 Glue ETL Pipeline

| Resource | Monthly Cost |
|----------|-------------|
| Glue job (2 workers × G.1X × 10 min/day × 30 days) | ~$2.64 |
| Glue Data Catalog | $0 (free tier) |
| S3 storage (processed Parquet) | ~$0.02 |
| **Total** | **~$2.66/month** |

## Notes
- Glue G.1X: $0.44/DPU-hour. 2 workers × 10 min = 0.33 DPU-hours = $0.15/run
- Run manually during learning instead of on schedule to save cost
- Glue bookmarks prevent reprocessing — only new files are processed on reruns
