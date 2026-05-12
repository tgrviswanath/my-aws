# Project 6.3 — Jenkins + Terraform Pipeline
# Terraform deploys Jenkins on ECS Fargate with EFS for persistent storage.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"             { default = "us-east-1" }
variable "project"            { default = "handson" }
variable "vpc_id"             { description = "VPC ID" }
variable "public_subnet_ids"  { type = list(string) }
variable "private_subnet_ids" { type = list(string) }

locals {
  name_prefix = "${var.project}-jenkins"
  common_tags = { Project = var.project, Stage = "stage-06", ManagedBy = "terraform" }
}

# ─── EFS for Jenkins home ─────────────────────────────────────────────────────

resource "aws_efs_file_system" "jenkins" {
  encrypted = true
  tags      = merge(local.common_tags, { Name = "${local.name_prefix}-efs" })
}

resource "aws_security_group" "efs" {
  name   = "${local.name_prefix}-efs-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 2049 to_port = 2049 protocol = "tcp" security_groups = [aws_security_group.jenkins.id] }
  egress  { from_port = 0    to_port = 0    protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-efs-sg" })
}

resource "aws_efs_mount_target" "jenkins" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.jenkins.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

# ─── Security Groups ──────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "${local.name_prefix}-alb-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 80   to_port = 80   protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443  to_port = 443  protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0    to_port = 0    protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-sg" })
}

resource "aws_security_group" "jenkins" {
  name   = "${local.name_prefix}-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 8080  to_port = 8080  protocol = "tcp" security_groups = [aws_security_group.alb.id] }
  ingress { from_port = 50000 to_port = 50000 protocol = "tcp" cidr_blocks = ["10.0.0.0/8"] }
  egress  { from_port = 0     to_port = 0     protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sg" })
}

# ─── ALB ──────────────────────────────────────────────────────────────────────

resource "aws_lb" "jenkins" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-alb" })
}

resource "aws_lb_target_group" "jenkins" {
  name        = "${local.name_prefix}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check { path = "/login" healthy_threshold = 2 unhealthy_threshold = 5 interval = 30 timeout = 10 }
  tags = local.common_tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.jenkins.arn
  port              = 80
  protocol          = "HTTP"
  default_action { type = "forward" target_group_arn = aws_lb_target_group.jenkins.arn }
}

# ─── ECS ──────────────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "jenkins" {
  name = "${local.name_prefix}-cluster"
  tags = local.common_tags
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

resource "aws_cloudwatch_log_group" "jenkins" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 7
  tags              = local.common_tags
}

resource "aws_ecs_task_definition" "jenkins" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.task_execution.arn

  volume {
    name = "jenkins-home"
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.jenkins.id
      root_directory = "/"
    }
  }

  container_definitions = jsonencode([{
    name      = "jenkins"
    image     = "jenkins/jenkins:lts-jdk17"
    essential = true
    portMappings = [
      { containerPort = 8080  protocol = "tcp" },
      { containerPort = 50000 protocol = "tcp" }
    ]
    mountPoints = [{
      sourceVolume  = "jenkins-home"
      containerPath = "/var/jenkins_home"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.jenkins.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "jenkins"
      }
    }
  }])

  tags = local.common_tags
}

resource "aws_ecs_service" "jenkins" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.jenkins.id
  task_definition = aws_ecs_task_definition.jenkins.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.jenkins.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.jenkins.arn
    container_name   = "jenkins"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.http, aws_efs_mount_target.jenkins]
  tags       = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "jenkins_url"  { value = "http://${aws_lb.jenkins.dns_name}" }
output "efs_id"       { value = aws_efs_file_system.jenkins.id }
