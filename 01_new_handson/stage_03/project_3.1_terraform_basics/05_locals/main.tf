# 05_locals/main.tf
# Locals are computed values — like variables but derived from other values.
# Use them to avoid repeating expressions and build consistent naming.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "environment" { default = "dev" }
variable "owner"       { default = "yourname" }

# ─── Locals ───────────────────────────────────────────────────────────────────

locals {
  # Consistent name prefix used across all resources
  name_prefix = "${var.project}-${var.environment}"

  # Common tags applied to every resource
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    CreatedAt   = timestamp()
  }

  # Computed values
  is_production = var.environment == "prod"
  bucket_name   = "${local.name_prefix}-data-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

# ─── Resources using locals ───────────────────────────────────────────────────

resource "aws_s3_bucket" "data" {
  bucket = local.bucket_name
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-data" })
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    # Enable versioning in prod, disable in dev to save costs
    status = local.is_production ? "Enabled" : "Suspended"
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "name_prefix"    { value = local.name_prefix }
output "bucket_name"    { value = aws_s3_bucket.data.bucket }
output "is_production"  { value = local.is_production }
