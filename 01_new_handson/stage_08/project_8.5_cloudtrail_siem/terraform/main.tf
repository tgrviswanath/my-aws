terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "alert_email" { description = "Email for security alerts" }

locals {
  common_tags = { Project = var.project, Stage = "stage-08", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── CloudTrail S3 Bucket ─────────────────────────────────────────────────────

resource "aws_s3_bucket" "cloudtrail" {
  bucket = "${var.project}-cloudtrail-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.cloudtrail.arn
      },
      {
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.cloudtrail.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } }
      }
    ]
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration { days = 365 }
  }
}

# ─── CloudWatch Log Group for CloudTrail ─────────────────────────────────────

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/${var.project}"
  retention_in_days = 90
  tags              = local.common_tags
}

resource "aws_iam_role" "cloudtrail_cw" {
  name = "${var.project}-cloudtrail-cw-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "cloudtrail.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "cloudtrail_cw" {
  name = "cloudwatch-logs"
  role = aws_iam_role.cloudtrail_cw.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
    }]
  })
}

# ─── CloudTrail ───────────────────────────────────────────────────────────────

resource "aws_cloudtrail" "main" {
  name                          = "${var.project}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.cloudtrail_cw.arn
  is_multi_region_trail         = true
  enable_log_file_validation    = true   # SHA-256 integrity validation
  include_global_service_events = true   # IAM, STS, etc.

  # CloudTrail Insights — detect unusual API activity
  insight_selector {
    insight_type = "ApiCallRateInsight"
  }
  insight_selector {
    insight_type = "ApiErrorRateInsight"
  }

  tags = merge(local.common_tags, { Name = "${var.project}-trail" })
}

# ─── SNS + EventBridge for Critical Events ────────────────────────────────────

resource "aws_sns_topic" "security_events" {
  name = "${var.project}-security-events"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "security_email" {
  topic_arn = aws_sns_topic.security_events.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Alert on root account usage
resource "aws_cloudwatch_event_rule" "root_usage" {
  name        = "${var.project}-root-account-usage"
  description = "Alert when root account is used"
  event_pattern = jsonencode({
    source      = ["aws.signin"]
    detail-type = ["AWS Console Sign In via CloudTrail"]
    detail      = { userIdentity = { type = ["Root"] } }
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "root_usage_sns" {
  rule      = aws_cloudwatch_event_rule.root_usage.name
  target_id = "RootUsageSNS"
  arn       = aws_sns_topic.security_events.arn
}

# Alert on IAM policy changes
resource "aws_cloudwatch_event_rule" "iam_changes" {
  name        = "${var.project}-iam-changes"
  description = "Alert on IAM policy/role changes"
  event_pattern = jsonencode({
    source      = ["aws.iam"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventName = [
        "CreateUser", "DeleteUser", "AttachRolePolicy", "DetachRolePolicy",
        "CreateRole", "DeleteRole", "PutUserPolicy", "CreateAccessKey",
        "UpdateAssumeRolePolicy"
      ]
    }
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "iam_changes_sns" {
  rule      = aws_cloudwatch_event_rule.iam_changes.name
  target_id = "IAMChangesSNS"
  arn       = aws_sns_topic.security_events.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "cloudtrail_arn"    { value = aws_cloudtrail.main.arn }
output "s3_bucket"         { value = aws_s3_bucket.cloudtrail.bucket }
output "log_group"         { value = aws_cloudwatch_log_group.cloudtrail.name }
output "sns_topic_arn"     { value = aws_sns_topic.security_events.arn }
