terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    archive = { source = "hashicorp/archive" version = "~> 2.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "alert_email" { description = "Email for cost alerts" }

locals {
  common_tags = { Project = var.project, Stage = "stage-10", ManagedBy = "terraform" }
}

# ─── Cost Anomaly Detection ───────────────────────────────────────────────────

resource "aws_ce_anomaly_monitor" "main" {
  name         = "${var.project}-anomaly-monitor"
  monitor_type = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_sns_topic" "cost_alerts" {
  name = "${var.project}-cost-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "cost_email" {
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_ce_anomaly_subscription" "main" {
  name      = "${var.project}-anomaly-subscription"
  frequency = "DAILY"

  monitor_arn_list = [aws_ce_anomaly_monitor.main.arn]

  subscriber {
    address = aws_sns_topic.cost_alerts.arn
    type    = "SNS"
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = ["10"]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }
}

# ─── Lambda: Daily Cost Optimizer ────────────────────────────────────────────

resource "aws_iam_role" "optimizer" {
  name = "${var.project}-cost-optimizer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "lambda.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "optimizer_basic" {
  role       = aws_iam_role.optimizer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "optimizer_ec2" {
  name = "ec2-ebs-access"
  role = aws_iam_role.optimizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:DescribeVolumes",
                    "ec2:DescribeSnapshots", "ec2:StopInstances",
                    "cloudwatch:GetMetricStatistics"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.cost_alerts.arn
      }
    ]
  })
}

data "archive_file" "optimizer" {
  type        = "zip"
  source_file = "${path.module}/../src/cost_optimizer.py"
  output_path = "${path.module}/optimizer.zip"
}

resource "aws_lambda_function" "optimizer" {
  filename         = data.archive_file.optimizer.output_path
  function_name    = "${var.project}-cost-optimizer"
  role             = aws_iam_role.optimizer.arn
  handler          = "cost_optimizer.print_report"
  runtime          = "python3.11"
  timeout          = 300
  source_code_hash = data.archive_file.optimizer.output_base64sha256
  tags             = local.common_tags
}

# Run daily at 8am UTC
resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.project}-cost-optimizer-daily"
  schedule_expression = "cron(0 8 * * ? *)"
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "optimizer" {
  rule      = aws_cloudwatch_event_rule.daily.name
  target_id = "CostOptimizer"
  arn       = aws_lambda_function.optimizer.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "lambda_name"    { value = aws_lambda_function.optimizer.function_name }
output "sns_topic_arn"  { value = aws_sns_topic.cost_alerts.arn }
