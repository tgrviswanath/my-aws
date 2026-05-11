terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "github_org"  { description = "GitHub organization or username" }
variable "github_repo" { description = "GitHub repository name" }

locals {
  github_repo_full = "${var.github_org}/${var.github_repo}"
  oidc_provider    = "token.actions.githubusercontent.com"
  common_tags      = { Project = "handson", Stage = "stage-06", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── OIDC Provider ────────────────────────────────────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://${local.oidc_provider}"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub's OIDC thumbprint (stable — rarely changes)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = local.common_tags
}

# ─── Helper: Trust Policy Builder ────────────────────────────────────────────

locals {
  oidc_arn = aws_iam_openid_connect_provider.github.arn

  # Trust policy for any ref in the repo (CI — pull requests)
  trust_any_ref = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider}:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "${local.oidc_provider}:sub" = "repo:${local.github_repo_full}:*"
        }
      }
    }]
  })

  # Trust policy scoped to main branch only (CD)
  trust_main_only = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider}:aud" = "sts.amazonaws.com"
          "${local.oidc_provider}:sub" = "repo:${local.github_repo_full}:ref:refs/heads/main"
        }
      }
    }]
  })

  # Trust policy scoped to production environment
  trust_production = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider}:aud" = "sts.amazonaws.com"
          "${local.oidc_provider}:sub" = "repo:${local.github_repo_full}:environment:production"
        }
      }
    }]
  })
}

# ─── CI Role (Pull Requests — read only) ─────────────────────────────────────

resource "aws_iam_role" "github_ci" {
  name               = "github-ci-role"
  assume_role_policy = local.trust_any_ref
  tags               = merge(local.common_tags, { Purpose = "github-ci" })
}

resource "aws_iam_role_policy" "github_ci" {
  name = "ci-permissions"
  role = aws_iam_role.github_ci.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Read ECR (for build cache)
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"]
        Resource = "*"
      },
      {
        # Describe ECS (for status checks)
        Effect   = "Allow"
        Action   = ["ecs:DescribeServices", "ecs:DescribeTaskDefinition",
                    "ecs:ListTasks", "ecs:DescribeTasks"]
        Resource = "*"
      }
    ]
  })
}

# ─── CD Role (Main branch — deploy) ──────────────────────────────────────────

resource "aws_iam_role" "github_cd" {
  name               = "github-cd-role"
  assume_role_policy = local.trust_main_only
  tags               = merge(local.common_tags, { Purpose = "github-cd" })
}

resource "aws_iam_role_policy" "github_cd" {
  name = "cd-permissions"
  role = aws_iam_role.github_cd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Push to ECR
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload", "ecr:PutImage"]
        Resource = "*"
      },
      {
        # Deploy to ECS
        Effect   = "Allow"
        Action   = ["ecs:RegisterTaskDefinition", "ecs:UpdateService",
                    "ecs:DescribeServices", "ecs:DescribeTaskDefinition",
                    "ecs:ListTasks", "ecs:DescribeTasks"]
        Resource = "*"
      },
      {
        # Pass IAM roles to ECS tasks
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/handson-*"
      }
    ]
  })
}

# ─── Terraform Role (main + environments) ────────────────────────────────────

resource "aws_iam_role" "github_terraform" {
  name               = "github-terraform-role"
  assume_role_policy = local.trust_production
  tags               = merge(local.common_tags, { Purpose = "github-terraform" })
}

resource "aws_iam_role_policy_attachment" "github_terraform" {
  role       = aws_iam_role.github_terraform.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "role_arns" {
  value = {
    ci        = aws_iam_role.github_ci.arn
    cd        = aws_iam_role.github_cd.arn
    terraform = aws_iam_role.github_terraform.arn
  }
}

output "oidc_provider_arn" { value = aws_iam_openid_connect_provider.github.arn }
