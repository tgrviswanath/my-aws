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
│   ├── dev/          ← dev environment (small, cheap)
│   ├── qa/           ← qa environment (medium)
│   └── prod/         ← prod environment (HA, larger)
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
terraform apply -var-file="dev.tfvars"

# Deploy qa environment
cd environments/qa
terraform init
terraform apply -var-file="qa.tfvars"
```

## Lessons Learned
- Modules make infrastructure DRY — write once, deploy many times
- Each environment has its own state file — changes to dev don't affect prod
- Use `terraform workspace` as an alternative to separate directories (but separate dirs are clearer)
- Module outputs must be explicitly declared — they don't auto-export
- Pin module versions in production: `source = "./modules/vpc"` is fine locally; use Git tags for shared modules
