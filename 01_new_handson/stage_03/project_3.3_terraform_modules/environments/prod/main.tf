terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

locals {
  env         = "prod"
  name_prefix = "handson-${local.env}"
  common_tags = {
    Project     = "handson"
    Environment = local.env
    ManagedBy   = "terraform"
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.1.0.0/16"   # different CIDR from dev — no overlap
  azs         = ["us-east-1a", "us-east-1b", "us-east-1c"]  # 3 AZs in prod
  common_tags = local.common_tags
}

module "rds" {
  source         = "../../modules/rds"
  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_db_subnet_ids
  app_sg_id      = aws_security_group.app.id
  db_password    = var.db_password
  instance_class = "db.t3.small"  # larger for prod
  multi_az       = true           # HA in prod
  common_tags    = local.common_tags
}

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
