# Cost Estimate — Project 1.5 Python AWS Automation

| Resource | Cost |
|----------|------|
| boto3 / Python | $0 |
| AWS API calls (describe, list) | $0 |
| RDS manual snapshots | $0.095/GB-month after free tier |
| S3 copy operations | $0.005 per 1,000 requests |
| **Total** | **~$0 for learning use** |

## Notes
- The scripts themselves cost nothing — you pay only for the AWS resources they interact with
- RDS snapshots: first snapshot is free (same size as DB), additional snapshots charged at $0.095/GB
- Keep snapshots for 7 days max during learning to avoid storage costs
