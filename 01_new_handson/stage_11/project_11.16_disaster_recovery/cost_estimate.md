# Cost Estimate — Project 11.16 Disaster Recovery Network

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC x2 (2 regions) | 2 | $0 |
| ALB x2 | ~2 hrs each | ~$0.03 |
| NAT Gateway x2 | ~2 hrs each | ~$0.18 |
| EC2 t3.micro x4 | ~2 hrs each | ~$0.08 |
| Route 53 Health Check | 1 | $0.50 |
| Route 53 DNS queries | ~1M | $0.40 |
| **Total (2-hr lab)** | | **~$1.19** |

## Full Monthly Cost (if left running)
| Resource | Monthly Cost |
|----------|-------------|
| 2x ALB | ~$32 |
| 2x NAT Gateway | ~$65 |
| 4x EC2 t3.micro | ~$30 |
| Route 53 health check | $0.50 |
| **Total** | **~$128/month** |

## DR Cost Optimization Strategies
| Strategy | Cost | RTO |
|----------|------|-----|
| Pilot light (minimal DR) | ~$5/month | 30-60 min |
| Warm standby (this project) | ~$64/month | 1-5 min |
| Active-active | ~$128/month | Seconds |

## Teardown
```bash
terraform destroy  # run for both regions
```
