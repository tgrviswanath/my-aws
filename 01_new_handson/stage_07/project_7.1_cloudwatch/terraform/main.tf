terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"       { default = "us-east-1" }
variable "project"      { default = "handson" }
variable "alert_email"  { description = "Email for alarm notifications" }
variable "alb_arn_suffix" { description = "ALB ARN suffix (from ALB ARN)" }
variable "ecs_cluster"  { default = "handson-cluster" }
variable "ecs_service"  { default = "handson-flask-api-service" }

locals {
  common_tags = { Project = var.project, Stage = "stage-07", ManagedBy = "terraform" }
}

# ─── SNS Topic for Alerts ─────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-monitoring-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── ECS Alarms ───────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project}-ecs-cpu-high"
  alarm_description   = "ECS CPU utilization > 80%"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  statistic           = "Average"
  period              = 300
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster
    ServiceName = var.ecs_service
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.project}-ecs-memory-high"
  alarm_description   = "ECS memory utilization > 85%"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  statistic           = "Average"
  period              = 300
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster
    ServiceName = var.ecs_service
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_task_count_low" {
  alarm_name          = "${var.project}-ecs-task-count-low"
  alarm_description   = "ECS running task count below desired"
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  statistic           = "Average"
  period              = 60
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = var.ecs_cluster
    ServiceName = var.ecs_service
  }

  tags = local.common_tags
}

# ─── ALB Alarms ───────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "${var.project}-alb-5xx-errors"
  alarm_description   = "ALB 5xx error rate > 10/min"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  statistic           = "Sum"
  period              = 60
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alb_latency_high" {
  alarm_name          = "${var.project}-alb-latency-high"
  alarm_description   = "ALB p99 latency > 2 seconds"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  extended_statistic  = "p99"
  period              = 300
  threshold           = 2
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = local.common_tags
}

# ─── Composite Alarm (reduce noise) ──────────────────────────────────────────

resource "aws_cloudwatch_composite_alarm" "service_degraded" {
  alarm_name        = "${var.project}-service-degraded"
  alarm_description = "Service is degraded: high CPU AND high latency"

  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.ecs_cpu_high.alarm_name}) AND ALARM(${aws_cloudwatch_metric_alarm.alb_latency_high.alarm_name})"

  alarm_actions = [aws_sns_topic.alerts.arn]
  tags          = local.common_tags
}

# ─── CloudWatch Dashboard ─────────────────────────────────────────────────────

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x = 0; y = 0; width = 12; height = 6
        properties = {
          title  = "ECS CPU & Memory Utilization"
          period = 300
          stat   = "Average"
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", var.ecs_cluster, "ServiceName", var.ecs_service],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", var.ecs_cluster, "ServiceName", var.ecs_service]
          ]
          yAxis = { left = { min = 0, max = 100 } }
        }
      },
      {
        type   = "metric"
        x = 12; y = 0; width = 12; height = 6
        properties = {
          title  = "ALB Request Count & Latency"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum" }],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p99", yAxis = "right" }]
          ]
        }
      },
      {
        type   = "metric"
        x = 0; y = 6; width = 12; height = 6
        properties = {
          title  = "ALB HTTP Status Codes"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", color = "#2ca02c" }],
            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", color = "#ff7f0e" }],
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count",    "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", color = "#d62728" }]
          ]
        }
      },
      {
        type   = "alarm"
        x = 12; y = 6; width = 12; height = 6
        properties = {
          title  = "Alarm Status"
          alarms = [
            aws_cloudwatch_metric_alarm.ecs_cpu_high.arn,
            aws_cloudwatch_metric_alarm.ecs_memory_high.arn,
            aws_cloudwatch_metric_alarm.alb_5xx_errors.arn,
            aws_cloudwatch_metric_alarm.alb_latency_high.arn,
            aws_cloudwatch_metric_alarm.ecs_task_count_low.arn,
          ]
        }
      }
    ]
  })
}

# ─── Log Insights Saved Queries ───────────────────────────────────────────────

resource "aws_cloudwatch_query_definition" "error_rate" {
  name = "${var.project}/error-rate-last-hour"

  log_group_names = ["/ecs/${var.project}-flask-api"]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /ERROR|Exception|error/
    | stats count(*) as error_count by bin(5m)
    | sort @timestamp desc
  EOT
}

resource "aws_cloudwatch_query_definition" "slow_requests" {
  name = "${var.project}/slow-requests"

  log_group_names = ["/ecs/${var.project}-flask-api"]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /duration/
    | parse @message "duration=* ms" as duration_ms
    | filter duration_ms > 1000
    | sort duration_ms desc
    | limit 20
  EOT
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "dashboard_url" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
output "sns_topic_arn" { value = aws_sns_topic.alerts.arn }
