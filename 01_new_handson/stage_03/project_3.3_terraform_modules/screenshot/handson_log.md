# Project 3.3 — Terraform Modules & Environments
## Engineering Logbook | Portfolio Case Study

---

## 1. Project Information

| Field | Details |
|-------|---------|
| **Project Name** | Terraform Modules & Environments |
| **Stage** | Stage 03 — Infrastructure as Code |
| **Date** | 2026-05-14 |
| **Region** | ap-south-1 (Mumbai) |
| **AWS Account** | 495331821583 |
| **IAM User** | vswnth1 |
| **Terraform Version** | v1.7.5 |
| **Provider Version** | hashicorp/aws v5.100.0 |

### Objective

Refactor the flat multi-tier infrastructure from Project 3.2 into **reusable Terraform modules**, then deploy the same infrastructure to **dev** and **qa** environments using those modules — with completely separate state files, separate VPCs, and zero code duplication. Demonstrate the DRY (Don't Repeat Yourself) principle in infrastructure as code.

---

## 2. Learning Objectives

- Understand what a Terraform module is and why it exists
- Create reusable modules for VPC, EC2/ALB/ASG, and RDS
- Pass inputs into modules using variables and receive outputs
- Wire modules together — use one module's output as another module's input
- Deploy the same modules to multiple environments (dev, qa) with different configurations
- Understand state isolation — each environment has its own `terraform.tfstate`
- Observe module namespacing in `terraform state list` (`module.vpc.*`, `module.ec2.*`, `module.rds.*`)
- Understand the difference between flat Terraform (Project 3.2) and modular Terraform (Project 3.3)

---

## 3. Prerequisites

### Tools Required

| Tool | Version | Purpose |
|------|---------|---------|
| Terraform | v1.7.5 | Infrastructure provisioning |
| AWS CLI | v2.x | AWS authentication and verification |
| Git Bash / PowerShell | Any | Terminal for running commands |
| Browser | Any | Verify ALB response |

### AWS Setup

- AWS account with IAM user `vswnth1` having programmatic access
- IAM permissions: EC2, VPC, RDS, ELB, AutoScaling, IAM (for SGs)
- Key pair `handson-key` created in `ap-south-1`
- AWS CLI configured: `aws configure` with `ap-south-1` as default region

### Screenshot Placeholders

- `[ screenshot: aws configure output showing ap-south-1 region ]`
- `[ screenshot: aws sts get-caller-identity showing account 495331821583 ]`

---

## 4. Architecture Flow

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16 for dev / 10.1.0.0/16 for qa)    │
│                                                      │
│  ┌──────────────┐    ┌──────────────┐               │
│  │ Public       │    │ Public       │  ← IGW         │
│  │ Subnet AZ-a  │    │ Subnet AZ-b  │               │
│  │ (ALB node)   │    │ (ALB node)   │               │
│  └──────┬───────┘    └──────┬───────┘               │
│         │  ALB (internet-facing)                     │
│         └──────────┬─────────┘                      │
│                    │ HTTP :80                        │
│         ┌──────────▼─────────┐                      │
│         │  Private App Subnets│  ← NAT Gateway       │
│         │  EC2 (ASG, nginx)  │                      │
│         └──────────┬─────────┘                      │
│                    │ MySQL :3306                     │
│         ┌──────────▼─────────┐                      │
│         │  Private DB Subnets │                      │
│         │  RDS MySQL 8.0     │                      │
│         └────────────────────┘                      │
└─────────────────────────────────────────────────────┘

Module boundaries:
  module.vpc  → VPC, subnets, IGW, NAT, EIP, route tables
  module.ec2  → ALB SG, App SG, ALB, Target Group, Listener, Launch Template, ASG
  module.rds  → RDS SG, DB Subnet Group, RDS MySQL instance
```

---

## 5. Folder Structure

```
project_3.3_terraform_modules/
├── modules/
│   ├── vpc/
│   │   └── main.tf        ← VPC, 6 subnets, IGW, NAT, EIP, 2 route tables, 6 associations
│   ├── ec2/
│   │   └── main.tf        ← ALB SG, App SG, ALB, TG, Listener, AMI data, Launch Template, ASG
│   └── rds/
│       └── main.tf        ← RDS SG, DB Subnet Group, RDS MySQL instance
├── environments/
│   ├── dev/
│   │   └── main.tf        ← Calls all 3 modules, CIDR 10.0.0.0/16, t3.micro, capacity=1
│   ├── qa/
│   │   └── main.tf        ← Calls all 3 modules, CIDR 10.1.0.0/16, t3.micro, capacity=1
│   └── prod/
│       └── main.tf        ← Calls all 3 modules, CIDR 10.2.0.0/16, t3.small, multi_az=true
├── code/
│   └── env_switcher.py    ← Python helper to switch between environments
├── docs/
│   └── architecture.md
├── screenshot/
│   ├── handson_log.md     ← This file
│   └── linkedin_carousel.html
├── cost_estimate.md
├── steps.md
└── README.md
```

---

## 6. Code Used

### environments/dev/main.tf

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = "ap-south-1" }

locals {
  env         = "dev"
  name_prefix = "handson-${local.env}"
  common_tags = {
    Project     = "handson"
    Environment = local.env
    ManagedBy   = "terraform"
    Stage       = "stage-03"
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.0.0.0/16"
  azs         = ["ap-south-1a", "ap-south-1b"]
  common_tags = local.common_tags
}

module "ec2" {
  source             = "../../modules/ec2"
  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  app_subnet_ids     = module.vpc.private_app_subnet_ids
  environment        = local.env
  key_name           = var.key_name
  my_ip              = var.my_ip
  instance_type      = "t3.micro"
  desired_capacity   = 1
  min_size           = 1
  max_size           = 2
  common_tags        = local.common_tags
}

module "rds" {
  source         = "../../modules/rds"
  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  app_sg_id      = module.ec2.app_sg_id
  db_password    = var.db_password
  instance_class = "db.t3.micro"
  multi_az       = false
  common_tags    = local.common_tags
}

variable "db_password" { type = string  sensitive = true }
variable "key_name"    { type = string  default = "handson-key" }
variable "my_ip"       { type = string  default = "103.82.209.148/32" }

output "vpc_id"       { value = module.vpc.vpc_id }
output "alb_url"      { value = module.ec2.alb_url }
output "alb_dns_name" { value = module.ec2.alb_dns_name }
output "rds_endpoint" { value = module.rds.endpoint }
```

### modules/vpc/main.tf (key sections)

```hcl
variable "name_prefix" { type = string }
variable "vpc_cidr"    { default = "10.0.0.0/16" }
variable "azs"         { type = list(string) }
variable "common_tags" { type = map(string)  default = {} }

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-public-${count.index}", Tier = "public" })
}

# ... private_app subnets (offset +10), private_db subnets (offset +20)
# ... IGW, EIP, NAT Gateway, public route table, private route table
# ... route table associations for all subnets

output "vpc_id"                 { value = aws_vpc.main.id }
output "public_subnet_ids"      { value = aws_subnet.public[*].id }
output "private_app_subnet_ids" { value = aws_subnet.private_app[*].id }
output "private_db_subnet_ids"  { value = aws_subnet.private_db[*].id }
output "nat_gateway_ip"         { value = aws_eip.nat.public_ip }
```

### modules/ec2/main.tf (key sections)

```hcl
variable "name_prefix"       { type = string }
variable "vpc_id"            { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "app_subnet_ids"    { type = list(string) }
variable "environment"       { type = string }
variable "key_name"          { type = string }
variable "my_ip"             { type = string }
variable "instance_type"     { default = "t3.micro" }
variable "desired_capacity"  { default = 1 }

# ALB SG → allows HTTP/HTTPS from internet
# App SG → allows HTTP from ALB SG only, SSH from my_ip
# ALB → internet-facing, attached to public subnets
# Target Group → HTTP:80, health check /health
# Listener → HTTP:80 → forward to target group
# Launch Template → AL2023 AMI, nginx user_data, app SG
# ASG → desired=1, min=1, max=2, private app subnets, ELB health check

output "alb_dns_name" { value = aws_lb.app.dns_name }
output "alb_url"      { value = "http://${aws_lb.app.dns_name}" }
output "app_sg_id"    { value = aws_security_group.app.id }
output "alb_sg_id"    { value = aws_security_group.alb.id }
```

### modules/rds/main.tf (key sections)

```hcl
variable "name_prefix"    { type = string }
variable "vpc_id"         { type = string }
variable "subnet_ids"     { type = list(string) }
variable "app_sg_id"      { type = string }
variable "db_password"    { type = string  sensitive = true }
variable "instance_class" { default = "db.t3.micro" }
variable "multi_az"       { default = false }

# RDS SG → allows MySQL :3306 from app_sg_id only
# DB Subnet Group → spans private_db subnets
# RDS MySQL 8.0 → db.t3.micro, 20GB gp2, backup_retention=0 (free tier)

output "endpoint"  { value = aws_db_instance.mysql.endpoint }
output "rds_sg_id" { value = aws_security_group.rds.id }
```
