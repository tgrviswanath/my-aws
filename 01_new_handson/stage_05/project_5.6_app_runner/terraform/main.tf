terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"        { default = "us-east-1" }
variable "project"       { default = "handson" }
variable "ecr_image_url" { description = "ECR image URL with tag" }

locals {
  name_prefix = "${var.project}-app-runner"
  common_tags = { Project = var.project, Stage = "stage-05", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── IAM Role for App Runner to access ECR ────────────────────────────────────

resource "aws_iam_role" "app_runner_ecr" {
  name = "${local.name_prefix}-ecr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "app_runner_ecr" {
  role       = aws_iam_role.app_runner_ecr.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# ─── App Runner Service ───────────────────────────────────────────────────────

resource "aws_apprunner_service" "app" {
  service_name = local.name_prefix

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_ecr.arn
    }

    image_repository {
      image_identifier      = var.ecr_image_url
      image_repository_type = "ECR"

      image_configuration {
        port = "5000"
        runtime_environment_variables = {
          APP_ENV     = "production"
          APP_VERSION = "1.0.0"
        }
      }
    }

    # Auto-deploy when new image is pushed to ECR
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu    = "0.25 vCPU"
    memory = "0.5 GB"
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = merge(local.common_tags, { Name = local.name_prefix })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "app_runner_url" { value = "https://${aws_apprunner_service.app.service_url}" }
output "service_arn"    { value = aws_apprunner_service.app.arn }
