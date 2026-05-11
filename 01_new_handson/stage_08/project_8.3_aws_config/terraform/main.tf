terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "alert_email" { description = "Email for compliance alerts" }

locals {
  common_tags = { Project = var.project, Stage = "stage-08", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Config S3 Bucket ─────────────────────────────────────────────────────────

resource "aws_s3_bucket" "config" {
  bucket = "${var.project}-config-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "config.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.config.arn
      },
      {
        Effect    = "Allow"
        Principal = { Service = "config.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.config.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/Config/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } }
      }
    ]
  })
}

# ─── Config IAM Role ──────────────────────────────────────────────────────────

resource "aws_iam_role" "config" {
  name = "${var.project}-config-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "config.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# ─── Config Recorder ──────────────────────────────────────────────────────────

resource "aws_config_configuration_recorder" "main" {
  name     = "${var.project}-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  name           = "${var.project}-delivery-channel"
  s3_bucket_name = aws_s3_bucket.config.bucket
  depends_on     = [aws_config_configuration_recorder.main]
}

resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.main]
}

# ─── Config Rules ─────────────────────────────────────────────────────────────

resource "aws_config_config_rule" "s3_encryption" {
  name = "s3-bucket-server-side-encryption-enabled"
  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "restricted_ssh" {
  name = "restricted-ssh"
  source {
    owner             = "AWS"
    source_identifier = "INCOMING_SSH_DISABLED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "rds_no_public_access" {
  name = "rds-instance-public-access-check"
  source {
    owner             = "AWS"
    source_identifier = "RDS_INSTANCE_PUBLIC_ACCESS_CHECK"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "required_tags" {
  name = "required-tags"
  source {
    owner             = "AWS"
    source_identifier = "REQUIRED_TAGS"
  }
  input_parameters = jsonencode({
    tag1Key = "Project"
    tag2Key = "Environment"
    tag3Key = "ManagedBy"
  })
  scope {
    compliance_resource_types = ["AWS::EC2::Instance", "AWS::RDS::DBInstance", "AWS::S3::Bucket"]
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "cloudtrail_enabled" {
  name = "cloudtrail-enabled"
  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENABLED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

# ─── SNS for Compliance Alerts ────────────────────────────────────────────────

resource "aws_sns_topic" "compliance" {
  name = "${var.project}-compliance-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "compliance_email" {
  topic_arn = aws_sns_topic.compliance.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── EventBridge Rule for Non-Compliance ─────────────────────────────────────

resource "aws_cloudwatch_event_rule" "config_noncompliant" {
  name        = "${var.project}-config-noncompliant"
  description = "Alert when Config rule finds non-compliant resource"

  event_pattern = jsonencode({
    source      = ["aws.config"]
    detail-type = ["Config Rules Compliance Change"]
    detail = {
      newEvaluationResult = {
        complianceType = ["NON_COMPLIANT"]
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "config_noncompliant_sns" {
  rule      = aws_cloudwatch_event_rule.config_noncompliant.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.compliance.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "config_bucket"    { value = aws_s3_bucket.config.bucket }
output "sns_topic_arn"    { value = aws_sns_topic.compliance.arn }
