# Cost Estimate — Project 11.5 Three-Tier Web Application

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC + 6 Subnets + IGW | 1 each | $0 |
| NAT Gateway x2 | 2 (hourly) | ~$64.80 |
| NAT data processing | ~1 GB | ~$0.09 |
| Elastic IPs x2 (attached) | 2 | $0 |
| EC2 t3.micro x3 | ~2 hrs | ~$0.06 |
| **Total** | | **~$65/month** |

## ⚠️ Cost Warning
Two NAT Gateways = ~$0.09/hr combined. For a 2-hour lab = ~$0.18.
**Always destroy after the lab.**

## Cost Optimization Options
- Use 1 NAT Gateway (shared) for learning — saves 50% but loses AZ isolation
- Use NAT Instances (t3.nano) for dev/learning — ~$6/month for two

## Teardown
```bash
terraform destroy
```
