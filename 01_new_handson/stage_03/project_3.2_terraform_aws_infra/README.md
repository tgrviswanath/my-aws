# Project 3.2 — Terraform AWS Infrastructure

## What This Does
Builds the complete multi-tier AWS infrastructure from Stage 2 using Terraform only — no console clicks. VPC, subnets, EC2, ALB, and RDS all defined as code.

## Infrastructure Created
```
VPC (10.0.0.0/16)
├── 2 Public Subnets  → ALB
├── 2 Private App Subnets → EC2 Auto Scaling Group
├── 2 Private DB Subnets  → RDS MySQL
├── Internet Gateway
├── NAT Gateway
├── Route Tables
├── Security Groups (chained: ALB → EC2 → RDS)
├── ALB + Target Group + Listener
├── Launch Template + Auto Scaling Group
└── RDS MySQL (db.t3.micro)
```

## Key Terraform Patterns Used
| Pattern | Where Used |
|---------|-----------|
| `count` | Create 2 subnets per tier |
| `for_each` | Tag multiple resources |
| `depends_on` | NAT GW depends on IGW |
| `data` source | Latest AMI lookup |
| `locals` | Name prefix, common tags |
| `sensitive` variable | DB password |
| `output` | Export IDs for other configs |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Get outputs
terraform output

# Destroy when done
terraform destroy -var-file="terraform.tfvars"
```

## Lessons Learned
- Split large configs into files: `vpc.tf`, `ec2.tf`, `rds.tf`, `outputs.tf`
- Use `count` for identical resources, `for_each` when each needs a unique config
- Never put passwords in `.tf` files — use variables + `.tfvars` (gitignored)
- `terraform plan -out=plan.tfplan` saves the plan; `terraform apply plan.tfplan` applies exactly that plan
- Use `terraform graph` to visualize resource dependencies
