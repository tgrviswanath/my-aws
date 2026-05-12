# Architecture — Project 3.3 Terraform Modules & Environments

## Module Structure

```
project_3.3_terraform_modules/
├── modules/
│   ├── vpc/        ← reusable VPC module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── rds/        ← reusable RDS module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev/        ← dev: small instances, no HA
    │   └── main.tf
    ├── qa/         ← qa: medium instances
    │   └── main.tf
    └── prod/       ← prod: larger instances, Multi-AZ
        └── main.tf
```

## Module Call Pattern

```hcl
# environments/dev/main.tf
module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = "handson-dev"
  vpc_cidr    = "10.0.0.0/16"
  azs         = ["us-east-1a", "us-east-1b"]
}

module "rds" {
  source         = "../../modules/rds"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  instance_class = "db.t3.micro"   # small for dev
  multi_az       = false
}
```

## Environment Differences

| Setting | Dev | QA | Prod |
|---------|-----|----|------|
| VPC CIDR | 10.0.0.0/16 | 10.1.0.0/16 | 10.2.0.0/16 |
| EC2 type | t3.micro | t3.small | t3.medium |
| RDS type | db.t3.micro | db.t3.small | db.t3.medium |
| Multi-AZ | No | No | Yes |
| AZs | 2 | 2 | 3 |

## State Isolation

```
Each environment has its own state file:
  environments/dev/  → terraform.tfstate (dev resources)
  environments/qa/   → terraform.tfstate (qa resources)
  environments/prod/ → terraform.tfstate (prod resources)

Changes to dev never affect prod.
```
