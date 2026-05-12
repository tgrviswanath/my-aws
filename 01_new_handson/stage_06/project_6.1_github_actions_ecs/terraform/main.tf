# Project 6.1 — GitHub Actions + ECS CI/CD
# Terraform creates the OIDC provider and IAM role for GitHub Actions.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "github_org"  { description = "GitHub username or org" }
variable "github_repo" { description = "GitHub repository name" }

locals {
  oidc_provider = "token.actions.githubusercontent.com"
  common_tags   = { Project = var.project, Stage = "stage-06", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── OIDC Provider ────────────────────────────────────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://${local.oidc_provider}"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  tags            = local.common_tags
}

# ─── GitHub Actions IAM Role ──────────────────────────────────────────────────

resource "aws_iam_role" "github_actions" {
  name = "${var.project}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "${local.oidc_provider}:aud" = "sts.amazonaws.com" }
        StringLike   = { "${local.oidc_provider}:sub" = "repo:${var.github_org}/${var.github_repo}:*" }
      }
    }]
  })

  tags = merge(local.common_tags, { Purpose = "github-actions-cicd" })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "cicd-permissions"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload", "ecr:PutImage",
                    "ecr:DescribeImages", "ecr:ListImages"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:RegisterTaskDefinition", "ecs:UpdateService",
                    "ecs:DescribeServices", "ecs:DescribeTaskDefinition",
                    "ecs:ListTasks", "ecs:DescribeTasks"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-*"
      }
    ]
  })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "role_arn"          { value = aws_iam_role.github_actions.arn }
output "oidc_provider_arn" { value = aws_iam_openid_connect_provider.github.arn }
output "github_secret_value" {
  description = "Add this as AWS_ROLE_ARN secret in GitHub"
  value       = aws_iam_role.github_actions.arn
}
