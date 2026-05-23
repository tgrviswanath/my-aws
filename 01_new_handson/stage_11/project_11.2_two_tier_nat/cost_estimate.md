# Cost Estimate — Project 11.2 Two-Tier Architecture with NAT Gateway

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC | 1 | $0 |
| Subnets (2) | 2 | $0 |
| Internet Gateway | 1 | $0 |
| NAT Gateway | 1 (hourly) | ~$32.40 |
| NAT data processing | ~1 GB | ~$0.045 |
| Elastic IP (attached) | 1 | $0 |
| EC2 t3.micro x2 | ~2 hrs | ~$0.04 |
| **Total** | | **~$32–33/month** |

## ⚠️ Cost Warning
NAT Gateway is ~$0.045/hr. For a 2-hour lab that's ~$0.09.
**Always destroy after the lab.**

## Teardown
```bash
terraform destroy
```
