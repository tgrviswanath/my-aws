# Cost Estimate — Project 11.11 AWS Transit Gateway Hub

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Transit Gateway | 1 TGW (~2 hrs) | ~$0.10 |
| TGW VPC Attachments (3) | 3 x ~2 hrs | ~$0.30 |
| TGW data processing | ~100 MB | ~$0.002 |
| EC2 t3.micro x3 | ~2 hrs each | ~$0.06 |
| **Total** | | **~$0.46** |

## Full Monthly Cost (if left running)
| Resource | Monthly Cost |
|----------|-------------|
| TGW | $36.50 |
| 3 Attachments | $109.50 |
| Data ($0.02/GB) | varies |
| **Total** | **~$146/month** |

## ⚠️ Cost Warning
TGW is expensive for learning. Destroy immediately after the lab.
For learning only, you can use VPC Peering (Project 11.7) which is free.

## Teardown
```bash
terraform destroy
# Order: delete attachments first, then TGW
```
