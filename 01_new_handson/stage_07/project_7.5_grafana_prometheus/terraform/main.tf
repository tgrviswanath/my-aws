terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-07", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── AWS Managed Prometheus (AMP) ────────────────────────────────────────────

resource "aws_prometheus_workspace" "main" {
  alias = "${var.project}-prometheus"
  tags  = local.common_tags
}

# ─── IAM Role for Prometheus remote_write ────────────────────────────────────

resource "aws_iam_role" "prometheus_write" {
  name = "${var.project}-prometheus-write-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "prometheus_write" {
  name = "amp-write"
  role = aws_iam_role.prometheus_write.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["aps:RemoteWrite", "aps:GetSeries", "aps:GetLabels",
                  "aps:GetMetricMetadata"]
      Resource = aws_prometheus_workspace.main.arn
    }]
  })
}

# ─── AWS Managed Grafana ──────────────────────────────────────────────────────

resource "aws_grafana_workspace" "main" {
  name                     = "${var.project}-grafana"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"

  data_sources = [
    "CLOUDWATCH",
    "PROMETHEUS",
    "XRAY",
  ]

  notification_destinations = ["SNS"]

  tags = local.common_tags
}

# ─── Grafana IAM Role ─────────────────────────────────────────────────────────

resource "aws_iam_role" "grafana" {
  name = "${var.project}-grafana-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "grafana.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "grafana_cloudwatch" {
  role       = aws_iam_role.grafana.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

resource "aws_iam_role_policy" "grafana_prometheus" {
  name = "amp-read"
  role = aws_iam_role.grafana.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["aps:QueryMetrics", "aps:GetSeries", "aps:GetLabels",
                  "aps:GetMetricMetadata", "aps:ListWorkspaces"]
      Resource = "*"
    }]
  })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "grafana_url"              { value = "https://${aws_grafana_workspace.main.endpoint}" }
output "prometheus_endpoint"      { value = aws_prometheus_workspace.main.prometheus_endpoint }
output "prometheus_workspace_id"  { value = aws_prometheus_workspace.main.id }
