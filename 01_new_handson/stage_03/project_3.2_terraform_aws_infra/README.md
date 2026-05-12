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

## Code

### `code/infra_validator.py` — Validate Terraform-created infrastructure

```bash
pip install boto3

# Validate infrastructure in default region
python code/infra_validator.py

# Validate in a specific region
python code/infra_validator.py --region us-west-2

# Use a specific AWS profile
python code/infra_validator.py --profile staging
```

Checks performed:
| Check | What it looks for |
|-------|------------------|
| VPC | VPC tagged `Project=handson` exists and is `available` |
| Public subnets | Subnets tagged `Tier=public` exist in the VPC |
| Private subnets | Subnets tagged `Tier=private` exist in the VPC |
| EC2 | At least one running instance in the VPC |
| RDS | At least one `available` RDS instance tagged `Project=handson` |

Exit code: `0` = all pass, `1` = one or more failures.
