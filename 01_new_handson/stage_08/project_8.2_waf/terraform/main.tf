terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }
variable "alb_arn" { description = "ARN of the ALB to protect" }

locals {
  common_tags = { Project = var.project, Stage = "stage-08", ManagedBy = "terraform" }
}

# ─── WAF Web ACL ──────────────────────────────────────────────────────────────

resource "aws_wafv2_web_acl" "main" {
  name  = "${var.project}-web-acl"
  scope = "REGIONAL"   # use CLOUDFRONT for CloudFront distributions

  default_action { allow {} }

  # ─── Rule 1: Rate limiting (100 req per 5 min per IP) ─────────────────────
  rule {
    name     = "rate-limit"
    priority = 1

    action { block {} }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimit"
      sampled_requests_enabled   = true
    }
  }

  # ─── Rule 2: AWS Managed Core Rule Set (OWASP Top 10) ─────────────────────
  rule {
    name     = "aws-managed-core-rules"
    priority = 10

    override_action { none {} }   # use managed rule's action

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Override specific rules to Count instead of Block (for testing)
        rule_action_override {
          name          = "SizeRestrictions_BODY"
          action_to_use { count {} }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CoreRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # ─── Rule 3: SQL Injection protection ─────────────────────────────────────
  rule {
    name     = "aws-managed-sql-rules"
    priority = 20

    override_action { none {} }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # ─── Rule 4: Known bad inputs (XSS, log4j, etc.) ─────────────────────────
  rule {
    name     = "aws-managed-bad-inputs"
    priority = 30

    override_action { none {} }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputs"
      sampled_requests_enabled   = true
    }
  }

  # ─── Rule 5: Block specific IPs ───────────────────────────────────────────
  rule {
    name     = "block-bad-ips"
    priority = 5

    action { block {} }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocked_ips.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockedIPs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project}-web-acl"
    sampled_requests_enabled   = true
  }

  tags = merge(local.common_tags, { Name = "${var.project}-web-acl" })
}

# ─── IP Set for blocked IPs ───────────────────────────────────────────────────

resource "aws_wafv2_ip_set" "blocked_ips" {
  name               = "${var.project}-blocked-ips"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = []   # add IPs here: ["1.2.3.4/32"]
  tags               = local.common_tags
}

# ─── Associate WAF with ALB ───────────────────────────────────────────────────

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# ─── WAF Logging ──────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${var.project}"   # must start with aws-waf-logs-
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "waf_arn"        { value = aws_wafv2_web_acl.main.arn }
output "waf_id"         { value = aws_wafv2_web_acl.main.id }
output "blocked_ip_set" { value = aws_wafv2_ip_set.blocked_ips.arn }
