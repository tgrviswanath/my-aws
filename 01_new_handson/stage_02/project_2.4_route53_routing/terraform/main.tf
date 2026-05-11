terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = "us-east-1" }

variable "hosted_zone_id"  { description = "Route53 hosted zone ID" }
variable "domain_name"     { description = "Your domain (e.g. example.com)" }
variable "primary_ip"      { description = "Primary EC2 public IP" }
variable "secondary_ip"    { description = "Secondary EC2 public IP" }
variable "alert_sns_arn"   { description = "SNS topic ARN for health check alerts" }

# ─── Health Check ─────────────────────────────────────────────────────────────

resource "aws_route53_health_check" "primary" {
  fqdn              = "primary.${var.domain_name}"
  port              = 80
  type              = "HTTP"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30

  tags = { Name = "primary-health-check", Project = "handson" }
}

resource "aws_cloudwatch_metric_alarm" "health_check" {
  alarm_name          = "route53-primary-health"
  alarm_description   = "Primary endpoint health check failed"
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  statistic           = "Minimum"
  period              = 60
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  alarm_actions       = [var.alert_sns_arn]

  dimensions = {
    HealthCheckId = aws_route53_health_check.primary.id
  }
}

# ─── Weighted Routing (A/B test) ──────────────────────────────────────────────

resource "aws_route53_record" "weighted_v1" {
  zone_id        = var.hosted_zone_id
  name           = "app.${var.domain_name}"
  type           = "A"
  set_identifier = "v1-primary"
  ttl            = 60

  weighted_routing_policy { weight = 90 }

  records = [var.primary_ip]
}

resource "aws_route53_record" "weighted_v2" {
  zone_id        = var.hosted_zone_id
  name           = "app.${var.domain_name}"
  type           = "A"
  set_identifier = "v2-canary"
  ttl            = 60

  weighted_routing_policy { weight = 10 }

  records = [var.secondary_ip]
}

# ─── Failover Routing ─────────────────────────────────────────────────────────

resource "aws_route53_record" "failover_primary" {
  zone_id        = var.hosted_zone_id
  name           = "failover.${var.domain_name}"
  type           = "A"
  set_identifier = "primary"
  ttl            = 30
  health_check_id = aws_route53_health_check.primary.id

  failover_routing_policy { type = "PRIMARY" }

  records = [var.primary_ip]
}

resource "aws_route53_record" "failover_secondary" {
  zone_id        = var.hosted_zone_id
  name           = "failover.${var.domain_name}"
  type           = "A"
  set_identifier = "secondary"
  ttl            = 30

  failover_routing_policy { type = "SECONDARY" }

  records = [var.secondary_ip]
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "weighted_endpoint"  { value = "app.${var.domain_name}" }
output "failover_endpoint"  { value = "failover.${var.domain_name}" }
output "health_check_id"    { value = aws_route53_health_check.primary.id }
