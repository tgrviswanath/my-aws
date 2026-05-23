# Cost Estimate — Project 11.18 Network Performance Optimization

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| EC2 c5n.large x2 | ~2 hrs each | ~$0.43 |
| Placement Group | 1 | $0 |
| Data transfer (within VPC) | ~100 GB benchmark | $0 |
| **Total (2-hr lab)** | | **~$0.43** |

## Instance Network Performance Reference
| Instance | Network | Baseline | Burst |
|----------|---------|----------|-------|
| t3.micro | Up to 5 Gbps | Low | Yes |
| m5.large | Up to 10 Gbps | Low | Yes |
| c5n.large | Up to 25 Gbps | 4.75 Gbps | Yes |
| c5n.18xlarge | 100 Gbps | 100 Gbps | No |

## Notes
- Data transfer within a VPC is free
- Placement groups are free
- Only EC2 instance hours are charged

## Teardown
```bash
terraform destroy
```
