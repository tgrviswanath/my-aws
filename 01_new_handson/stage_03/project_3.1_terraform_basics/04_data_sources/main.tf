# 04_data_sources/main.tf
# Data sources READ existing AWS resources without creating them.
# Use them to reference resources not managed by this Terraform config.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

# ─── Data Sources ─────────────────────────────────────────────────────────────

# Get the latest Amazon Linux 2023 AMI — no hardcoded AMI IDs
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Get the default VPC (already exists in every account)
data "aws_vpc" "default" {
  default = true
}

# Get subnets in the default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Get an existing S3 bucket (not managed by this config)
# data "aws_s3_bucket" "existing" {
#   bucket = "my-existing-bucket"
# }

# ─── Use data sources in resources ───────────────────────────────────────────

resource "aws_instance" "example" {
  # Use data source instead of hardcoded AMI ID
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  # Use data source for subnet
  subnet_id = data.aws_subnets.default.ids[0]

  tags = {
    Name    = "data-source-demo"
    Project = "handson"
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "ami_id"          { value = data.aws_ami.amazon_linux.id }
output "ami_name"        { value = data.aws_ami.amazon_linux.name }
output "account_id"      { value = data.aws_caller_identity.current.account_id }
output "current_region"  { value = data.aws_region.current.name }
output "default_vpc_id"  { value = data.aws_vpc.default.id }
output "default_subnets" { value = data.aws_subnets.default.ids }
