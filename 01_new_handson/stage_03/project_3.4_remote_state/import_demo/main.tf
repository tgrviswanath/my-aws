# import_demo/main.tf
# Phase 7 — terraform import demo
#
# Scenario: the bucket "handson-app-data-495331821583" already exists in AWS
# (created by main/). This config has never managed it.
# We import it so Terraform can start tracking and managing it.
#
# Steps:
#   1. terraform init
#   2. terraform import aws_s3_bucket.imported handson-app-data-495331821583
#   3. terraform plan  →  should show no changes if config matches reality

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = "us-east-1" }

# ─── Resource block describing the existing bucket ────────────────────────────
# This must match what actually exists in AWS.
# After import, terraform plan should show 0 changes.

resource "aws_s3_bucket" "imported" {
  bucket = "handson-app-data-495331821583"

  tags = {
    ManagedBy = "terraform"
    Name      = "handson-app-data"
    Project   = "handson"
    Stage     = "stage-03"
  }
}

resource "aws_s3_bucket_versioning" "imported" {
  bucket = aws_s3_bucket.imported.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "imported" {
  bucket = aws_s3_bucket.imported.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "imported" {
  bucket                  = aws_s3_bucket.imported.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "imported_bucket_name" { value = aws_s3_bucket.imported.bucket }
output "imported_bucket_arn"  { value = aws_s3_bucket.imported.arn }
