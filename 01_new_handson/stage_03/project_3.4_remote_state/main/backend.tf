# backend.tf — S3 remote state backend
# Run bootstrap/ first to create the bucket and DynamoDB table.
# Replace nothing here — account ID is already set.

terraform {
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "stage-03/project-3.4/main/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
