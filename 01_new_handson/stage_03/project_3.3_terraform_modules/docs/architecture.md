# Architecture — Project 3.3 Terraform Modules & Environments

## Module Structure

```
project_3.3_terraform_modules/
├── modules/
│   ├── vpc/        ← reusable VPC module (main.tf)
│   ├── ec2/        ← reusable EC2/ALB/ASG module (main.tf)
│   └── rds/        ← reusable RDS module (main.tf)
└── environments/
    ├── dev/        ← dev: small instances, no HA  (main.tf)
    ├── qa/         ← qa: same size, separate state (main.tf)
    └── prod/       ← prod: larger instances, Multi-AZ, 3 AZs (main.tf)
```

## Module Call Pattern

```hcl
# environments/dev/main.tf
module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = "handson-dev"
  vpc_cidr    = "10.0.0.0/16"
  azs         = ["ap-south-1a", "ap-south-1b"]
}

module "ec2" {
  source            = "../../modules/ec2"
  name_prefix       = "handson-dev"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  app_subnet_ids    = module.vpc.private_app_subnet_ids
  environment       = "dev"
  key_name          = "handson-key"
  my_ip             = "103.82.209.148/32"
  instance_type     = "t3.micro"
  desired_capacity  = 1
}

module "rds" {
  source         = "../../modules/rds"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  app_sg_id      = module.ec2.app_sg_id   # ← wired from ec2 module output
  instance_class = "db.t3.micro"
  multi_az       = false
}
```

## Environment Differences

| Setting          | Dev          | QA           | Prod          |
|------------------|--------------|--------------|---------------|
| VPC CIDR         | 10.0.0.0/16  | 10.1.0.0/16  | 10.2.0.0/16   |
| EC2 type         | t3.micro     | t3.micro     | t3.small      |
| RDS type         | db.t3.micro  | db.t3.micro  | db.t3.small   |
| Multi-AZ RDS     | No           | No           | Yes           |
| AZs              | 2            | 2            | 3             |
| desired_capacity | 1            | 1            | 2             |

## State Isolation

```
Each environment has its own state file:
  environments/dev/  → terraform.tfstate (dev resources)
  environments/qa/   → terraform.tfstate (qa resources)
  environments/prod/ → terraform.tfstate (prod resources)

Changes to dev never affect prod.
```
