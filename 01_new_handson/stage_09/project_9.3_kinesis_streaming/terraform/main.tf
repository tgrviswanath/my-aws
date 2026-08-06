terraform {
  required_providers {
    aws     = { source = "hashicorp/aws",     version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}

provider "aws" { region = var.region }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

# ─── Kinesis Data Stream ──────────────────────────────────────────────────────

resource "aws_kinesis_stream" "events" {
  name             = "${var.project}-events"
  shard_count      = var.shard_count
  retention_period = var.retention_hours

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = merge(local.common_tags, { Name = "${var.project}-events" })
}

# ─── DynamoDB for aggregates ──────────────────────────────────────────────────

resource "aws_dynamodb_table" "aggregates" {
  name         = "${var.project}-stream-aggregates"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute { name = "pk" type = "S" }
  attribute { name = "sk" type = "S" }

  tags = merge(local.common_tags, { Name = "${var.project}-stream-aggregates" })
}

# ─── Lambda Consumer ──────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${var.project}-kinesis-consumer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_kinesis_dynamo" {
  name = "kinesis-dynamo-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["kinesis:GetRecords", "kinesis:GetShardIterator",
                    "kinesis:DescribeStream", "kinesis:ListStreams",
                    "kinesis:ListShards"]
        Resource = aws_kinesis_stream.events.arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem", "dynamodb:PutItem", "dynamodb:GetItem"]
        Resource = aws_dynamodb_table.aggregates.arn
      }
    ]
  })
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/consumer_lambda.py"
  output_path = "${path.module}/consumer.zip"
}

resource "aws_lambda_function" "consumer" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "${var.project}-kinesis-consumer"
  role             = aws_iam_role.lambda.arn
  handler          = "consumer_lambda.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = { TABLE_NAME = aws_dynamodb_table.aggregates.name }
  }

  tags = local.common_tags
}

# ─── Kinesis → Lambda trigger ─────────────────────────────────────────────────

resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn              = aws_kinesis_stream.events.arn
  function_name                 = aws_lambda_function.consumer.arn
  starting_position             = "LATEST"
  batch_size                    = 100
  bisect_batch_on_function_error = true   # split batch on error to isolate bad records

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.dlq.arn
    }
  }
}

resource "aws_sqs_queue" "dlq" {
  name = "${var.project}-kinesis-dlq"
  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "stream_name"    { value = aws_kinesis_stream.events.name }
output "stream_arn"     { value = aws_kinesis_stream.events.arn }
output "table_name"     { value = aws_dynamodb_table.aggregates.name }
output "lambda_name"    { value = aws_lambda_function.consumer.function_name }
