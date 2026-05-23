# Cost Estimate — Project 11.13 Direct Connect Simulation

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPN Connection (BGP) | ~2 hrs | ~$0.10 |
| EC2 t3.micro (BGP router) | ~2 hrs | ~$0.02 |
| EC2 t3.micro (AWS private) | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.14** |

## Real Direct Connect Costs (for reference)
| Port Speed | Monthly Cost |
|------------|-------------|
| 1 Gbps hosted | ~$220/month |
| 10 Gbps dedicated | ~$1,620/month |
| Data transfer | $0.02/GB (out) |

Direct Connect is expensive — this simulation gives you the BGP concepts at near-zero cost.

## Teardown
```bash
terraform destroy
```
