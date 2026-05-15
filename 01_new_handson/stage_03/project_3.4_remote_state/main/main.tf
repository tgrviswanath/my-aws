# Project 3.4 — Terraform Remote State
# Main infrastructure config — uses the S3 remote backend defined in backend.tf.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-03", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Application S3 Bucket ────────────────────────────────────────────────────

resource "aws_s3_bucket" "app_data" {
  bucket = "${var.project}-app-data-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "${var.project}-app-data" })
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_data" {
  bucket = aws_s3_bucket.app_data.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket                  = aws_s3_bucket.app_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── Outputs (readable by other configs via terraform_remote_state) ───────────

output "app_bucket_name" { value = aws_s3_bucket.app_data.bucket }
output "app_bucket_arn"  { value = aws_s3_bucket.app_data.arn }
output "account_id"      { value = data.aws_caller_identity.current.account_id }
output "region"          { value = var.region }
