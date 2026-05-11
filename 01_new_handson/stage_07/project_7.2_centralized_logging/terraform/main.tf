terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "log_group_name"  { default = "/ecs/handson-flask-api" }
variable "master_user"     { default = "admin" }
variable "master_password" { type = string sensitive = true }

locals {
  domain_name = "${var.project}-logs"
  common_tags = { Project = var.project, Stage = "stage-07", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ─── OpenSearch Domain ────────────────────────────────────────────────────────

resource "aws_opensearch_domain" "logs" {
  domain_name    = local.domain_name
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type  = "t3.small.search"   # cheapest option
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10   # GB
    volume_type = "gp3"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.master_user
      master_user_password = var.master_password
    }
  }

  encrypt_at_rest { enabled = true }
  node_to_node_encryption { enabled = true }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "*" }
      Action    = "es:*"
      Resource  = "arn:aws:es:${var.region}:${data.aws_caller_identity.current.account_id}:domain/${local.domain_name}/*"
    }]
  })

  tags = merge(local.common_tags, { Name = local.domain_name })
}

# ─── Firehose IAM Role ────────────────────────────────────────────────────────

resource "aws_iam_role" "firehose" {
  name = "${var.project}-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "firehose.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "firehose" {
  name = "firehose-opensearch-policy"
  role = aws_iam_role.firehose.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["es:DescribeElasticsearchDomain", "es:DescribeElasticsearchDomains",
                    "es:DescribeElasticsearchDomainConfig", "es:ESHttpPost", "es:ESHttpPut"]
        Resource = ["${aws_opensearch_domain.logs.arn}", "${aws_opensearch_domain.logs.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:AbortMultipartUpload", "s3:GetBucketLocation", "s3:GetObject",
                    "s3:ListBucket", "s3:ListBucketMultipartUploads", "s3:PutObject"]
        Resource = ["${aws_s3_bucket.firehose_backup.arn}", "${aws_s3_bucket.firehose_backup.arn}/*"]
      }
    ]
  })
}

# ─── S3 Backup for Firehose ───────────────────────────────────────────────────

resource "aws_s3_bucket" "firehose_backup" {
  bucket = "${var.project}-firehose-backup-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_lifecycle_configuration" "firehose_backup" {
  bucket = aws_s3_bucket.firehose_backup.id
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    expiration { days = 30 }
  }
}

# ─── Kinesis Firehose ─────────────────────────────────────────────────────────

resource "aws_kinesis_firehose_delivery_stream" "logs" {
  name        = "${var.project}-logs-stream"
  destination = "opensearch"

  opensearch_configuration {
    domain_arn         = aws_opensearch_domain.logs.arn
    role_arn           = aws_iam_role.firehose.arn
    index_name         = "ecs-logs"
    index_rotation_period = "OneDay"
    buffering_size     = 5
    buffering_interval = 60

    s3_configuration {
      role_arn           = aws_iam_role.firehose.arn
      bucket_arn         = aws_s3_bucket.firehose_backup.arn
      buffering_size     = 10
      buffering_interval = 300
      compression_format = "GZIP"
    }
  }

  tags = local.common_tags
}

# ─── CloudWatch Logs Subscription Filter ─────────────────────────────────────

resource "aws_iam_role" "cwl_firehose" {
  name = "${var.project}-cwl-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "cwl_firehose" {
  name = "cwl-firehose-policy"
  role = aws_iam_role.cwl_firehose.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["firehose:PutRecord", "firehose:PutRecordBatch"]
      Resource = aws_kinesis_firehose_delivery_stream.logs.arn
    }]
  })
}

resource "aws_cloudwatch_log_subscription_filter" "ecs_to_firehose" {
  name            = "${var.project}-ecs-to-opensearch"
  log_group_name  = var.log_group_name
  filter_pattern  = ""   # empty = all logs
  destination_arn = aws_kinesis_firehose_delivery_stream.logs.arn
  role_arn        = aws_iam_role.cwl_firehose.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "opensearch_endpoint" { value = aws_opensearch_domain.logs.endpoint }
output "kibana_url"          { value = "https://${aws_opensearch_domain.logs.endpoint}/_dashboards" }
output "firehose_stream_name" { value = aws_kinesis_firehose_delivery_stream.logs.name }
