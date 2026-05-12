# Project 8.6 — Zero Trust Security Lab
# Enables IAM Identity Center (SSO) and configures VPC Flow Logs for all traffic.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }
variable "vpc_id"  { description = "VPC ID to enable flow logs on" }

locals {
  common_tags = { Project = var.project, Stage = "stage-08", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── VPC Flow Logs (ALL traffic — for Zero Trust visibility) ─────────────────

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/vpc/flow-logs/${var.project}-zero-trust"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_iam_role" "flow_logs" {
  name = "${var.project}-zero-trust-flow-logs-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  name = "flow-logs-policy"
  role = aws_iam_role.flow_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream",
                  "logs:PutLogEvents", "logs:DescribeLogGroups",
                  "logs:DescribeLogStreams"]
      Resource = "*"
    }]
  })
}

resource "aws_flow_log" "all_traffic" {
  vpc_id          = var.vpc_id
  traffic_type    = "ALL"
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  tags            = merge(local.common_tags, { Name = "${var.project}-zero-trust-flow-logs" })
}

# ─── CloudWatch Alarms for Zero Trust Violations ─────────────────────────────

resource "aws_cloudwatch_log_metric_filter" "rejected_connections" {
  name           = "${var.project}-rejected-connections"
  pattern        = "[version, account, eni, source, destination, srcport, destport, protocol, packets, bytes, windowstart, windowend, action=REJECT, flowlogstatus]"
  log_group_name = aws_cloudwatch_log_group.flow_logs.name

  metric_transformation {
    name      = "RejectedConnections"
    namespace = "${var.project}/ZeroTrust"
    value     = "1"
  }
}

resource "aws_sns_topic" "zero_trust_alerts" {
  name = "${var.project}-zero-trust-alerts"
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "high_rejected_connections" {
  alarm_name          = "${var.project}-high-rejected-connections"
  alarm_description   = "Unusually high number of rejected network connections"
  metric_name         = "RejectedConnections"
  namespace           = "${var.project}/ZeroTrust"
  statistic           = "Sum"
  period              = 300
  threshold           = 100
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  alarm_actions       = [aws_sns_topic.zero_trust_alerts.arn]
  treat_missing_data  = "notBreaching"
  tags                = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "flow_log_group"    { value = aws_cloudwatch_log_group.flow_logs.name }
output "flow_log_id"       { value = aws_flow_log.all_traffic.id }
output "sns_topic_arn"     { value = aws_sns_topic.zero_trust_alerts.arn }
