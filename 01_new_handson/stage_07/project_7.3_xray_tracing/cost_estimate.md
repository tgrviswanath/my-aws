# Cost Estimate — Project 7.3 AWS X-Ray Distributed Tracing

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| X-Ray traces (first 100K free) | ~10K traces | $0 |
| X-Ray scans (first 1M free) | ~100K scans | $0 |
| **Total** | | **$0** |

## Notes
- X-Ray free tier: 100,000 traces recorded + 1,000,000 traces retrieved per month — permanent
- After free tier: $5 per million traces recorded
- Sampling at 5% (default) keeps costs very low even at high traffic
