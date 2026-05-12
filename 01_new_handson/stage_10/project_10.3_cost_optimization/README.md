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

## Code

### `src/cost_optimizer.py` — Automated cost optimization

```bash
pip install boto3

# Dry run — see what would be cleaned up (no changes made)
python src/cost_optimizer.py --dry-run

# Run all optimizations
python src/cost_optimizer.py

# Run specific optimization only
python src/cost_optimizer.py --action stop-idle-ec2
python src/cost_optimizer.py --action delete-unattached-ebs
python src/cost_optimizer.py --action remove-old-snapshots
```

Automations:
| Action | Savings | Criteria |
|--------|---------|---------|
| Stop idle EC2 | ~$15/instance/month | CPU < 5% for 7 days |
| Delete unattached EBS | ~$0.10/GB/month | No attachment for 7 days |
| Remove old snapshots | ~$0.05/GB/month | Older than 30 days |
