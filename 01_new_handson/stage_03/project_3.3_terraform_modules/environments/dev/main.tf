terraform {
  required_providers {
    aws = { 
      source = "hashicorp/aws" 
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

# ─── VPC Module ───────────────────────────────────────────────────────────────

module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.0.0.0/16"
  azs         = ["ap-south-1a", "ap-south-1b"]
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
  instance_type      = "t3.micro"   # small for dev
  desired_capacity   = 1            # cost saving
  min_size           = 1
  max_size           = 2
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
  instance_class = "db.t3.micro"  # free tier
  multi_az       = false          # no HA in dev
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
