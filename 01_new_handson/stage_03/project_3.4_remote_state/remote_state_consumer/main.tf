terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = "us-east-1" }

# Read outputs from another Terraform config's remote state
data "terraform_remote_state" "main" {
  backend = "s3"
  config = {
    bucket = "handson-terraform-state-495331821583"
    key    = "stage-03/project-3.4/main/terraform.tfstate"
    region = "us-east-1"
  }
}

# Use the remote state outputs
# Reads outputs exported by main/main.tf
output "app_bucket_name_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.app_bucket_name
}

output "app_bucket_arn_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.app_bucket_arn
}

output "account_id_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.account_id
}

output "region_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.region
}
