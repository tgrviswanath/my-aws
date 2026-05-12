# Project 9.7 — Data Quality Validation
# Lambda function that runs Great Expectations checks after each ETL job.

terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    archive = { source = "hashicorp/archive" version = "~> 2.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "data_lake_bucket" { description = "Data lake S3 bucket" }
variable "alert_email"     { description = "Email for quality failure alerts" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

# ─── SNS for quality alerts ───────────────────────────────────────────────────

resource "aws_sns_topic" "quality_alerts" {
  name = "${var.project}-data-quality-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "quality_email" {
  topic_arn = aws_sns_topic.quality_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── Lambda IAM Role ──────────────────────────────────────────────────────────

resource "aws_iam_role" "quality_lambda" {
  name = "${var.project}-quality-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "lambda.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "quality_basic" {
  role       = aws_iam_role.quality_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "quality_s3_sns" {
  name = "s3-sns-access"
  role = aws_iam_role.quality_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
        Resource = [
          "arn:aws:s3:::${var.data_lake_bucket}",
          "arn:aws:s3:::${var.data_lake_bucket}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.quality_alerts.arn
      }
    ]
  })
}

# ─── Lambda Function ──────────────────────────────────────────────────────────

data "archive_file" "quality" {
  type        = "zip"
  source_file = "${path.module}/../src/validate_orders.py"
  output_path = "${path.module}/quality.zip"
}

resource "aws_lambda_function" "quality" {
  filename         = data.archive_file.quality.output_path
  function_name    = "${var.project}-data-quality-check"
  role             = aws_iam_role.quality_lambda.arn
  handler          = "validate_orders.main"
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 512
  source_code_hash = data.archive_file.quality.output_base64sha256

  environment {
    variables = {
      DATA_LAKE_BUCKET = var.data_lake_bucket
      SNS_TOPIC_ARN    = aws_sns_topic.quality_alerts.arn
    }
  }

  tags = local.common_tags
}

# ─── EventBridge: trigger after Glue job completes ───────────────────────────

resource "aws_cloudwatch_event_rule" "glue_success" {
  name        = "${var.project}-glue-job-success"
  description = "Trigger data quality check after Glue ETL job succeeds"

  event_pattern = jsonencode({
    source      = ["aws.glue"]
    detail-type = ["Glue Job State Change"]
    detail = {
      jobName = ["${var.project}-etl-job"]
      state   = ["SUCCEEDED"]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "quality_lambda" {
  rule      = aws_cloudwatch_event_rule.glue_success.name
  target_id = "TriggerQualityCheck"
  arn       = aws_lambda_function.quality.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.quality.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.glue_success.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "lambda_name"   { value = aws_lambda_function.quality.function_name }
output "sns_topic_arn" { value = aws_sns_topic.quality_alerts.arn }
