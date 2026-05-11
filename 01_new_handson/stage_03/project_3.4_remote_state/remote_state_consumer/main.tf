terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

# Read outputs from another Terraform config's remote state
data "terraform_remote_state" "main" {
  backend = "s3"
  config = {
    bucket = "handson-terraform-state-ACCOUNTID"
    key    = "stage-03/project-3.4/terraform.tfstate"
    region = "us-east-1"
  }
}

# Use the remote state outputs
output "vpc_id_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.vpc_id
}

output "app_bucket_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.app_bucket_name
}
