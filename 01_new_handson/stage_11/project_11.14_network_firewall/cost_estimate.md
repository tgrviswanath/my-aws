# Cost Estimate — Project 11.14 AWS Network Firewall

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Network Firewall endpoint | 1 AZ (~2 hrs) | ~$0.79 |
| Firewall data processing | ~1 GB | ~$0.065 |
| EC2 t3.micro | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.88** |

## Full Monthly Cost (if left running)
| Resource | Monthly Cost |
|----------|-------------|
| Firewall endpoint (per AZ) | ~$285 |
| Data processing ($0.065/GB) | varies |
| **Total** | **~$285+/month** |

## ⚠️ Cost Warning
Network Firewall is the most expensive resource in this stage at ~$0.395/hr per AZ.
Destroy immediately after the lab.

## Teardown
```bash
terraform destroy
# Order: delete firewall → policy → rule groups
```
