terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "admin_password"  { type = string sensitive = true }
variable "vpc_id"          { description = "VPC ID" }
variable "private_subnet_ids" { type = list(string) }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Redshift Serverless Namespace ───────────────────────────────────────────

resource "aws_redshiftserverless_namespace" "main" {
  namespace_name      = "${var.project}-namespace"
  admin_username      = "admin"
  admin_user_password = var.admin_password
  db_name             = "analytics"

  iam_roles = [aws_iam_role.redshift.arn]

  tags = local.common_tags
}

# ─── Redshift Serverless Workgroup ───────────────────────────────────────────

resource "aws_redshiftserverless_workgroup" "main" {
  namespace_name = aws_redshiftserverless_namespace.main.namespace_name
  workgroup_name = "${var.project}-workgroup"
  base_capacity  = 8   # 8 RPUs — minimum, scales automatically

  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.redshift.id]

  publicly_accessible = false

  tags = local.common_tags
}

# ─── Security Group ───────────────────────────────────────────────────────────

resource "aws_security_group" "redshift" {
  name   = "${var.project}-redshift-sg"
  vpc_id = var.vpc_id

  ingress {
    description = "Redshift from VPC"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project}-redshift-sg" })
}

# ─── IAM Role for Redshift to access S3 ──────────────────────────────────────

resource "aws_iam_role" "redshift" {
  name = "${var.project}-redshift-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "redshift.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "redshift_s3" {
  role       = aws_iam_role.redshift.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "redshift_glue" {
  role       = aws_iam_role.redshift.name
  policy_arn = "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "redshift_endpoint" { value = aws_redshiftserverless_workgroup.main.endpoint[0].address }
output "redshift_port"     { value = 5439 }
output "database_name"     { value = "analytics" }
output "iam_role_arn"      { value = aws_iam_role.redshift.arn }
