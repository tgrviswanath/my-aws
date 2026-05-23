# Cost Estimate — Project 11.19 IPv6 Implementation

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC + Subnets | 1 VPC | $0 |
| Internet Gateway | 1 | $0 |
| Egress-Only IGW | 1 | $0 |
| IPv6 addresses | any number | $0 |
| EC2 t3.micro x2 | ~2 hrs | ~$0.04 |
| **Total** | | **~$0.04** |

## IPv6 Cost Advantages
- IPv6 addresses are FREE (unlike Elastic IPs which cost $0.005/hr when unattached)
- Egress-Only IGW is FREE (unlike NAT Gateway which costs ~$32/month)
- For IPv6-only private subnets: replace NAT Gateway with EIGW → save ~$32/month

## Notes
AWS charges for public IPv4 addresses ($0.005/hr per address since Feb 2024).
IPv6 addresses are always free — another reason to adopt IPv6.

## Teardown
```bash
terraform destroy
```
