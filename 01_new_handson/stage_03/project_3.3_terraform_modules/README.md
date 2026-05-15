# Project 3.3 — Terraform Modules & Environments

## What This Does
Refactors the infrastructure from Project 3.2 into reusable modules, then deploys the same infrastructure to dev, qa, and prod environments with different configurations.

## Module Structure
```
project_3.3_terraform_modules/
├── modules/
│   ├── vpc/          ← reusable VPC module
│   ├── ec2/          ← reusable EC2/ALB/ASG module
│   └── rds/          ← reusable RDS module
├── environments/
│   ├── dev/          ← dev environment (small, cheap, desired_capacity=1)
│   ├── qa/           ← qa environment (separate state, same size as dev)
│   └── prod/         ← prod environment (HA, larger, 3 AZs)
└── README.md
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| Module | Reusable group of resources with inputs/outputs |
| Module source | Local path, Git URL, or Terraform Registry |
| Module input | Variable passed into the module |
| Module output | Value exported from the module |
| Environment | Separate state per env — dev/qa/prod |

## How to Deploy
```bash
# Deploy dev environment
cd environments/dev
terraform init
terraform apply -var="db_password=Handson2026Pass!"

# Deploy qa environment (separate state — independent from dev)
cd environments/qa
terraform init
terraform apply -var="db_password=Handson2026Pass!"
```

## Lessons Learned
- Modules make infrastructure DRY — write once, deploy many times
- Each environment has its own state file — changes to dev don't affect prod
- Use `terraform workspace` as an alternative to separate directories (but separate dirs are clearer)
- Module outputs must be explicitly declared — they don't auto-export
- Pin module versions in production: `source = "./modules/vpc"` is fine locally; use Git tags for shared modules

## Code

### `code/env_switcher.py` — Switch between dev/qa/prod Terraform environments

```bash
# Plan for dev environment
python code/env_switcher.py --env dev --action plan

# Apply to qa
python code/env_switcher.py --env qa --action apply

# Apply to prod (requires typing 'yes' to confirm)
python code/env_switcher.py --env prod --action apply

# Destroy dev environment
python code/env_switcher.py --env dev --action destroy --auto-approve

# Run against a specific Terraform directory
python code/env_switcher.py --env dev --action plan --dir ./terraform
```

Expected directory layout:
```
terraform/
├── main.tf
├── variables.tf
└── envs/
    ├── dev.tfvars
    ├── qa.tfvars
    └── prod.tfvars
```

What it does:
- Selects the correct `.tfvars` file for the environment
- Creates or selects the matching Terraform workspace
- Shows a cost estimate comparison table (dev/qa/prod)
- Requires explicit `yes` confirmation before applying to prod
