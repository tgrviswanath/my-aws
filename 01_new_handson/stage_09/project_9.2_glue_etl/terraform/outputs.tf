# outputs.tf — Project 9.2 Glue ETL Pipeline
# ─────────────────────────────────────────────────────────────────────────────
# Values exported after terraform apply.
# Use: terraform output glue_job_name
# Reference in scripts: $(terraform output -raw glue_job_name)
# ─────────────────────────────────────────────────────────────────────────────

output "glue_job_name" {
  description = "Name of the Glue ETL job"
  value       = aws_glue_job.etl.name
}

output "glue_trigger_name" {
  description = "Name of the daily Glue trigger"
  value       = aws_glue_trigger.daily.name
}

output "etl_script_s3_path" {
  description = "S3 URI of the uploaded PySpark ETL script"
  value       = "s3://${var.data_lake_bucket}/scripts/etl_job.py"
}

output "processed_output_path" {
  description = "S3 URI where processed Parquet files are written"
  value       = "s3://${var.data_lake_bucket}/processed/orders/"
}

output "daily_aggregates_path" {
  description = "S3 URI where daily aggregate Parquet files are written"
  value       = "s3://${var.data_lake_bucket}/processed/orders_daily/"
}

output "start_job_command" {
  description = "AWS CLI command to manually start a job run"
  value       = "aws glue start-job-run --job-name ${aws_glue_job.etl.name}"
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for job output logs"
  value       = "/aws-glue/jobs/output"
}

output "cost_per_run_estimate" {
  description = "Estimated cost per 10-minute job run (2 x G.1X workers)"
  value       = "~$0.15 USD (2 workers x G.1X x 10min / 60min x $0.44/DPU-hr)"
}
