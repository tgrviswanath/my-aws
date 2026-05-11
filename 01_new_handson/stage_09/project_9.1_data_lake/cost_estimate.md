# Cost Estimate — Project 9.1 Data Lake Architecture

| Resource | Monthly Cost |
|----------|-------------|
| S3 storage (< 5 GB) | $0 (free tier) |
| Glue Crawler (1 DPU-hour/run) | ~$0.44 |
| Glue Data Catalog (< 1M objects) | $0 (free tier) |
| Athena queries (< 1 GB scanned) | ~$0.005 |
| **Total** | **~$0.45/month** |

## Notes
- S3 is essentially free at learning volumes
- Glue Crawler: $0.44/DPU-hour — run manually, not on schedule, to save cost
- Athena: $0.005/GB scanned — use partition filters to minimize scans
