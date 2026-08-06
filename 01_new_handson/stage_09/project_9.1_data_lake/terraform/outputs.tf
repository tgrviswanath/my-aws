output "data_lake_bucket" {
  description = "Name of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.bucket
}

output "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "athena_results_bucket" {
  description = "Name of the S3 bucket for Athena query results"
  value       = aws_s3_bucket.athena_results.bucket
}

output "glue_database" {
  description = "Name of the main Glue Data Catalog database"
  value       = aws_glue_catalog_database.data_lake.name
}

output "glue_role_arn" {
  description = "ARN of the IAM role used by Glue crawler"
  value       = aws_iam_role.glue.arn
}

output "glue_crawler_name" {
  description = "Name of the Glue crawler"
  value       = aws_glue_crawler.raw_data.name
}

output "athena_workgroup" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.data_lake.name
}

output "raw_zone_path" {
  description = "S3 path for the raw zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/raw/"
}

output "processed_zone_path" {
  description = "S3 path for the processed zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/processed/"
}

output "curated_zone_path" {
  description = "S3 path for the curated zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/curated/"
}
