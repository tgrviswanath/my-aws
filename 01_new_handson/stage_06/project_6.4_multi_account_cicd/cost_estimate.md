# Cost Estimate — Project 6.4 Multi-account CI/CD Pipeline

| Resource | Monthly Cost |
|----------|-------------|
| AWS Organizations | $0 |
| IAM cross-account roles | $0 |
| GitHub Actions (free tier) | $0 |
| ECS per account (if deployed) | ~$25 each |
| **Total (pipeline infra only)** | **$0** |

## Notes
- AWS Organizations is free — no charge for creating sub-accounts
- Cross-account IAM roles are free
- The cost comes from the ECS/RDS resources in each account
- For learning: simulate with a single account using different IAM roles

