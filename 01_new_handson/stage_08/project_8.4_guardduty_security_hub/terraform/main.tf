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

# ─── GuardDuty ────────────────────────────────────────────────────────────────

resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs { enable = true }
    kubernetes {
      audit_logs { enable = true }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes { enable = true }
      }
    }
  }

  tags = local.common_tags
}

# ─── Security Hub ─────────────────────────────────────────────────────────────

resource "aws_securityhub_account" "main" {}

# Enable CIS AWS Foundations standard
resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:${var.region}::standards/cis-aws-foundations-benchmark/v/1.4.0"
  depends_on    = [aws_securityhub_account.main]
}

# Enable AWS Foundational Security Best Practices
resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:${var.region}::standards/aws-foundational-security-best-practices/v/1.0.0"
  depends_on    = [aws_securityhub_account.main]
}

# Connect GuardDuty findings to Security Hub
resource "aws_securityhub_product_subscription" "guardduty" {
  product_arn = "arn:aws:securityhub:${var.region}::product/aws/guardduty"
  depends_on  = [aws_securityhub_account.main]
}

# ─── SNS for Security Alerts ──────────────────────────────────────────────────

resource "aws_sns_topic" "security" {
  name = "${var.project}-security-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "security_email" {
  topic_arn = aws_sns_topic.security.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── EventBridge: GuardDuty HIGH/CRITICAL findings → SNS ─────────────────────

resource "aws_cloudwatch_event_rule" "guardduty_high" {
  name        = "${var.project}-guardduty-high-severity"
  description = "Alert on GuardDuty HIGH and CRITICAL findings"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "guardduty_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_high.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security.arn

  input_transformer {
    input_paths = {
      severity    = "$.detail.severity"
      type        = "$.detail.type"
      description = "$.detail.description"
      account     = "$.detail.accountId"
      region      = "$.region"
    }
    input_template = "\"GuardDuty Finding\\nSeverity: <severity>\\nType: <type>\\nAccount: <account>\\nRegion: <region>\\nDescription: <description>\""
  }
}

# ─── EventBridge: Security Hub CRITICAL findings → SNS ───────────────────────

resource "aws_cloudwatch_event_rule" "securityhub_critical" {
  name        = "${var.project}-securityhub-critical"
  description = "Alert on Security Hub CRITICAL findings"

  event_pattern = jsonencode({
    source      = ["aws.securityhub"]
    detail-type = ["Security Hub Findings - Imported"]
    detail = {
      findings = {
        Severity = { Label = ["CRITICAL"] }
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "securityhub_sns" {
  rule      = aws_cloudwatch_event_rule.securityhub_critical.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "guardduty_detector_id" { value = aws_guardduty_detector.main.id }
output "security_hub_arn"      { value = aws_securityhub_account.main.id }
output "sns_topic_arn"         { value = aws_sns_topic.security.arn }
