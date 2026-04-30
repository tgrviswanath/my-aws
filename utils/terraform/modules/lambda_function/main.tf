# Reusable Terraform module for Lambda function with best practices
# Usage:
# module "my_function" {
#   source        = "./modules/lambda_function"
#   function_name = "my-function"
#   handler       = "app.handler"
#   runtime       = "python3.12"
#   source_dir    = "${path.module}/src"
#   environment_variables = {
#     TABLE_NAME = aws_dynamodb_table.main.name
#   }
#   iam_policy_statements = [
#     {
#       effect    = "Allow"
#       actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
#       resources = [aws_dynamodb_table.main.arn]
#     }
#   ]
# }

variable "function_name" {
  description = "Lambda function name"
  type        = string
}

variable "handler" {
  description = "Lambda handler (file.function)"
  type        = string
  default     = "handler.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "architectures" {
  description = "Lambda architectures"
  type        = list(string)
  default     = ["arm64"]
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512
}

variable "source_dir" {
  description = "Directory containing Lambda source code"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "iam_policy_statements" {
  description = "Additional IAM policy statements"
  type = list(object({
    effect    = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "vpc_config" {
  description = "VPC configuration for Lambda"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "reserved_concurrency" {
  description = "Reserved concurrency (-1 = unreserved)"
  type        = number
  default     = -1
}

variable "enable_xray" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = null
}

variable "layers" {
  description = "Lambda layer ARNs"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── Package Lambda code ───────────────────────────────────────────────────────
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/${var.function_name}.zip"
}

# ── IAM Role ──────────────────────────────────────────────────────────────────
resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = var.vpc_config != null ? (
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  ) : (
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  )
}

resource "aws_iam_role_policy" "custom" {
  count = length(var.iam_policy_statements) > 0 ? 1 : 0
  name  = "${var.function_name}-policy"
  role  = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for stmt in var.iam_policy_statements : {
        Effect   = stmt.effect
        Action   = stmt.actions
        Resource = stmt.resources
      }
    ]
  })
}

# ── CloudWatch Log Group ──────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = var.tags
}

# ── Lambda Function ───────────────────────────────────────────────────────────
resource "aws_lambda_function" "main" {
  function_name = var.function_name
  role          = aws_iam_role.lambda.arn
  handler       = var.handler
  runtime       = var.runtime
  architectures = var.architectures
  timeout       = var.timeout
  memory_size   = var.memory_size
  layers        = var.layers

  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  reserved_concurrent_executions = var.reserved_concurrency

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  environment {
    variables = merge(var.environment_variables, {
      POWERTOOLS_SERVICE_NAME = var.function_name
      LOG_LEVEL               = "INFO"
    })
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.basic,
    aws_cloudwatch_log_group.lambda
  ]

  tags = var.tags
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.function_name}-errors"
  alarm_description   = "Lambda function error rate"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "throttles" {
  alarm_name          = "${var.function_name}-throttles"
  alarm_description   = "Lambda function throttles"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = var.tags
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.main.arn
}

output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.main.function_name
}

output "invoke_arn" {
  description = "Lambda invoke ARN (for API Gateway)"
  value       = aws_lambda_function.main.invoke_arn
}

output "role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.lambda.name
}
