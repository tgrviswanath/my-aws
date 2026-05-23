# Cost Estimate — Project 11.10 Multi-Region VPC

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC x2 (2 regions) | 2 | $0 |
| Inter-region peering | 1 | $0 |
| Data transfer (cross-region) | ~100 MB | ~$0.002 |
| EC2 t3.micro x2 | ~2 hrs each | ~$0.04 |
| **Total** | | **~$0.05** |

## Cross-Region Data Transfer Costs
| Route | Cost per GB |
|-------|-------------|
| us-east-1 ↔ us-west-2 | ~$0.02/GB |
| us-east-1 ↔ eu-west-1 | ~$0.02/GB |
| us-east-1 ↔ ap-southeast-1 | ~$0.09/GB |

For high-volume cross-region traffic, consider AWS Direct Connect or CloudFront.

## Teardown
```bash
terraform destroy  # run in both regions
```
