terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"        { default = "us-east-1" }
variable "project"       { default = "handson" }
variable "data_lake_bucket" { description = "Data lake S3 bucket name" }
variable "glue_role_arn"    { description = "Glue IAM role ARN from project 9.1" }
variable "database_name"    { description = "Glue database name from project 9.1" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

# ─── Upload ETL Script to S3 ──────────────────────────────────────────────────

resource "aws_s3_object" "etl_script" {
  bucket = var.data_lake_bucket
  key    = "scripts/etl_job.py"
  source = "${path.module}/../src/etl_job.py"
  etag   = filemd5("${path.module}/../src/etl_job.py")
}

# ─── Glue Job ─────────────────────────────────────────────────────────────────

resource "aws_glue_job" "etl" {
  name     = "${var.project}-etl-job"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.data_lake_bucket}/scripts/etl_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"              = "python"
    "--job-bookmark-option"       = "job-bookmark-enable"
    "--enable-metrics"            = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--source_bucket"             = var.data_lake_bucket
    "--target_bucket"             = var.data_lake_bucket
    "--database_name"             = var.database_name
    "--TempDir"                   = "s3://${var.data_lake_bucket}/temp/"
  }

  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"   # 4 vCPU, 16 GB RAM per worker

  timeout = 60   # minutes

  tags = local.common_tags
}

# ─── Glue Trigger (daily schedule) ───────────────────────────────────────────

resource "aws_glue_trigger" "daily" {
  name     = "${var.project}-etl-daily"
  type     = "SCHEDULED"
  schedule = "cron(0 2 * * ? *)"   # 2am UTC daily

  actions {
    job_name = aws_glue_job.etl.name
  }

  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "glue_job_name"    { value = aws_glue_job.etl.name }
output "glue_trigger_name" { value = aws_glue_trigger.daily.name }
