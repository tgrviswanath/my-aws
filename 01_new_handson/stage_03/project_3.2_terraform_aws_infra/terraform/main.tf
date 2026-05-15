# Project 3.2 — Terraform AWS Infrastructure
# Full multi-tier infrastructure: VPC + EC2 + ALB + RDS
#
# Resources are split across files for clarity:
#   versions.tf  — required_providers, required_version
#   variables.tf — all input variables
#   locals.tf    — name_prefix, common_tags
#   vpc.tf       — VPC, subnets, IGW, NAT, route tables
#   ec2.tf       — security groups, ALB, launch template, ASG
#   rds.tf       — RDS MySQL
#   outputs.tf   — all outputs

provider "aws" { region = var.region }
