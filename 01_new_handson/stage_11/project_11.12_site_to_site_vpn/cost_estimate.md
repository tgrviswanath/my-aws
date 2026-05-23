# Cost Estimate — Project 11.12 Site-to-Site VPN

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPN Connection | 1 (~2 hrs) | ~$0.10 |
| VPN data transfer | ~100 MB | ~$0.009 |
| EC2 t3.micro (strongSwan) | ~2 hrs | ~$0.02 |
| EC2 t3.micro (AWS private) | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.15** |

## Full Monthly Cost (if left running)
| Resource | Monthly Cost |
|----------|-------------|
| VPN Connection | $36.50 |
| Data ($0.09/GB outbound) | varies |
| **Total** | **~$36.50+/month** |

## ⚠️ Cost Warning
VPN connection costs $0.05/hr. Destroy after the lab.

## Teardown
```bash
terraform destroy
```
