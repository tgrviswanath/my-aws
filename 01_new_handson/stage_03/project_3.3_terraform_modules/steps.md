# Steps — Project 3.3 Terraform Modules & Environments

## Phase 1 — Understand Module Structure

```bash
# A module is just a directory with .tf files
# It has inputs (variables) and outputs
# You call it with a module block

# Local module
module "vpc" {
  source      = "./modules/vpc"
  name_prefix = "handson-dev"
  vpc_cidr    = "10.0.0.0/16"
}

# Public registry module (Terraform Registry)
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  name    = "my-vpc"
  cidr    = "10.0.0.0/16"
}
```

---

## Phase 2 — Deploy Dev Environment

```bash
cd environments/dev

terraform init
terraform plan -var="db_password=devpassword123"
terraform apply -var="db_password=devpassword123"

terraform output
```

---

## Phase 3 — Deploy QA Environment (separate state)

```bash
cd environments/qa

# Each environment has its own state — completely independent
terraform init
terraform plan -var="db_password=qapassword123"
terraform apply -var="db_password=qapassword123"

# Verify dev and qa are independent
cd ../dev && terraform state list
cd ../qa  && terraform state list
# Both have their own resources — no overlap
```

---

## Phase 4 — Compare Environments

```bash
# Dev: small, no HA
# Prod: larger instances, Multi-AZ RDS, 3 AZs

# Show the difference in plan output
cd environments/dev
terraform plan -var="db_password=x" 2>&1 | grep "instance_class"
# db.t3.micro

cd environments/prod
terraform plan -var="db_password=x" 2>&1 | grep "instance_class"
# db.t3.small
```

---

## Phase 5 — Update a Module (Propagate Change)

```bash
# Add a new tag to the VPC module
# Edit modules/vpc/main.tf — add "CostCenter" tag to common_tags

# Now plan both environments — both will show the change
cd environments/dev
terraform plan -var="db_password=x"
# Shows: ~ aws_vpc.main will be updated in-place (tag change)

cd environments/prod
terraform plan -var="db_password=x"
# Same change — module update propagates to all consumers
```

---

## Screenshots to Take
- [ ] Module directory structure in file explorer
- [ ] `terraform init` showing module initialization
- [ ] Dev environment deployed with outputs
- [ ] QA environment deployed with different config
- [ ] `terraform state list` showing module resources (e.g. `module.vpc.aws_vpc.main`)
- [ ] Module update propagating to both environments in plan
