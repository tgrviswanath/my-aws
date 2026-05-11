terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-05", ManagedBy = "terraform" }
}

# ─── ECR Repositories ─────────────────────────────────────────────────────────

resource "aws_ecr_repository" "flask_api" {
  name                 = "${var.project}-flask-api"
  image_tag_mutability = "MUTABLE"   # allows overwriting :latest tag

  image_scanning_configuration {
    scan_on_push = true   # scan every image on push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, { Name = "${var.project}-flask-api" })
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  tags = merge(local.common_tags, { Name = "${var.project}-backend" })
}

# ─── Lifecycle Policies ───────────────────────────────────────────────────────

resource "aws_ecr_lifecycle_policy" "flask_api" {
  repository = aws_ecr_repository.flask_api.name

  policy = jsonencode({
    rules = [
      {
        # Keep last 10 tagged images
        rulePriority = 1
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "release"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      },
      {
        # Delete untagged images after 1 day
        rulePriority = 2
        description  = "Delete untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy     = aws_ecr_lifecycle_policy.flask_api.policy
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}

output "ecr_url"          { value = aws_ecr_repository.flask_api.repository_url }
output "backend_ecr_url"  { value = aws_ecr_repository.backend.repository_url }
output "registry_id"      { value = data.aws_caller_identity.current.account_id }

output "login_command" {
  value = "aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}
