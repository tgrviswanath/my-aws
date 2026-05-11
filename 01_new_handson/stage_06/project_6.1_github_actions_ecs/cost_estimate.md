# Cost Estimate — Project 6.1 GitHub Actions + ECS CI/CD

| Resource | Monthly Cost |
|----------|-------------|
| GitHub Actions (2,000 min/month free) | $0 |
| ECR image storage | $0 (free tier) |
| ECS Fargate (from Project 5.4) | ~$25 |
| **Total (pipeline only)** | **$0** |

## Notes
- GitHub Actions free tier: 2,000 minutes/month for public repos, unlimited
- Each CI run takes ~3–5 minutes; CD run ~5–8 minutes
- 2,000 minutes covers ~200 deployments/month — more than enough for learning
- The ECS infrastructure cost is from Project 5.4 — not new cost here
