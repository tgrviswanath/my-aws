terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"       { default = "us-east-1" }
variable "project"      { default = "handson" }
variable "ecr_image_url" { description = "Full ECR image URL with tag" }
variable "vpc_id"        { description = "VPC ID" }
variable "public_subnet_ids"  { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "desired_count" { default = 2 }

locals {
  name_prefix = "${var.project}-flask-api"
  common_tags = { Project = var.project, Stage = "stage-05", ManagedBy = "terraform" }
}

# ─── CloudWatch Log Group ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 7
  tags              = local.common_tags
}

# ─── IAM Roles ────────────────────────────────────────────────────────────────

# Task Execution Role — ECS infrastructure (pull image, write logs)
resource "aws_iam_role" "task_execution" {
  name = "${local.name_prefix}-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "ecs-tasks.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role — application permissions (what your code can do)
resource "aws_iam_role" "task" {
  name = "${local.name_prefix}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "ecs-tasks.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

# ─── Security Groups ──────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "${local.name_prefix}-alb-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 80  to_port = 80  protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0   to_port = 0   protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-sg" })
}

resource "aws_security_group" "tasks" {
  name   = "${local.name_prefix}-tasks-sg"
  vpc_id = var.vpc_id
  ingress {
    description     = "From ALB only"
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-tasks-sg" })
}

# ─── ALB ──────────────────────────────────────────────────────────────────────

resource "aws_lb" "app" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-alb" })
}

resource "aws_lb_target_group" "app" {
  name        = "${local.name_prefix}-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"   # Required for Fargate (awsvpc network mode)

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-tg" })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"
  default_action { type = "forward" target_group_arn = aws_lb_target_group.app.arn }
}

# ─── ECS Cluster ──────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, { Name = "${var.project}-cluster" })
}

# ─── Task Definition ──────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "app" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"   # Required for Fargate
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"      # 0.25 vCPU
  memory                   = "512"      # 512 MB
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "flask-api"
    image     = var.ecr_image_url
    essential = true

    portMappings = [{
      containerPort = 5000
      protocol      = "tcp"
    }]

    environment = [
      { name = "APP_ENV",     value = "production" },
      { name = "APP_VERSION", value = "1.0.0" },
      { name = "PORT",        value = "5000" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:5000/health')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
  }])

  tags = merge(local.common_tags, { Name = local.name_prefix })
}

# ─── ECS Service ──────────────────────────────────────────────────────────────

resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "flask-api"
    container_port   = 5000
  }

  deployment_configuration {
    minimum_healthy_percent = 50
    maximum_percent         = 200
  }

  depends_on = [aws_lb_listener.http]
  tags       = merge(local.common_tags, { Name = "${local.name_prefix}-service" })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "alb_url"          { value = "http://${aws_lb.app.dns_name}" }
output "cluster_name"     { value = aws_ecs_cluster.main.name }
output "service_name"     { value = aws_ecs_service.app.name }
output "log_group"        { value = aws_cloudwatch_log_group.app.name }
