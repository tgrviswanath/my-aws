# Cost Estimate — Project 2.3 ALB vs NLB Comparison Lab

| Resource | Monthly Cost |
|----------|-------------|
| ALB (1 ALB, minimal traffic) | ~$16 |
| NLB (1 NLB, minimal traffic) | ~$16 |
| Elastic IPs (2, attached to NLB) | $0 |
| EC2 instances (existing from 2.2) | $0 (free tier) |
| **Total** | **~$32/month** |

## Notes
- This is a short-lived comparison lab — destroy after completing the comparison
- Both ALBs and NLBs have a base hourly charge (~$0.008/hr) plus LCU charges
- Run for 1–2 days to complete the lab: ~$2 total
