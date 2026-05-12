# 02_variables/main.tf
# Demonstrates all variable types and usage patterns.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

# ─── Variable Types ───────────────────────────────────────────────────────────

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
  # No default — will prompt at runtime or must be passed via -var or .tfvars
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "Environment must be dev, qa, or prod."
  }
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "handson"
    Stage     = "stage-03"
    ManagedBy = "terraform"
  }
}

variable "allowed_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default     = ["https://example.com"]
}

# ─── Resources ────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "main" {
  bucket = "${var.environment}-${var.bucket_name}"
  tags   = merge(var.tags, { Environment = var.environment })
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "bucket_name"   { value = aws_s3_bucket.main.bucket }
output "bucket_arn"    { value = aws_s3_bucket.main.arn }
output "environment"   { value = var.environment }
