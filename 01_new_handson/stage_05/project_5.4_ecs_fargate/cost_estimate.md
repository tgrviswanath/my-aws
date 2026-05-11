# Cost Estimate — Project 5.4 ECS Fargate Deployment

## Assumptions: 2 tasks running 24/7

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Fargate vCPU | 2 tasks × 0.25 vCPU × 730 hrs | ~$7.30 |
| Fargate memory | 2 tasks × 0.5 GB × 730 hrs | ~$1.60 |
| ALB | 1 ALB, minimal traffic | ~$16 |
| ECR storage | ~200 MB | $0 (free tier) |
| CloudWatch Logs | < 1 GB | $0 (free tier) |
| **Total** | | **~$25/month** |

## Cost Reduction Tips
- Run only 1 task during learning: `desired_count = 1` → ~$12/month
- Destroy after each session: `terraform destroy`
- Fargate Spot: up to 70% cheaper for non-critical workloads
- ALB is the biggest fixed cost — share it across multiple services
