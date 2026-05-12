# Project 2.5 — Failure Simulation Lab
# Enables VPC Flow Logs for diagnosing network failures.

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
  common_tags = { Project = var.project, Stage = "stage-02", ManagedBy = "terraform" }
}

# CloudWatch log group for VPC flow logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/vpc/flow-logs/${var.project}"
  retention_in_days = 7
  tags              = local.common_tags
}

# IAM role for flow logs to write to CloudWatch
resource "aws_iam_role" "flow_logs" {
  name = "${var.project}-flow-logs-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
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

# Enable VPC Flow Logs
resource "aws_flow_log" "main" {
  vpc_id          = var.vpc_id
  traffic_type    = "ALL"
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  tags            = merge(local.common_tags, { Name = "${var.project}-flow-logs" })
}

output "log_group_name" { value = aws_cloudwatch_log_group.flow_logs.name }
output "flow_log_id"    { value = aws_flow_log.main.id }
