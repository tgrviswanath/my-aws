provider "aws" { region = "us-east-1" }

# Simple resource to demonstrate remote state
resource "aws_s3_bucket" "app_data" {
  bucket = "handson-app-data-${data.aws_caller_identity.current.account_id}"
  tags   = { Project = "handson", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

output "vpc_id"          { value = "demo-vpc-id" }
output "app_bucket_name" { value = aws_s3_bucket.app_data.bucket }
output "account_id"      { value = data.aws_caller_identity.current.account_id }
