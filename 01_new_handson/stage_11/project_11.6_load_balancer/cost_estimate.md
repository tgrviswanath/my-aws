# Cost Estimate — Project 11.6 Load Balancer Integration

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| ALB | 1 (hourly) | ~$16.20 |
| ALB LCU | minimal test traffic | ~$0.10 |
| EC2 t3.micro x2 | ~2 hrs | ~$0.04 |
| NAT Gateway x2 | ~2 hrs | ~$0.09 |
| **Total** | | **~$16–17/month** |

## Notes
ALB costs ~$0.008/hr. For a 2-hour lab = ~$0.016.
Destroy after the lab to avoid ongoing charges.

## Teardown
```bash
terraform destroy
```
