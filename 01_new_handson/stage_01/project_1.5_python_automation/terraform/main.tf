# Project 1.5 — Python AWS Automation
# Terraform creates the IAM user + S3 bucket used by the Python scripts.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-01", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# S3 bucket for automation scripts to work with
resource "aws_s3_bucket" "automation" {
  bucket = "${var.project}-automation-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "automation-bucket" })
}

resource "aws_s3_bucket_versioning" "automation" {
  bucket = aws_s3_bucket.automation.id
  versioning_configuration { status = "Enabled" }
}

# IAM policy for the Python scripts
resource "aws_iam_policy" "automation" {
  name        = "${var.project}-automation-policy"
  description = "Permissions for Python automation scripts"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                    "s3:ListBucket", "s3:GetBucketVersioning"]
        Resource = [aws_s3_bucket.automation.arn, "${aws_s3_bucket.automation.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:StartInstances", "ec2:StopInstances"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["rds:CreateDBSnapshot", "rds:DescribeDBSnapshots",
                    "rds:DescribeDBInstances"]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

output "bucket_name"   { value = aws_s3_bucket.automation.bucket }
output "policy_arn"    { value = aws_iam_policy.automation.arn }
