# migration_demo/main.tf
# Phase 6 — State Migration Demo
# Step 1: This config starts with LOCAL state (no backend block).
# Step 2: We add the backend block and run terraform init to migrate.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Step 2: Backend block added — running terraform init will prompt to migrate
  # local state (terraform.tfstate) up to S3.
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "stage-03/project-3.4/migration-demo/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}

provider "aws" { region = "us-east-1" }

data "aws_caller_identity" "current" {}

# A simple SSM parameter — lightweight resource, no cost
resource "aws_ssm_parameter" "demo" {
  name  = "/handson/migration-demo/message"
  type  = "String"
  value = "hello from local state"

  tags = { ManagedBy = "terraform", Purpose = "migration-demo" }
}

output "parameter_name" { value = aws_ssm_parameter.demo.name }
output "account_id"     { value = data.aws_caller_identity.current.account_id }
