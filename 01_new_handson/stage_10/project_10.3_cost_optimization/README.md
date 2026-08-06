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

---

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription with required permissions | IAM user or role |
| Configuration | Resource settings | Region, names, sizes |
| Source Data | Files or code to deploy | Application source, data files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed and running services | AWS Console / CLI |
| Endpoints | Service URLs and connection strings | Resource overview page |
| Logs | Execution and audit logs | CloudWatch Logs |

## Quick Start
`ash
# Configure AWS CLI
aws configure

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Create resource group
aws ec2 describe-regions --output table
`

## Lessons Learned
- Always tag AWS resources for cost tracking and organization
- Use IAM roles instead of access keys wherever possible
- Delete resources after learning to avoid unexpected charges
- Enable CloudWatch logging for all services in production
- Use the free tier for all lab exercises to minimize cost
