output "vpc_id"          { value = aws_vpc.main.id }
output "log_group_name"  { value = aws_cloudwatch_log_group.flow_logs.name }
output "s3_bucket"       { value = aws_s3_bucket.flow_logs.bucket }
