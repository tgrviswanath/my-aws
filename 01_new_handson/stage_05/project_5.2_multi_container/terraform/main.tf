# Project 5.2 — Multi-container Application
# Terraform creates ECR repos for backend and frontend images.

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
  repos       = ["backend", "frontend"]
}

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "app" {
  for_each             = toset(local.repos)
  name                 = "${var.project}-${each.key}"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  tags = merge(local.common_tags, { Name = "${var.project}-${each.key}" })
}

resource "aws_ecr_lifecycle_policy" "app" {
  for_each   = toset(local.repos)
  repository = aws_ecr_repository.app[each.key].name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection    = { tagStatus = "any" countType = "imageCountMoreThan" countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

output "ecr_urls" { value = { for k, r in aws_ecr_repository.app : k => r.repository_url } }
