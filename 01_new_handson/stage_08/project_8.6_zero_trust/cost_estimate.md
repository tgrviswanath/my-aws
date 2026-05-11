# Cost Estimate — Project 8.6 Zero Trust Security Lab

| Resource | Monthly Cost |
|----------|-------------|
| IAM Identity Center | $0 |
| MFA enforcement | $0 |
| Security groups (micro-segmentation) | $0 |
| VPC Flow Logs (CloudWatch) | ~$0.50 |
| AWS Verified Access (if used) | ~$0.27/hr per endpoint |
| **Total (basic Zero Trust)** | **~$0.50/month** |

## Notes
- Most Zero Trust controls are free (IAM, security groups, MFA)
- AWS Verified Access: $0.27/hr per endpoint — skip for learning, use for production
- The real cost of Zero Trust is engineering time, not AWS charges
