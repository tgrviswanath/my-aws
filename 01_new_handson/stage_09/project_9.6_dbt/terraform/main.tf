# Project 9.6 — dbt Transformation Pipeline
# Terraform creates the Athena workgroup and S3 staging bucket for dbt.
# dbt itself runs locally (dbt Core is free and open source).

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

# ─── S3 bucket for dbt staging results ───────────────────────────────────────

resource "aws_s3_bucket" "dbt_staging" {
  bucket = "${var.project}-dbt-staging-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "dbt-staging" })
}

resource "aws_s3_bucket_lifecycle_configuration" "dbt_staging" {
  bucket = aws_s3_bucket.dbt_staging.id
  rule {
    id     = "expire-staging"
    status = "Enabled"
    expiration { days = 7 }
  }
}

# ─── Athena Workgroup for dbt ─────────────────────────────────────────────────

resource "aws_athena_workgroup" "dbt" {
  name = "${var.project}-dbt"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.dbt_staging.bucket}/dbt/"
    }
    bytes_scanned_cutoff_per_query = 1073741824  # 1 GB limit per query
    enforce_workgroup_configuration = true
  }

  tags = local.common_tags
}

# ─── IAM Policy for dbt to access Athena + Glue + S3 ─────────────────────────

resource "aws_iam_policy" "dbt" {
  name        = "${var.project}-dbt-policy"
  description = "Permissions for dbt to run against Athena"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["athena:StartQueryExecution", "athena:GetQueryExecution",
                    "athena:GetQueryResults", "athena:StopQueryExecution",
                    "athena:ListWorkGroups", "athena:GetWorkGroup"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["glue:GetDatabase", "glue:GetDatabases", "glue:GetTable",
                    "glue:GetTables", "glue:GetPartition", "glue:GetPartitions",
                    "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
                    "glue:CreatePartition", "glue:BatchCreatePartition"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.dbt_staging.arn,
          "${aws_s3_bucket.dbt_staging.arn}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "dbt_staging_bucket" { value = aws_s3_bucket.dbt_staging.bucket }
output "athena_workgroup"   { value = aws_athena_workgroup.dbt.name }
output "dbt_policy_arn"     { value = aws_iam_policy.dbt.arn }

output "dbt_profiles_yml" {
  description = "Add this to ~/.dbt/profiles.yml"
  value = <<-EOT
    ${var.project}:
      target: dev
      outputs:
        dev:
          type: athena
          s3_staging_dir: s3://${aws_s3_bucket.dbt_staging.bucket}/dbt/
          region_name: ${var.region}
          database: awsdatacatalog
          schema: handson_data_lake
          work_group: ${aws_athena_workgroup.dbt.name}
  EOT
}
