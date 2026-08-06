terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

locals {
  common_tags = {
    Project   = var.project
    Stage     = "stage-09"
    ManagedBy = "terraform"
  }
}

# ─── Upload ETL Script to S3 ──────────────────────────────────────────────────
# Terraform uploads the local PySpark script to S3 before creating the Glue job.
# etag = MD5 of file content — if etl_job.py changes locally, Terraform re-uploads.

resource "aws_s3_object" "etl_script" {
  bucket = var.data_lake_bucket
  key    = "scripts/etl_job.py"
  source = "${path.module}/../src/etl_job.py"
  etag   = filemd5("${path.module}/../src/etl_job.py")
  tags   = local.common_tags
}

# ─── Glue ETL Job ─────────────────────────────────────────────────────────────

resource "aws_glue_job" "etl" {
  name     = "${var.project}-etl-job"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"   # Spark ETL job type (not "pythonshell")
    script_location = "s3://${var.data_lake_bucket}/scripts/etl_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                      = "python"
    "--job-bookmark-option"               = "job-bookmark-enable"
    "--enable-metrics"                    = "true"
    "--enable-continuous-cloudwatch-log"  = "true"
    "--source_bucket"                     = var.data_lake_bucket
    "--target_bucket"                     = var.data_lake_bucket
    "--database_name"                     = var.database_name
    "--TempDir"                           = "s3://${var.data_lake_bucket}/temp/"
  }

  glue_version      = var.glue_version
  number_of_workers = var.num_workers
  worker_type       = var.worker_type
  timeout           = var.job_timeout_minutes
  max_retries       = 1

  tags = local.common_tags

  # Ensure the script is uploaded to S3 before job is created
  depends_on = [aws_s3_object.etl_script]
}

# ─── Glue Trigger (daily schedule) ───────────────────────────────────────────
# Created in CREATED (inactive) state by default.
# Set enable_trigger = true in terraform.tfvars to activate automatic daily runs.

resource "aws_glue_trigger" "daily" {
  name     = "${var.project}-etl-daily"
  type     = "SCHEDULED"
  schedule = var.trigger_schedule
  enabled  = var.enable_trigger   # false = CREATED state (no auto-runs)

  actions {
    job_name = aws_glue_job.etl.name
  }

  tags = local.common_tags
}
