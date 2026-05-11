# Cost Estimate — Project 7.4 Athena Log Analytics

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Athena queries (10 queries × 100 MB each) | 1 GB scanned | $0.005 |
| S3 query results storage | < 100 MB | $0 |
| Glue Data Catalog | < 1M objects | $0 (free tier) |
| **Total** | | **~$0.01/month** |

## Notes
- Athena is extremely cheap for learning — pay only for data scanned
- Always use partition filters (WHERE year=... AND month=...) to minimize scans
- The 1 GB scan limit in the workgroup prevents accidental large queries
- CloudTrail and ALB logs are already in S3 — no extra storage cost
