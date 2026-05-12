# Project 0.3 — Git & GitHub Workflow
# Terraform creates an S3 bucket to store project artifacts (screenshots, docs).
# Also creates the IAM user for GitHub Actions CI/CD (used in later projects).

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-00", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# S3 bucket for project artifacts (screenshots, architecture diagrams)
resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project}-artifacts-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "${var.project}-artifacts" })
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM user for GitHub Actions (used in project 6.1 and beyond)
# NOTE: In production, use OIDC instead of IAM user keys (see project 6.2)
resource "aws_iam_user" "github_actions" {
  name = "${var.project}-github-actions"
  tags = merge(local.common_tags, { Purpose = "github-actions-ci-cd" })
}

resource "aws_iam_user_policy" "github_actions" {
  name = "github-actions-minimal"
  user = aws_iam_user.github_actions.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*"
        ]
      }
    ]
  })
}

output "artifacts_bucket" { value = aws_s3_bucket.artifacts.bucket }
output "github_actions_user" { value = aws_iam_user.github_actions.name }
output "note" {
  value = "For CI/CD, prefer OIDC (project 6.2) over IAM user access keys"
}
