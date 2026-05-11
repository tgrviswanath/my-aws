# Cost Estimate — Project 5.5 Blue-Green Deployment

| Resource | Monthly Cost |
|----------|-------------|
| CodeDeploy (ECS deployments) | $0 (free for ECS) |
| ECS Fargate (2x tasks during deploy) | ~$25 (same as 5.4) |
| ALB (shared from 5.4) | ~$16 |
| **Total** | **~$41/month** |

## Notes
- CodeDeploy is free for ECS deployments
- During deployment, you briefly run 2x tasks (blue + green) — short-lived cost
- Destroy after learning: `terraform destroy`
