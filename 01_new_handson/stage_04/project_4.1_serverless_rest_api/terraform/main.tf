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
  name_prefix = "${var.project}-api"
  common_tags = { Project = var.project, Stage = "stage-04", ManagedBy = "terraform" }
}

# ─── DynamoDB Table ───────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "items" {
  name         = "${local.name_prefix}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-items" })
}

# ─── Lambda IAM Role ──────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-lambda-role"

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

resource "aws_iam_role_policy" "dynamodb" {
  name = "dynamodb-access"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                  "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query"]
      Resource = aws_dynamodb_table.items.arn
    }]
  })
}

# ─── Lambda Function ──────────────────────────────────────────────────────────

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "api" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "${local.name_prefix}-handler"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.items.name
    }
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-handler" })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
  tags              = local.common_tags
}

# ─── API Gateway (HTTP API v2) ────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-gateway"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-gateway" })
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "list" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /items"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "get" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /items/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "create" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /items"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "update" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "PUT /items/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "delete" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "DELETE /items/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${local.name_prefix}"
  retention_in_days = 7
  tags              = local.common_tags
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "api_url"        { value = aws_apigatewayv2_stage.default.invoke_url }
output "table_name"     { value = aws_dynamodb_table.items.name }
output "lambda_name"    { value = aws_lambda_function.api.function_name }
