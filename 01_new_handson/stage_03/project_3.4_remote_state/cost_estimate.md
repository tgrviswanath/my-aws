# Cost Estimate — Project 3.4 Terraform Remote State

| Resource | Monthly Cost |
|----------|-------------|
| S3 bucket (state files, < 1 MB) | $0 (free tier) |
| S3 versioning storage | ~$0.01 |
| DynamoDB (PAY_PER_REQUEST, minimal ops) | $0 (free tier: 25 WCU/RCU) |
| S3 API calls (state reads/writes) | ~$0.01 |
| **Total** | **~$0.02/month** |

## Notes
- Remote state infrastructure is essentially free
- This is a one-time setup — keep it running permanently
- The S3 bucket should NEVER be destroyed (it holds all your state)
- Use `lifecycle { prevent_destroy = true }` on the state bucket
