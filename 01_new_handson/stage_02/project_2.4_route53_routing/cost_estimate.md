# Cost Estimate — Project 2.4 Route53 Advanced Routing

| Resource | Monthly Cost |
|----------|-------------|
| Route53 hosted zone | $0.50 |
| Health checks (2) | $1.00 ($0.50 each) |
| DNS queries (~10K) | $0.00 (first 1B free) |
| CloudWatch alarm (1) | $0.10 |
| **Total** | **~$1.60/month** |

## Notes
- Health checks are the main cost here at $0.50/month each
- DNS queries are essentially free for learning volumes
- Delete health checks when done to stop charges
