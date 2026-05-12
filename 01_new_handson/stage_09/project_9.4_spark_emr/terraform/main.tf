# Project 9.4 — Spark Processing on EMR Serverless

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "data_lake_bucket" { description = "Data lake S3 bucket name" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── EMR Serverless Application ───────────────────────────────────────────────

resource "aws_emrserverless_application" "spark" {
  name          = "${var.project}-spark"
  release_label = "emr-6.15.0"
  type          = "SPARK"

  initial_capacity {
    initial_capacity_type = "Driver"
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = "2 vCPU"
        memory = "4 GB"
      }
    }
  }

  maximum_capacity {
    cpu    = "20 vCPU"
    memory = "40 GB"
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }

  tags = merge(local.common_tags, { Name = "${var.project}-spark" })
}

# ─── IAM Role for EMR Serverless ──────────────────────────────────────────────

resource "aws_iam_role" "emr" {
  name = "${var.project}-emr-serverless-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "emr-serverless.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "emr_s3" {
  name = "s3-access"
  role = aws_iam_role.emr.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.data_lake_bucket}",
          "arn:aws:s3:::${var.data_lake_bucket}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["glue:GetDatabase", "glue:GetTable", "glue:GetPartitions",
                    "glue:CreateTable", "glue:UpdateTable"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_logs" {
  role       = aws_iam_role.emr.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# ─── Upload Spark script to S3 ────────────────────────────────────────────────

resource "aws_s3_object" "spark_script" {
  bucket = var.data_lake_bucket
  key    = "scripts/spark_job.py"
  source = "${path.module}/../src/spark_job.py"
  etag   = filemd5("${path.module}/../src/spark_job.py")
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "application_id"  { value = aws_emrserverless_application.spark.id }
output "emr_role_arn"    { value = aws_iam_role.emr.arn }
output "spark_script_s3" { value = "s3://${var.data_lake_bucket}/scripts/spark_job.py" }

output "submit_command" {
  value = <<-EOT
    aws emr-serverless start-job-run \
      --application-id ${aws_emrserverless_application.spark.id} \
      --execution-role-arn ${aws_iam_role.emr.arn} \
      --job-driver '{"sparkSubmit":{"entryPoint":"s3://${var.data_lake_bucket}/scripts/spark_job.py","entryPointArguments":["--input","s3://${var.data_lake_bucket}/raw/orders/","--output","s3://${var.data_lake_bucket}/processed/spark/"]}}'
  EOT
}
