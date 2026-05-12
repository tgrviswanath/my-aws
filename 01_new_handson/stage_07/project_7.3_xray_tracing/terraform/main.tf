# Project 7.3 — AWS X-Ray Distributed Tracing
# Adds X-Ray daemon sidecar to ECS task definition and grants IAM permissions.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "ecr_image_url"   { description = "Flask API ECR image URL" }
variable "vpc_id"          { description = "VPC ID" }
variable "subnet_ids"      { type = list(string) }
variable "alb_sg_id"       { description = "ALB security group ID" }

locals {
  name_prefix = "${var.project}-xray"
  common_tags = { Project = var.project, Stage = "stage-07", ManagedBy = "terraform" }
}

# ─── IAM Role with X-Ray permissions ─────────────────────────────────────────

resource "aws_iam_role" "task" {
  name = "${local.name_prefix}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "ecs-tasks.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "xray" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role" "task_execution" {
  name = "${local.name_prefix}-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "ecs-tasks.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ─── CloudWatch Log Groups ────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}-app"
  retention_in_days = 7
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "xray" {
  name              = "/ecs/${local.name_prefix}-xray-daemon"
  retention_in_days = 7
  tags              = local.common_tags
}

# ─── Security Group ───────────────────────────────────────────────────────────

resource "aws_security_group" "tasks" {
  name   = "${local.name_prefix}-tasks-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 5000 to_port = 5000 protocol = "tcp" security_groups = [var.alb_sg_id] }
  egress  { from_port = 0    to_port = 0    protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-tasks-sg" })
}

# ─── ECS Task Definition with X-Ray Sidecar ──────────────────────────────────

resource "aws_ecs_task_definition" "app_with_xray" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    # Main application container
    {
      name      = "flask-api"
      image     = var.ecr_image_url
      essential = true
      portMappings = [{ containerPort = 5000 protocol = "tcp" }]
      environment = [
        { name = "AWS_XRAY_DAEMON_ADDRESS", value = "127.0.0.1:2000" },
        { name = "APP_ENV", value = "production" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "app"
        }
      }
    },
    # X-Ray daemon sidecar
    {
      name      = "xray-daemon"
      image     = "amazon/aws-xray-daemon:latest"
      essential = false
      command   = ["--local-mode"]
      portMappings = [{ containerPort = 2000 protocol = "udp" }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.xray.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "xray"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-task" })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "task_definition_arn" { value = aws_ecs_task_definition.app_with_xray.arn }
output "task_role_arn"       { value = aws_iam_role.task.arn }
output "xray_console_url"    { value = "https://${var.region}.console.aws.amazon.com/xray/home?region=${var.region}#/service-map" }
