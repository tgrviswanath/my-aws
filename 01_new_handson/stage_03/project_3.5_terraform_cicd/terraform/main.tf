# Project 3.5 — Terraform CI/CD Pipeline
# Infrastructure managed by GitHub Actions CI/CD.
# This file is applied automatically on merge to main.
# Backend is configured in backend.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = var.region }

variable "region" { default = "ap-south-1" }
variable "project" { default = "handson" }
variable "environment" { default = "dev" }

locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Stage       = "stage-03"
    ManagedBy   = "terraform-cicd"
    Pipeline    = "github-actions"
  }
}

data "aws_caller_identity" "current" {}

# ─── Application S3 Bucket (managed by CI/CD) ────────────────────────────────

resource "aws_s3_bucket" "app" {
  bucket = "${var.project}-cicd-demo-${var.environment}-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "${var.project}-cicd-demo" })
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket                  = aws_s3_bucket.app.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── SNS Topic for pipeline notifications ────────────────────────────────────

resource "aws_sns_topic" "pipeline_alerts" {
  name = "${var.project}-pipeline-alerts"
  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "bucket_name" { value = aws_s3_bucket.app.bucket }
output "bucket_arn" { value = aws_s3_bucket.app.arn }
output "account_id" { value = data.aws_caller_identity.current.account_id }
output "sns_topic_arn" { value = aws_sns_topic.pipeline_alerts.arn }
output "environment" { value = var.environment }

# pipeline test trigger — feature/test-pipeline branch
