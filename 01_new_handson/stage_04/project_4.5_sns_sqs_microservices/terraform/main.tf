terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    archive = { source = "hashicorp/archive" version = "~> 2.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  name_prefix = "${var.project}-orders"
  common_tags = { Project = var.project, Stage = "stage-04", ManagedBy = "terraform" }
}

# ─── SNS Topic ────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "order_events" {
  name = "${local.name_prefix}-events"
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-events" })
}

# ─── SQS Queues (one per consumer) ───────────────────────────────────────────

locals {
  consumers = ["inventory", "email", "analytics"]
}

resource "aws_sqs_queue" "dlq" {
  for_each                  = toset(local.consumers)
  name                      = "${local.name_prefix}-${each.key}-dlq"
  message_retention_seconds = 1209600  # 14 days
  tags                      = merge(local.common_tags, { Consumer = each.key })
}

resource "aws_sqs_queue" "consumer" {
  for_each                   = toset(local.consumers)
  name                       = "${local.name_prefix}-${each.key}"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600  # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, { Consumer = each.key })
}

# ─── SNS → SQS Subscriptions ─────────────────────────────────────────────────

resource "aws_sqs_queue_policy" "consumer" {
  for_each  = toset(local.consumers)
  queue_url = aws_sqs_queue.consumer[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.consumer[each.key].arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.order_events.arn } }
    }]
  })
}

resource "aws_sns_topic_subscription" "consumer" {
  for_each  = toset(local.consumers)
  topic_arn = aws_sns_topic.order_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.consumer[each.key].arn
}

# ─── Lambda Consumers ─────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-consumer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "lambda.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "sqs_access" {
  name = "sqs-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = [for q in aws_sqs_queue.consumer : q.arn]
    }]
  })
}

data "archive_file" "consumers" {
  type        = "zip"
  source_file = "${path.module}/../src/consumers.py"
  output_path = "${path.module}/consumers.zip"
}

locals {
  handler_map = {
    inventory = "consumers.inventory_handler"
    email     = "consumers.email_handler"
    analytics = "consumers.analytics_handler"
  }
}

resource "aws_lambda_function" "consumer" {
  for_each         = toset(local.consumers)
  filename         = data.archive_file.consumers.output_path
  function_name    = "${local.name_prefix}-${each.key}-consumer"
  role             = aws_iam_role.lambda.arn
  handler          = local.handler_map[each.key]
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.consumers.output_base64sha256
  tags             = merge(local.common_tags, { Consumer = each.key })
}

resource "aws_lambda_event_source_mapping" "sqs" {
  for_each         = toset(local.consumers)
  event_source_arn = aws_sqs_queue.consumer[each.key].arn
  function_name    = aws_lambda_function.consumer[each.key].arn
  batch_size       = 10
}

# ─── API for publishing orders ────────────────────────────────────────────────

data "archive_file" "publisher" {
  type        = "zip"
  source_file = "${path.module}/../src/order_publisher.py"
  output_path = "${path.module}/publisher.zip"
}

resource "aws_iam_role_policy" "sns_publish" {
  name = "sns-publish"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sns:Publish"]
      Resource = aws_sns_topic.order_events.arn
    }]
  })
}

resource "aws_lambda_function" "publisher" {
  filename         = data.archive_file.publisher.output_path
  function_name    = "${local.name_prefix}-publisher"
  role             = aws_iam_role.lambda.arn
  handler          = "order_publisher.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.publisher.output_base64sha256
  environment { variables = { SNS_TOPIC_ARN = aws_sns_topic.order_events.arn } }
  tags = local.common_tags
}

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  tags          = local.common_tags
}

resource "aws_apigatewayv2_integration" "publisher" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.publisher.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "orders" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.publisher.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
  tags        = local.common_tags
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.publisher.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "api_url"       { value = aws_apigatewayv2_stage.default.invoke_url }
output "sns_topic_arn" { value = aws_sns_topic.order_events.arn }
output "queue_urls"    { value = { for k, q in aws_sqs_queue.consumer : k => q.url } }
output "dlq_urls"      { value = { for k, q in aws_sqs_queue.dlq : k => q.url } }
