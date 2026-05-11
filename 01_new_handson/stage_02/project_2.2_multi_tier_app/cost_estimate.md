# Cost Estimate — Project 2.2 Multi-Tier Web Application

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| ALB | 1 ALB, ~1 LCU | ~$16–18 |
| EC2 t3.micro x2 | 2 instances | $0 (free tier) or ~$15 |
| RDS db.t3.micro | 1 instance | $0 (free tier) or ~$13 |
| NAT Gateway | From Project 2.1 | ~$32 |
| Data transfer | Minimal | ~$1 |
| **Total (free tier)** | | **~$50/month** |
| **Total (no free tier)** | | **~$75/month** |

## Cost Reduction Tips
- Destroy after each learning session: `terraform destroy`
- Use 1 EC2 instance (desired=1) during learning
- Skip Multi-AZ on RDS for learning
- NAT Gateway is the biggest cost — delete when not in use
