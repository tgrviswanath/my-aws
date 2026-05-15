# Hands-on Log — Project 3.3: Terraform Modules & Environments

**Date:** 2026-05-14
**Region:** ap-south-1 (Mumbai)
**Account:** 495331821583
**IAM User:** vswnth1
**Terraform Version:** v1.7.5

---

## What This Project Does

Refactors the flat infrastructure from Project 3.2 into **reusable Terraform modules**, then deploys the same infrastructure to **dev** and **qa** environments with completely separate state files. Demonstrates the DRY (Don't Repeat Yourself) principle — write the module once, deploy many times.

---

## Project Structure

```
project_3.3_terraform_modules/
├── modules/
│   ├── vpc/        ← reusable VPC module (VPC, subnets, IGW, NAT, route tables)
│   ├── ec2/        ← reusable EC2 module (ALB, ASG, Launch Template, SGs)
│   └── rds/        ← reusable RDS module (RDS MySQL, SG, subnet group)
├── environments/
│   ├── dev/        ← dev: 10.0.0.0/16, t3.micro, desired_capacity=1
│   ├── qa/         ← qa:  10.1.0.0/16, t3.micro, desired_capacity=1
│   └── prod/       ← prod: 10.2.0.0/16, t3.small, multi_az=true (not deployed)
└── screenshot/
    └── handson_log.md
```

---

## Pre-flight Fixes Applied

Before starting the hands-on, the following issues were identified and fixed:

| File | Issue | Fix |
|------|-------|-----|
| `environments/dev/main.tf` | Region `us-east-1`, wrong AZs | Changed to `ap-south-1`, AZs to `ap-south-1a/b` |
| `environments/prod/main.tf` | Same region/AZ issues | Same fix, 3 AZs: `ap-south-1a/b/c` |
| `modules/rds/main.tf` | `backup_retention_period = var.multi_az ? 7 : 1` | Changed to `0` (free tier) |
| `modules/rds/main.tf` | Single-line egress block | Expanded to multi-line |
| `modules/vpc/main.tf` | Single-line route blocks | Expanded to multi-line |
| `modules/ec2/main.tf` | Single-line variable blocks with 2 args | Expanded to multi-line |
| `modules/rds/main.tf` | `type = string sensitive = true` on one line | Expanded to multi-line |
| `modules/vpc/main.tf` | `type = map(string) default = {}` on one line | Expanded to multi-line |
| `modules/ec2/` | Missing entirely | Created from scratch |
| `environments/qa/` | Missing entirely | Created from scratch |

---

## Phase 1 — Dev Environment

### Step 1: terraform init

```
cd environments/dev
terraform init
```

**Observation:** Terraform initialized all 3 modules cleanly:
- `ec2 in ..\..\modules\ec2`
- `rds in ..\..\modules\rds`
- `vpc in ..\..\modules\vpc`
- Provider: `hashicorp/aws v5.100.0` installed

### Step 2: terraform plan

```
terraform plan -var="db_password=Handson2026Pass!"
```

**Observation:** `Plan: 28 to add, 0 to change, 0 to destroy`
- 4 outputs planned: `alb_dns_name`, `alb_url`, `rds_endpoint`, `vpc_id`
- All resources namespaced under `module.vpc.*`, `module.ec2.*`, `module.rds.*`

### Step 3: terraform apply

```
terraform apply -var="db_password=Handson2026Pass!"
```

**Observation:** All 28 resources created successfully.

**Resource creation order (dependency chain):**
1. `module.vpc.aws_vpc.main` — VPC first (12s)
2. Subnets, IGW, EIP, route tables — parallel
3. `module.ec2.aws_security_group.alb` → `module.ec2.aws_security_group.app`
4. `module.ec2.aws_launch_template.app`
5. `module.vpc.aws_nat_gateway.main` (1m55s — slowest VPC resource)
6. `module.ec2.aws_lb.app` (2m52s)
7. `module.ec2.aws_lb_listener.http`
8. `module.ec2.aws_autoscaling_group.app` (16s)
9. `module.rds.aws_db_instance.mysql` (5m5s — slowest overall)

**Apply complete:** `Resources: 28 added, 0 changed, 0 destroyed`

**Outputs:**
```
alb_dns_name = "handson-dev-alb-683186817.ap-south-1.elb.amazonaws.com"
alb_url      = "http://handson-dev-alb-683186817.ap-south-1.elb.amazonaws.com"
rds_endpoint = "handson-dev-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306"
vpc_id       = "vpc-0ae2e324b5a34ee35"
```

### Step 4: Verify Dev

**Browser response:**
```
ip-10-0-11-11.ap-south-1.compute.internal
AZ: | Env: dev
```

**Key observation:** IP `10.0.11.11` — confirms VPC CIDR `10.0.0.0/16` is correct.

**terraform state list output:**
```
module.ec2.data.aws_ami.amazon_linux
module.ec2.aws_autoscaling_group.app
module.ec2.aws_launch_template.app
module.ec2.aws_lb.app
module.ec2.aws_lb_listener.http
module.ec2.aws_lb_target_group.app
module.ec2.aws_security_group.alb
module.ec2.aws_security_group.app
module.rds.aws_db_instance.mysql
module.rds.aws_db_subnet_group.main
module.rds.aws_security_group.rds
module.vpc.aws_eip.nat
module.vpc.aws_internet_gateway.main
module.vpc.aws_nat_gateway.main
module.vpc.aws_route_table.private
module.vpc.aws_route_table.public
module.vpc.aws_route_table_association.private_app[0]
module.vpc.aws_route_table_association.private_app[1]
module.vpc.aws_route_table_association.private_db[0]
module.vpc.aws_route_table_association.private_db[1]
module.vpc.aws_route_table_association.public[0]
module.vpc.aws_route_table_association.public[1]
module.vpc.aws_subnet.private_app[0]
module.vpc.aws_subnet.private_app[1]
module.vpc.aws_subnet.private_db[0]
module.vpc.aws_subnet.private_db[1]
module.vpc.aws_subnet.public[0]
module.vpc.aws_subnet.public[1]
module.vpc.aws_vpc.main
```

**Key observation:** Every resource is prefixed with `module.<name>.` — this is what module namespacing looks like in state. Compare to Project 3.2 where all resources were at the root level.

---

## Phase 2 — QA Environment (Separate State)

### Step 1: terraform init + plan

```
cd environments/qa
terraform init
terraform plan -var="db_password=Handson2026Pass!"
```

**Observation:** `Plan: 28 to add, 0 to change, 0 to destroy`
- Same 28 resources as dev — same modules reused
- Different names: `handson-qa-*` instead of `handson-dev-*`
- Different CIDR: `10.1.0.0/16` instead of `10.0.0.0/16`
- Completely separate state file: `environments/qa/terraform.tfstate`

### Step 2: terraform apply

```
terraform apply -var="db_password=Handson2026Pass!"
```

**Apply complete:** `Resources: 28 added, 0 changed, 0 destroyed`

**Outputs:**
```
alb_dns_name = "handson-qa-alb-611087484.ap-south-1.elb.amazonaws.com"
alb_url      = "http://handson-qa-alb-611087484.ap-south-1.elb.amazonaws.com"
rds_endpoint = "handson-qa-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306"
vpc_id       = "vpc-0bffd322056a89968"
```

### Step 3: Verify QA

**Browser response:**
```
ip-10-1-11-122.ap-south-1.compute.internal
AZ: | Env: qa
```

**Key observation:** IP `10.1.11.122` — confirms QA VPC CIDR `10.1.0.0/16`. Different from dev's `10.0.x.x`. State isolation proven.

---

## Phase 3 — State Isolation Proof

Both environments running simultaneously with completely independent state:

| Property | Dev | QA |
|----------|-----|----|
| VPC ID | `vpc-0ae2e324b5a34ee35` | `vpc-0bffd322056a89968` |
| VPC CIDR | `10.0.0.0/16` | `10.1.0.0/16` |
| EC2 IP | `10.0.11.11` | `10.1.11.122` |
| ALB | `handson-dev-alb-683186817` | `handson-qa-alb-611087484` |
| RDS | `handson-dev-mysql` | `handson-qa-mysql` |
| State file | `environments/dev/terraform.tfstate` | `environments/qa/terraform.tfstate` |

**Key observation:** `terraform state list` in dev and qa show identical resource *types* but track completely different AWS resource *IDs*. Destroying QA has zero impact on dev.

---

## Phase 4 — Destroy

### Destroy QA first

```
cd environments/qa
terraform destroy -var="db_password=Handson2026Pass!"
```

**Destroy complete:** `Resources: 28 destroyed`
- ASG took ~5m43s (waiting for EC2 instances to terminate)
- RDS took ~1m51s
- NAT Gateway took ~1m1s

### Destroy Dev

```
cd environments/dev
terraform destroy -var="db_password=Handson2026Pass!"
```

**Destroy complete:** `Resources: 28 destroyed`
- ASG took ~5m38s
- RDS took ~1m52s
- NAT Gateway took ~1m1s

**Key observation:** Destroying QA had zero effect on dev — dev continued serving traffic throughout QA destroy. This is the core value of separate state files.

---

## Key Learnings

| Concept | What We Observed |
|---------|-----------------|
| **Module reuse** | Same 3 modules (vpc, ec2, rds) deployed to both dev and qa — zero code duplication |
| **Module namespacing** | State shows `module.vpc.*`, `module.ec2.*`, `module.rds.*` — clean separation |
| **State isolation** | `environments/dev/terraform.tfstate` and `environments/qa/terraform.tfstate` are independent files |
| **Module inputs** | Each environment passes different values: CIDR, instance type, desired_capacity |
| **Module outputs** | `module.ec2.app_sg_id` wired directly into `module.rds` — modules communicate via outputs |
| **DRY principle** | 28 resources deployed twice with zero code duplication in the module definitions |
| **CIDR planning** | dev=10.0.x.x, qa=10.1.x.x, prod=10.2.x.x — no overlap, safe to peer if needed |

---

## Resource Summary

| Resource | Dev | QA |
|----------|-----|----|
| VPC | `vpc-0ae2e324b5a34ee35` | `vpc-0bffd322056a89968` |
| ALB | `handson-dev-alb-683186817.ap-south-1.elb.amazonaws.com` | `handson-qa-alb-611087484.ap-south-1.elb.amazonaws.com` |
| RDS | `handson-dev-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306` | `handson-qa-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306` |

---

## Screenshots Checklist

- [ ] Module folder structure in VS Code file explorer
- [ ] `terraform init` output showing all 3 modules initialized
- [ ] `terraform plan` showing 28 resources with `module.*` prefixes
- [ ] `terraform apply` complete — dev outputs
- [ ] Browser: `ip-10-0-11-11... | Env: dev`
- [ ] `terraform state list` — dev (module.vpc.*, module.ec2.*, module.rds.*)
- [ ] `terraform apply` complete — qa outputs
- [ ] Browser: `ip-10-1-11-122... | Env: qa`
- [ ] `terraform state list` — qa (same structure, different IDs)
- [ ] `terraform destroy` complete — both environments
