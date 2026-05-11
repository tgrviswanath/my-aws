# Cost Estimate — Project 8.1 Secrets Manager + Parameter Store

| Resource | Monthly Cost |
|----------|-------------|
| Secrets Manager (2 secrets) | $0.80 |
| SSM Parameter Store (standard, 3 params) | $0 |
| KMS key | $1.00 |
| KMS API calls (~1000) | $0.03 |
| **Total** | **~$1.83/month** |

## Notes
- Secrets Manager: $0.40/secret/month + $0.05 per 10K API calls
- SSM Standard Parameters: free (up to 10,000 parameters)
- KMS: $1/month per key + $0.03 per 10K API calls
- This is a permanent cost — keep secrets running for all future projects
