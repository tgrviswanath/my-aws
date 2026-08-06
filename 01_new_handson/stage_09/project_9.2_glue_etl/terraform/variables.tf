# variables.tf — Project 9.2 Glue ETL Pipeline
# ─────────────────────────────────────────────────────────────────────────────
# All configurable parameters for the Glue ETL pipeline.
# Required variables (no defaults) MUST be set via terraform.tfvars or -var flag.
# Get required values from Project 9.1 terraform outputs.
# ─────────────────────────────────────────────────────────────────────────────

variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix used in all resource names"
  type        = string
  default     = "handson"
}

# ── Required — get from Project 9.1 terraform outputs ──────────────────────

variable "data_lake_bucket" {
  description = "S3 data lake bucket name from Project 9.1 (terraform output data_lake_bucket)"
  type        = string
  # No default — must be provided
  # Get with: cd ../project_9.1_data_lake/terraform && terraform output -raw data_lake_bucket
}

variable "glue_role_arn" {
  description = "Glue IAM role ARN from Project 9.1 (terraform output glue_role_arn)"
  type        = string
  # No default — must be provided
  # Get with: cd ../project_9.1_data_lake/terraform && terraform output -raw glue_role_arn
}

variable "database_name" {
  description = "Glue Data Catalog database name from Project 9.1 (terraform output glue_database)"
  type        = string
  default     = "handson_data_lake"
  # Default matches the database created in Project 9.1
}

# ── Optional — tune as needed ───────────────────────────────────────────────

variable "worker_type" {
  description = "Glue worker type: G.1X (4vCPU/16GB), G.2X (8vCPU/32GB)"
  type        = string
  default     = "G.1X"
  validation {
    condition     = contains(["G.1X", "G.2X", "G.4X", "G.8X"], var.worker_type)
    error_message = "Worker type must be one of: G.1X, G.2X, G.4X, G.8X"
  }
}

variable "num_workers" {
  description = "Number of Glue workers (minimum 2 for Spark)"
  type        = number
  default     = 2
  validation {
    condition     = var.num_workers >= 2
    error_message = "Minimum 2 workers required for Spark execution"
  }
}

variable "job_timeout_minutes" {
  description = "Maximum job runtime in minutes (cost protection — kills runaway jobs)"
  type        = number
  default     = 60
}

variable "glue_version" {
  description = "AWS Glue version (affects Spark version)"
  type        = string
  default     = "4.0"
  # Glue 4.0 = Spark 3.3.0, Python 3.10
  # Glue 3.0 = Spark 3.1.1, Python 3.7 (older)
}

variable "trigger_schedule" {
  description = "Cron schedule for daily trigger (AWS 6-field cron format)"
  type        = string
  default     = "cron(0 2 * * ? *)"
  # Default: 2:00 AM UTC daily
  # Example alternatives:
  # "cron(0 */6 * * ? *)"  — every 6 hours
  # "cron(0 2 ? * MON *)"  — every Monday at 2am
}

variable "enable_trigger" {
  description = "Whether to activate the daily trigger (set false during learning to avoid daily charges)"
  type        = bool
  default     = false
  # Set to true in production to enable automatic daily runs
}
