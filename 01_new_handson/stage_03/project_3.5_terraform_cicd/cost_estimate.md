# Cost Estimate — Project 3.5 Terraform CI/CD Pipeline

| Resource | Monthly Cost |
|----------|-------------|
| GitHub Actions (2,000 min/month free) | $0 |
| IAM OIDC provider | $0 |
| IAM role | $0 |
| S3 state bucket (from Project 3.4) | ~$0.02 |
| Demo S3 bucket (app data) | $0 (free tier) |
| **Total** | **~$0.02/month** |

## Notes
- The pipeline itself is free — GitHub Actions free tier is generous
- The only cost is the remote state infrastructure from Project 3.4
- This pattern scales to enterprise use with no additional cost per pipeline run
