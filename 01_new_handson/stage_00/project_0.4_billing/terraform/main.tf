terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Billing metrics are only available in us-east-1
provider "aws" {
  region = "us-east-1"
}

# ─── Variables ────────────────────────────────────────────────────────────────

variable "alert_email" {
  description = "Email address to receive billing alerts"
  type        = string
}

variable "budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 20
}

variable "alarm_threshold" {
  description = "CloudWatch billing alarm threshold in USD"
  type        = number
  default     = 10
}

# ─── SNS Topic ────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "billing_alerts" {
  name = "billing-alerts"

  tags = {
    Project     = "handson"
    Stage       = "stage-00"
    Owner       = "learning"
    Environment = "learning"
  }
}

resource "aws_sns_topic_subscription" "billing_email" {
  topic_arn = aws_sns_topic.billing_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── CloudWatch Billing Alarm ─────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "billing_alarm" {
  alarm_name          = "billing-alert-${var.alarm_threshold}usd"
  alarm_description   = "Alert when estimated charges exceed $${var.alarm_threshold}"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  statistic           = "Maximum"
  period              = 86400
  threshold           = var.alarm_threshold
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  alarm_actions       = [aws_sns_topic.billing_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Project     = "handson"
    Stage       = "stage-00"
    Environment = "learning"
  }
}

# ─── AWS Budget ───────────────────────────────────────────────────────────────

resource "aws_budgets_budget" "monthly" {
  name         = "monthly-aws-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Alert at 50% actual spend
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # Alert at 80% actual spend
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # Alert at 100% forecasted spend
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "sns_topic_arn" {
  description = "ARN of the billing alerts SNS topic"
  value       = aws_sns_topic.billing_alerts.arn
}

output "cloudwatch_alarm_name" {
  description = "Name of the billing CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.billing_alarm.alarm_name
}

output "budget_name" {
  description = "Name of the AWS budget"
  value       = aws_budgets_budget.monthly.name
}
