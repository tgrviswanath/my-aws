# bootstrap/main.tf
# Creates the S3 bucket and DynamoDB table needed for remote state.
# This config itself uses LOCAL state (chicken-and-egg problem).
# Run this ONCE, then never touch it again.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

data "aws_caller_identity" "current" {}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  bucket_name  = "handson-terraform-state-${local.account_id}"
  table_name   = "handson-terraform-locks"
}

# ─── S3 State Bucket ──────────────────────────────────────────────────────────

resource "aws_s3_bucket" "state" {
  bucket = local.bucket_name

  # Prevent accidental deletion
  lifecycle { prevent_destroy = true }

  tags = { Name = "terraform-state", ManagedBy = "terraform", Purpose = "state" }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── DynamoDB Lock Table ──────────────────────────────────────────────────────

resource "aws_dynamodb_table" "locks" {
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"   # MUST be exactly "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = { Name = "terraform-locks", ManagedBy = "terraform", Purpose = "state-locking" }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "state_bucket_name" { value = aws_s3_bucket.state.bucket }
output "lock_table_name"   { value = aws_dynamodb_table.locks.name }
output "backend_config" {
  value = <<-EOT
    # Add this to your terraform block:
    backend "s3" {
      bucket         = "${aws_s3_bucket.state.bucket}"
      key            = "YOUR_PROJECT/terraform.tfstate"
      region         = "us-east-1"
      dynamodb_table = "${aws_dynamodb_table.locks.name}"
      encrypt        = true
    }
  EOT
}
