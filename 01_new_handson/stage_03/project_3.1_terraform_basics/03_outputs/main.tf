# 03_outputs/main.tf
# Demonstrates output types, sensitive outputs, and using outputs in scripts.

terraform {
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
}

provider "aws" { region = "ap-south-1" }

resource "aws_s3_bucket" "app" {
  bucket = "outputs-demo-${random_id.suffix.hex}"
  tags   = { Project = "handson", Stage = "stage-03" }
}

resource "random_id" "suffix" { byte_length = 4 }

resource "aws_ssm_parameter" "db_password" {
  name  = "/handson/db/password"
  type  = "SecureString"
  value = "super-secret-password-123"
}

# ─── Output Types ─────────────────────────────────────────────────────────────

# Simple string output
output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.app.bucket
}

# Sensitive output — value is hidden in terminal but accessible via -json
output "db_password" {
  description = "Database password (sensitive)"
  value       = aws_ssm_parameter.db_password.value
  sensitive   = true
}

# Object output — multiple values grouped
output "bucket_info" {
  description = "S3 bucket details"
  value = {
    name   = aws_s3_bucket.app.bucket
    arn    = aws_s3_bucket.app.arn
    region = aws_s3_bucket.app.region
  }
}

# Computed output
output "bucket_console_url" {
  description = "Direct link to bucket in AWS Console"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.app.bucket}"
}
