# Project 2.2 — Multi-Tier Web Application

## What This Does
Deploys a full 3-tier web application inside the custom VPC from Project 2.1: CloudFront → ALB → EC2 (Auto Scaling) → RDS.

## Architecture
```
Internet
  → CloudFront (CDN + HTTPS)
    → ALB (load balancer, public subnets)
      → EC2 Auto Scaling Group (app tier, private subnets)
        → RDS MySQL (db tier, private subnets)
```

## Services Used
| Service | Role |
|---------|------|
| CloudFront | CDN, HTTPS termination |
| ALB | Layer 7 load balancer across AZs |
| EC2 Auto Scaling Group | Horizontally scalable app servers |
| Launch Template | EC2 configuration template |
| RDS MySQL | Managed database in private subnet |
| Security Groups | Layered firewall per tier |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Layered security groups | Each tier only accepts traffic from the tier above it |
| Auto Scaling | Automatically add/remove EC2 instances based on load |
| Launch Template | Defines EC2 config — AMI, type, user data, SG |
| Target Group | ALB routes to a group of EC2 instances |
| Health check | ALB removes unhealthy instances from rotation |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- Security groups chain: ALB-SG → EC2-SG → RDS-SG (each only allows the previous tier)
- ALB must be in public subnets; EC2 and RDS in private subnets
- Auto Scaling needs a Launch Template, not a Launch Configuration (LC is legacy)
- Health check path must return HTTP 200 — configure your app's `/health` endpoint
- CloudFront in front of ALB adds caching and DDoS protection

## Code

### `code/health_check.py` — Check health of all application tiers

```bash
pip install boto3

# Check all tiers (auto-discovers ALB, EC2, RDS)
python code/health_check.py

# Check a specific ALB and RDS instance
python code/health_check.py --alb-arn arn:aws:elasticloadbalancing:... --rds-id mydb

# Use a specific region
python code/health_check.py --region us-west-2
```

What it checks:
| Tier | Check |
|------|-------|
| Tier 1 — ALB | State (active), listener count and ports |
| Tier 1 — Target Groups | Per-target health (healthy/unhealthy count) |
| Tier 2 — EC2 | Instance state, system status checks, instance status checks |
| Tier 3 — RDS | Instance status, Multi-AZ warning if single-AZ |

Prints an overall health report: `ALL SYSTEMS HEALTHY` or `ISSUES DETECTED`.
