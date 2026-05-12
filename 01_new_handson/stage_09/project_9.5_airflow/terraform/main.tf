# Project 9.5 — Airflow Data Orchestration
# Creates S3 bucket for MWAA DAGs and requirements.
# Note: MWAA itself is very expensive (~$670/month) — use local Docker for learning.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── S3 Bucket for DAGs ───────────────────────────────────────────────────────

resource "aws_s3_bucket" "mwaa" {
  bucket = "${var.project}-mwaa-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "mwaa-dags" })
}

resource "aws_s3_bucket_versioning" "mwaa" {
  bucket = aws_s3_bucket.mwaa.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "mwaa" {
  bucket                  = aws_s3_bucket.mwaa.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload DAG file
resource "aws_s3_object" "daily_pipeline_dag" {
  bucket = aws_s3_bucket.mwaa.id
  key    = "dags/daily_pipeline.py"
  source = "${path.module}/../dags/daily_pipeline.py"
  etag   = filemd5("${path.module}/../dags/daily_pipeline.py")
}

# ─── IAM Role for MWAA ────────────────────────────────────────────────────────

resource "aws_iam_role" "mwaa" {
  name = "${var.project}-mwaa-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"] }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "mwaa" {
  name = "mwaa-policy"
  role = aws_iam_role.mwaa.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject*", "s3:GetBucket*", "s3:List*"]
        Resource = [aws_s3_bucket.mwaa.arn, "${aws_s3_bucket.mwaa.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                    "logs:GetLogEvents", "logs:GetLogRecord", "logs:DescribeLogGroups"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["glue:StartJobRun", "glue:GetJobRun", "glue:GetJob"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = "*"
      }
    ]
  })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "mwaa_bucket"         { value = aws_s3_bucket.mwaa.bucket }
output "mwaa_role_arn"       { value = aws_iam_role.mwaa.arn }
output "dag_s3_path"         { value = "s3://${aws_s3_bucket.mwaa.bucket}/dags/" }

output "local_dev_command" {
  description = "Run Airflow locally with Docker (recommended for learning)"
  value       = "docker compose up -d  # see dags/ folder for DAG files"
}
