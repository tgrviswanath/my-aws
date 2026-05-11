# 01_hello_terraform/main.tf
# Your very first Terraform resource — an S3 bucket.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "us-east-1"
}

# Create an S3 bucket — the simplest possible AWS resource
resource "aws_s3_bucket" "hello" {
  bucket = "hello-terraform-${random_id.suffix.hex}"

  tags = {
    Name        = "hello-terraform"
    Project     = "handson"
    Stage       = "stage-03"
    ManagedBy   = "terraform"
  }
}

# Random suffix so bucket name is globally unique
resource "random_id" "suffix" {
  byte_length = 4
}

# Enable versioning on the bucket
resource "aws_s3_bucket_versioning" "hello" {
  bucket = aws_s3_bucket.hello.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Output the bucket name so we can see it after apply
output "bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.hello.bucket
}

output "bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.hello.arn
}
