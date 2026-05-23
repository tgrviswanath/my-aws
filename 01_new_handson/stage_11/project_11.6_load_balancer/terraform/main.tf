terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

# ALB Security Group
resource "aws_security_group" "alb" {
  name   = "alb-sg-11-6"
  vpc_id = var.vpc_id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "alb-sg-11-6" }
}

# Target Group
resource "aws_lb_target_group" "web" {
  name     = "tg-web-11-6"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200"
  }
  tags = { Name = "tg-web-11-6" }
}

# ALB
resource "aws_lb" "alb" {
  name               = "alb-11-6"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = { Name = "alb-11-6" }
}

# Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}
