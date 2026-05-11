# target-account/main.tf
# Deploy this in EACH target account (dev, staging, prod)
# Creates a cross-account role that the management account can assume

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

variable "source_account_id" {
  description = "AWS account ID of the management/CI account"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "source_role_name" {
  description = "Name of the role in the source account that will assume this role"
  default     = "github-cd-role"
}

# ─── Cross-account Deploy Role ────────────────────────────────────────────────

resource "aws_iam_role" "deploy" {
  name = "handson-${var.environment}-deploy-role"

  # Trust the management account's CI role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${var.source_account_id}:role/${var.source_role_name}"
      }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = "handson-${var.environment}-deploy"
        }
      }
    }]
  })

  tags = {
    Environment = var.environment
    Purpose     = "cross-account-deploy"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "deploy" {
  name = "deploy-permissions"
  role = aws_iam_role.deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices",
                    "ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition",
                    "ecs:ListTasks", "ecs:DescribeTasks"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = "arn:aws:iam::*:role/handson-*"
      }
    ]
  })
}

output "deploy_role_arn" { value = aws_iam_role.deploy.arn }
