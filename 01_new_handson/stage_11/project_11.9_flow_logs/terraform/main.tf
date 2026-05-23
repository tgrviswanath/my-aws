terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

data "aws_caller_identity" "current" {}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-9" }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/vpc/flowlogs/11-9"
  retention_in_days = 7
}

# IAM Role for Flow Logs
resource "aws_iam_role" "flow_logs" {
  name = "role-flowlogs-11-9"
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
  role = aws_iam_role.flow_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                  "logs:DescribeLogGroups", "logs:DescribeLogStreams"]
      Resource = "*"
    }]
  })
}

# S3 Bucket for flow logs
resource "aws_s3_bucket" "flow_logs" {
  bucket        = "flowlogs-11-9-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags = { Name = "flowlogs-11-9" }
}

# Flow Log → CloudWatch
resource "aws_flow_log" "cw" {
  vpc_id                   = aws_vpc.main.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.flow_logs.arn
  iam_role_arn             = aws_iam_role.flow_logs.arn
  max_aggregation_interval = 60
  tags = { Name = "flowlog-cw-11-9" }
}

# Flow Log → S3
resource "aws_flow_log" "s3" {
  vpc_id                   = aws_vpc.main.id
  traffic_type             = "ALL"
  log_destination_type     = "s3"
  log_destination          = aws_s3_bucket.flow_logs.arn
  max_aggregation_interval = 60
  tags = { Name = "flowlog-s3-11-9" }
}
