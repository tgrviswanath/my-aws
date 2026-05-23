# Cost Estimate — Project 11.15 Multi-Account Network Architecture

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC + Subnets | 1 VPC | $0 |
| RAM | Resource sharing | $0 |
| Route 53 PHZ | 1 zone | $0.50 |
| Route 53 queries | ~1M queries | $0.40 |
| EC2 t3.micro x2 | ~2 hrs each | ~$0.04 |
| NAT Gateway | ~2 hrs | ~$0.09 |
| **Total** | | **~$1.03** |

## Notes
- RAM itself is free — you only pay for the shared resources
- Route 53 PHZ: $0.50/month per zone + $0.40/million queries
- The main cost driver is the NAT Gateway if left running

## Teardown
```bash
terraform destroy
# Also manually: delete RAM share, disassociate PHZ from Dev VPC
```
