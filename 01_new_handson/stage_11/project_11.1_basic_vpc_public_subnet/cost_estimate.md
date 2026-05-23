# Cost Estimate — Project 11.1 Basic VPC with Public Subnet

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC | 1 VPC | $0 |
| Subnet | 1 subnet | $0 |
| Internet Gateway | 1 IGW | $0 |
| EC2 t3.micro | ~2 hrs learning | ~$0.02 |
| Elastic IP (unattached) | 0 | $0 |
| **Total** | | **~$0.02** |

## Notes
- VPC, subnets, IGW, and route tables are free
- EC2 t3.micro is free tier eligible (750 hrs/month for 12 months)
- No NAT Gateway in this project — keeps cost at near zero

## Teardown
```bash
terraform destroy
```
Terminate EC2 immediately after the lab to avoid any charges.
