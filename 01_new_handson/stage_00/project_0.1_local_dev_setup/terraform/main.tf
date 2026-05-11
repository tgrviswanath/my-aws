terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# LocalStack provider — points to localhost instead of real AWS
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3         = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    dynamodb   = "http://localhost:4566"
    apigateway = "http://localhost:4566"
    iam        = "http://localhost:4566"
  }
}

# S3 bucket
resource "aws_s3_bucket" "demo" {
  bucket = "localstack-demo-bucket"
}

# DynamoDB table
resource "aws_dynamodb_table" "users" {
  name         = "Users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }
}

output "s3_bucket_name" {
  value = aws_s3_bucket.demo.bucket
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.users.name
}
