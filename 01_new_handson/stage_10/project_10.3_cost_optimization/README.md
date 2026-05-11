# Project 10.3 — Cost Optimization Automation

## What This Does
Automates AWS cost optimization: identifies idle resources, rightsizes over-provisioned instances, cleans up unused resources, and enforces cost tagging.

## Automations Built
| Automation | Saves | How |
|-----------|-------|-----|
| Stop idle EC2 | ~$15/instance/month | Lambda checks CPU < 5% for 7 days |
| Delete unattached EBS | ~$0.10/GB/month | Lambda finds volumes with no attachment |
| Remove old snapshots | ~$0.05/GB/month | Lambda deletes snapshots > 30 days |
| Rightsize EC2 | 20-50% | Compute Optimizer recommendations |
| S3 lifecycle policies | 60-90% | Move to IA/Glacier after 30/90 days |
| Reserved Instance alerts | 30-60% | Alert when on-demand usage is high |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var="alert_email=your@email.com"
```

## Lessons Learned
- Compute Optimizer: free ML-based rightsizing recommendations — always enable it
- Savings Plans: commit to $/hour spend, not specific instances — more flexible than RIs
- S3 Intelligent-Tiering: auto-moves objects between tiers — good for unpredictable access
- Cost anomaly detection: ML-based alerts when spend spikes unexpectedly
- Tagging is the foundation — you can't optimize what you can't identify
