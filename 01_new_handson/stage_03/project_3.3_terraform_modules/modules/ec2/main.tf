# modules/ec2/main.tf
# Reusable EC2 module — ALB + Launch Template + ASG + Security Groups
# Accepts inputs from the calling environment, exports ALB DNS and SG IDs.

# ─── Variables ────────────────────────────────────────────────────────────────

variable "name_prefix"       { type = string }
variable "vpc_id"            { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "app_subnet_ids"    { type = list(string) }
variable "environment"       { type = string }
variable "key_name"          { type = string }
variable "my_ip" {
  type        = string
  description = "Your IP for SSH access e.g. 1.2.3.4/32"
}
variable "instance_type"    { default = "t3.micro" }
variable "desired_capacity" { default = 1 }
variable "min_size"         { default = 1 }
variable "max_size"         { default = 2 }
variable "common_tags" {
  type    = map(string)
  default = {}
}

# ─── Security Group: ALB ──────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "${var.name_prefix}-alb-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-alb-sg" })
}

# ─── Security Group: App (EC2) ────────────────────────────────────────────────

resource "aws_security_group" "app" {
  name   = "${var.name_prefix}-app-sg"
  vpc_id = var.vpc_id

  ingress {
    description     = "HTTP from ALB only"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-app-sg" })
}

# ─── ALB ──────────────────────────────────────────────────────────────────────

resource "aws_lb" "app" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = merge(var.common_tags, { Name = "${var.name_prefix}-alb" })
}

resource "aws_lb_target_group" "app" {
  name     = "${var.name_prefix}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-tg" })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ─── AMI Data Source ──────────────────────────────────────────────────────────

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# ─── Launch Template ──────────────────────────────────────────────────────────

resource "aws_launch_template" "app" {
  name_prefix            = "${var.name_prefix}-lt-"
  image_id               = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y && yum install -y nginx
    systemctl start nginx && systemctl enable nginx
    HOSTNAME=$(hostname)
    AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    echo "<h1>$HOSTNAME</h1><p>AZ: $AZ | Env: ${var.environment}</p>" > /usr/share/nginx/html/index.html
    echo "OK" > /usr/share/nginx/html/health
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.common_tags, { Name = "${var.name_prefix}-app" })
  }
}

# ─── Auto Scaling Group ───────────────────────────────────────────────────────

resource "aws_autoscaling_group" "app" {
  name                      = "${var.name_prefix}-asg"
  desired_capacity          = var.desired_capacity
  min_size                  = var.min_size
  max_size                  = var.max_size
  vpc_zone_identifier       = var.app_subnet_ids
  target_group_arns         = [aws_lb_target_group.app.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.name_prefix}-app"
    propagate_at_launch = true
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "alb_dns_name" { value = aws_lb.app.dns_name }
output "alb_url"      { value = "http://${aws_lb.app.dns_name}" }
output "app_sg_id"    { value = aws_security_group.app.id }
output "alb_sg_id"    { value = aws_security_group.alb.id }
