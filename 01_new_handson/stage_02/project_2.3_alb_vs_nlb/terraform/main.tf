terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" { region = var.region }

variable "region"            { default = "us-east-1" }
variable "vpc_id"            { description = "VPC ID from project 2.1" }
variable "public_subnet_ids" { type = list(string) }
variable "app_sg_id"         { description = "App EC2 security group ID" }
variable "instance_ids"      { type = list(string) description = "EC2 instance IDs for target groups" }

# ─── ALB ──────────────────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "compare-alb-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 80 to_port = 80 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0  to_port = 0  protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "compare-alb-sg" }
}

resource "aws_lb" "alb" {
  name               = "compare-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = { Name = "compare-alb", Project = "handson" }
}

resource "aws_lb_target_group" "web" {
  name     = "tg-web"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check { path = "/health" }
}

resource "aws_lb_target_group" "api" {
  name     = "tg-api"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check { path = "/health" }
}

resource "aws_lb_listener" "alb_http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# Path-based routing rule: /api/* → tg-api
resource "aws_lb_listener_rule" "api_path" {
  listener_arn = aws_lb_listener.alb_http.arn
  priority     = 10

  condition {
    path_pattern { values = ["/api/*"] }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ─── NLB ──────────────────────────────────────────────────────────────────────

resource "aws_eip" "nlb" {
  count  = length(var.public_subnet_ids)
  domain = "vpc"
}

resource "aws_lb" "nlb" {
  name               = "compare-nlb"
  internal           = false
  load_balancer_type = "network"

  dynamic "subnet_mapping" {
    for_each = var.public_subnet_ids
    content {
      subnet_id     = subnet_mapping.value
      allocation_id = aws_eip.nlb[subnet_mapping.key].id
    }
  }

  tags = { Name = "compare-nlb", Project = "handson" }
}

resource "aws_lb_target_group" "nlb_tg" {
  name     = "tg-nlb"
  port     = 80
  protocol = "TCP"
  vpc_id   = var.vpc_id
}

resource "aws_lb_listener" "nlb_tcp" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_tg.arn
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "alb_dns"      { value = aws_lb.alb.dns_name }
output "nlb_dns"      { value = aws_lb.nlb.dns_name }
output "nlb_eips"     { value = aws_eip.nlb[*].public_ip }
