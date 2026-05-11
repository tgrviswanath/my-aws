terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }

  # Remote state backend — replace ACCOUNTID with your AWS account ID
  # Run bootstrap/ first to create the bucket and table
  backend "s3" {
    bucket         = "handson-terraform-state-ACCOUNTID"
    key            = "stage-03/project-3.4/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
