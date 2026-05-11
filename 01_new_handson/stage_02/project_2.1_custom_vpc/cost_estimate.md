# Cost Estimate — Project 2.1 Custom VPC

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC | 1 VPC | $0 |
| Subnets (6) | 6 subnets | $0 |
| Internet Gateway | 1 IGW | $0 |
| NAT Gateway | 1 NAT (hourly) | ~$32.40 |
| NAT Gateway data | ~1 GB | ~$0.045 |
| Elastic IP (attached) | 1 EIP | $0 |
| Route Tables | 2 tables | $0 |
| **Total** | | **~$32–33/month** |

## ⚠️ Cost Warning
NAT Gateway is the most expensive resource in this project at ~$0.045/hr.

**To minimize cost during learning:**
- Delete the NAT Gateway when not actively using it
- Use `terraform destroy` after each session
- Or replace NAT Gateway with a NAT Instance (t3.nano ~$3/month) for learning only

## Teardown Command
```bash
terraform destroy
```
Always destroy after learning to stop NAT Gateway charges.
