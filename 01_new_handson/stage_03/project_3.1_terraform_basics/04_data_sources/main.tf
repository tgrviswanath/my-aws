# 04_data_sources/main.tf
# Data sources READ existing AWS resources without creating them.
# Use them to reference resources not managed by this Terraform config.
# Cost: $0 — data sources only read, never create resources.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "ap-south-1" }

# ─── Data Source 1: Latest Amazon Linux 2023 AMI ─────────────────────────────
# No more hardcoded AMI IDs — always gets the latest automatically

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

# ─── Data Source 2: Current AWS Account & Region ─────────────────────────────
# Useful for building ARNs and bucket names dynamically

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ─── Data Source 3: Default VPC ──────────────────────────────────────────────
# Every AWS account has a default VPC — read it without creating one

data "aws_vpc" "default" {
  default = true
}

# ─── Data Source 4: Subnets in Default VPC ───────────────────────────────────

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ─── Data Source 5: Availability Zones ───────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

# ─── Outputs — show what data sources discovered ─────────────────────────────

output "ami_id" {
  description = "Latest Amazon Linux 2023 AMI ID in ap-south-1"
  value       = data.aws_ami.amazon_linux.id
}

output "ami_name" {
  description = "Full AMI name"
  value       = data.aws_ami.amazon_linux.name
}

output "account_id" {
  description = "Current AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "current_region" {
  description = "Current AWS region"
  value       = data.aws_region.current.name
}

output "default_vpc_id" {
  description = "Default VPC ID"
  value       = data.aws_vpc.default.id
}

output "default_vpc_cidr" {
  description = "Default VPC CIDR block"
  value       = data.aws_vpc.default.cidr_block
}

output "default_subnet_ids" {
  description = "All subnet IDs in the default VPC"
  value       = data.aws_subnets.default.ids
}

output "availability_zones" {
  description = "Available AZs in ap-south-1"
  value       = data.aws_availability_zones.available.names
}

output "useful_for_ec2" {
  description = "How you would use these in an EC2 resource"
  value       = "ami = ${data.aws_ami.amazon_linux.id} | subnet_id = ${data.aws_subnets.default.ids[0]}"
}
