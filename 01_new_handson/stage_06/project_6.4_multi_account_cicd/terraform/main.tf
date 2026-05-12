# Project 6.4 — Multi-account CI/CD Pipeline
# This is the management account Terraform — creates the OIDC role
# that can assume roles in target accounts.
# Run target-account/main.tf in each target account separately.

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

# ─── OIDC Provider (management account) ──────────────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://${local.oidc_provider}"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  tags            = local.common_tags
}

# ─── Management account CI role (can assume roles in target accounts) ─────────

resource "aws_iam_role" "github_cd" {
  name = "${var.project}-github-cd-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "${local.oidc_provider}:aud" = "sts.amazonaws.com" }
        StringEquals = { "${local.oidc_provider}:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main" }
      }
    }]
  })

  tags = merge(local.common_tags, { Purpose = "multi-account-cicd" })
}

resource "aws_iam_role_policy" "github_cd_assume" {
  name = "assume-target-account-roles"
  role = aws_iam_role.github_cd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sts:AssumeRole"]
        Resource = [
          # Add target account role ARNs here after deploying target-account/main.tf
          "arn:aws:iam::*:role/${var.project}-*-deploy-role"
        ]
      },
      {
        # ECR in management account (shared registry)
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload", "ecr:PutImage"]
        Resource = "*"
      }
    ]
  })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "github_cd_role_arn"   { value = aws_iam_role.github_cd.arn }
output "oidc_provider_arn"    { value = aws_iam_openid_connect_provider.github.arn }
output "account_id"           { value = data.aws_caller_identity.current.account_id }

output "next_step" {
  value = "Deploy target-account/main.tf in each target account (dev, staging, prod) with source_account_id=${data.aws_caller_identity.current.account_id}"
}
