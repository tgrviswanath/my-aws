# Project 10.5 — Production-grade Microservices Platform
# This is the capstone project — it composes all previous modules.
# Uses Terraform module calls to assemble the full platform.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }

  # Use remote state from Project 3.4
  backend "s3" {
    bucket         = "handson-terraform-state-ACCOUNTID"
    key            = "stage-10/project-10.5/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "environment" { default = "prod" }
variable "db_password" { type = string sensitive = true }
variable "alert_email" { description = "Email for all alerts" }

locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    Stage       = "stage-10"
  }
}

# ─── Reference outputs from previous stages via remote state ──────────────────

data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = {
    bucket = "handson-terraform-state-ACCOUNTID"
    key    = "stage-02/project-2.1/terraform.tfstate"
    region = "us-east-1"
  }
}

data "terraform_remote_state" "ecr" {
  backend = "s3"
  config = {
    bucket = "handson-terraform-state-ACCOUNTID"
    key    = "stage-05/project-5.3/terraform.tfstate"
    region = "us-east-1"
  }
}

# ─── Platform-level SNS topic for all alerts ─────────────────────────────────

resource "aws_sns_topic" "platform_alerts" {
  name = "${local.name_prefix}-platform-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "platform_email" {
  topic_arn = aws_sns_topic.platform_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── Cost budget for the full platform ───────────────────────────────────────

resource "aws_budgets_budget" "platform" {
  name         = "${local.name_prefix}-platform-budget"
  budget_type  = "COST"
  limit_amount = "500"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "platform_summary" {
  value = {
    vpc_id          = data.terraform_remote_state.vpc.outputs.vpc_id
    ecr_url         = data.terraform_remote_state.ecr.outputs.ecr_url
    sns_alerts_arn  = aws_sns_topic.platform_alerts.arn
    budget_name     = aws_budgets_budget.platform.name
  }
}

output "next_steps" {
  value = <<-EOT
    Platform foundation deployed. Next steps:
    1. Deploy ECS services: cd stage_05/project_5.4_ecs_fargate/terraform && terraform apply
    2. Deploy API Gateway: cd stage_04/project_4.2_api_auth/terraform && terraform apply
    3. Deploy WAF: cd stage_08/project_8.2_waf/terraform && terraform apply
    4. Deploy monitoring: cd stage_07/project_7.1_cloudwatch/terraform && terraform apply
    5. Deploy data pipeline: cd stage_09/project_9.3_kinesis_streaming/terraform && terraform apply
    6. Set up CI/CD: configure GitHub Actions with OIDC role
  EOT
}
