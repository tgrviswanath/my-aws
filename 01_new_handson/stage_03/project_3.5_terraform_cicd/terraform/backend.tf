# backend.tf — S3 remote state backend for project 3.5
# Reuses the S3 bucket and DynamoDB table from project 3.4 bootstrap.
# Run bootstrap/ from project 3.4 first if not already done.

terraform {
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "stage-03/project-3.5/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
