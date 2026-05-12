# Project 5.1 — Single-service Docker Application
# This project runs locally — Terraform creates the ECR repo to push the image to.

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

data "aws_caller_identity" "current" {}

# ECR repository to push the Flask image to
resource "aws_ecr_repository" "flask_api" {
  name                 = "${var.project}-flask-api"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  tags = merge(local.common_tags, { Name = "${var.project}-flask-api" })
}

resource "aws_ecr_lifecycle_policy" "flask_api" {
  repository = aws_ecr_repository.flask_api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection    = { tagStatus = "any" countType = "imageCountMoreThan" countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

output "ecr_url"        { value = aws_ecr_repository.flask_api.repository_url }
output "login_command"  {
  value = "aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}
