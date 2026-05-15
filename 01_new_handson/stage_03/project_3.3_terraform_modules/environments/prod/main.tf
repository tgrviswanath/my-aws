terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "ap-south-1" }

locals {
  env         = "prod"
  name_prefix = "handson-${local.env}"
  common_tags = {
    Project     = "handson"
    Environment = local.env
    ManagedBy   = "terraform"
    Stage       = "stage-03"
  }
}

# ─── VPC Module ───────────────────────────────────────────────────────────────

module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.2.0.0/16"          # different CIDR — no overlap with dev/qa
  azs         = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]  # 3 AZs for HA
  common_tags = local.common_tags
}

# ─── EC2 Module (ALB + ASG) ───────────────────────────────────────────────────

module "ec2" {
  source             = "../../modules/ec2"
  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  app_subnet_ids     = module.vpc.private_app_subnet_ids
  environment        = local.env
  key_name           = var.key_name
  my_ip              = var.my_ip
  instance_type      = "t3.small"   # larger for prod
  desired_capacity   = 2            # HA — 2 instances across AZs
  min_size           = 2
  max_size           = 4
  common_tags        = local.common_tags
}

# ─── RDS Module ───────────────────────────────────────────────────────────────

module "rds" {
  source         = "../../modules/rds"
  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  app_sg_id      = module.ec2.app_sg_id
  db_password    = var.db_password
  instance_class = "db.t3.small"  # larger for prod
  multi_az       = true           # HA in prod
  common_tags    = local.common_tags
}

# ─── Variables ────────────────────────────────────────────────────────────────

variable "db_password" {
  type      = string
  sensitive = true
}

variable "key_name" {
  type        = string
  default     = "handson-key"
  description = "EC2 key pair name"
}

variable "my_ip" {
  type        = string
  default     = "103.82.209.148/32"
  description = "Your IP for SSH access"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "vpc_id"       { value = module.vpc.vpc_id }
output "alb_url"      { value = module.ec2.alb_url }
output "alb_dns_name" { value = module.ec2.alb_dns_name }
output "rds_endpoint" { value = module.rds.endpoint }
