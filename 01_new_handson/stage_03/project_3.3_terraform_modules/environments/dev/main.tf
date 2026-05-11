terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

locals {
  env         = "dev"
  name_prefix = "handson-${local.env}"
  common_tags = {
    Project     = "handson"
    Environment = local.env
    ManagedBy   = "terraform"
  }
}

# ─── VPC Module ───────────────────────────────────────────────────────────────

module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.0.0.0/16"
  azs         = ["us-east-1a", "us-east-1b"]
  common_tags = local.common_tags
}

# ─── RDS Module ───────────────────────────────────────────────────────────────

module "rds" {
  source         = "../../modules/rds"
  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  app_sg_id      = aws_security_group.app.id
  db_password    = var.db_password
  instance_class = "db.t3.micro"  # small for dev
  multi_az       = false          # no HA in dev
  common_tags    = local.common_tags
}

# App security group (simplified — full version in ec2 module)
resource "aws_security_group" "app" {
  name   = "${local.name_prefix}-app-sg"
  vpc_id = module.vpc.vpc_id
  ingress { from_port = 80 to_port = 80 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0  to_port = 0  protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app-sg" })
}

variable "db_password" { type = string sensitive = true }

output "vpc_id"       { value = module.vpc.vpc_id }
output "rds_endpoint" { value = module.rds.endpoint }
