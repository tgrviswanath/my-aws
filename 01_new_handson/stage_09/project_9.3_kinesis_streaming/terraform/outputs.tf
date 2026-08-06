# outputs.tf — Project 9.3 Kinesis Streaming Pipeline
# ─────────────────────────────────────────────────────────────────────────────
# Values exported after terraform apply.
# Usage: terraform output stream_name
#        $(terraform output -raw stream_name)
# ─────────────────────────────────────────────────────────────────────────────

output "stream_name" {
  description = "Kinesis Data Stream name"
  value       = aws_kinesis_stream.events.name
}

output "stream_arn" {
  description = "Kinesis Data Stream ARN"
  value       = aws_kinesis_stream.events.arn
}

output "table_name" {
  description = "DynamoDB aggregates table name"
  value       = aws_dynamodb_table.aggregates.name
}

output "lambda_name" {
  description = "Lambda consumer function name"
  value       = aws_lambda_function.consumer.function_name
}

output "lambda_arn" {
  description = "Lambda consumer function ARN"
  value       = aws_lambda_function.consumer.arn
}

output "dlq_url" {
  description = "SQS Dead Letter Queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "SQS Dead Letter Queue ARN"
  value       = aws_sqs_queue.dlq.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda output"
  value       = "/aws/lambda/${aws_lambda_function.consumer.function_name}"
}

output "run_producer" {
  description = "Command to send test events to the stream"
  value       = "python src/producer.py"
}

output "tail_logs" {
  description = "Command to watch Lambda logs in real-time"
  value       = "aws logs tail /aws/lambda/${aws_lambda_function.consumer.function_name} --follow"
}

output "check_aggregates" {
  description = "Command to view DynamoDB aggregates"
  value       = "aws dynamodb scan --table-name ${aws_dynamodb_table.aggregates.name} --query \"Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N}\""
}

output "cost_per_hour" {
  description = "Estimated Kinesis cost per hour (shard cost only)"
  value       = "$${format("%.3f", var.shard_count * 0.015)}/hr for ${var.shard_count} shard(s)"
}
