provider "aws" { region = "us-east-1" }

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "app" {
  bucket = "handson-cicd-demo-${data.aws_caller_identity.current.account_id}"
  tags   = { Project = "handson", ManagedBy = "terraform-cicd", Stage = "stage-03" }
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id
  versioning_configuration { status = "Enabled" }
}

output "bucket_name" { value = aws_s3_bucket.app.bucket }
output "account_id"  { value = data.aws_caller_identity.current.account_id }
