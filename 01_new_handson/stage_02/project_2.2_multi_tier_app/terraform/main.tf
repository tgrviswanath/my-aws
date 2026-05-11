terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region"   { default = "us-east-1" }
variable "key_name" { description = "EC2 key pair name" }
variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

# ─── Reference VPC outputs from Project 2.1 ──────────────────────────────────
# In a real project, use remote state or data sources.
# Here we use variables for simplicity.

variable "vpc_id"               { description = "VPC ID from project 2.1" }
variable "public_subnet_ids"    { description = "Public subnet IDs" type = list(string) }
variable "private_app_subnet_ids" { description = "Private app subnet IDs" type = list(string) }
variable "private_db_subnet_ids"  { description = "Private DB subnet IDs" type = list(string) }

# ─── Security Groups ──────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "alb-sg"
  vpc_id = var.vpc_id

  ingress { from_port = 80  to_port = 80  protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0   to_port = 0   protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }

  tags = { Name = "alb-sg", Project = "handson" }
}

resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = var.vpc_id

  ingress {
    description     = "HTTP from ALB only"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }

  tags = { Name = "app-sg", Project = "handson" }
}

resource "aws_security_group" "rds" {
  name   = "rds-sg"
  vpc_id = var.vpc_id

  ingress {
    description     = "MySQL from app tier only"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }

  tags = { Name = "rds-sg", Project = "handson" }
}

# ─── ALB ──────────────────────────────────────────────────────────────────────

resource "aws_lb" "app" {
  name               = "app-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  tags = { Name = "app-alb", Project = "handson" }
}

resource "aws_lb_target_group" "app" {
  name     = "app-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }

  tags = { Name = "app-tg", Project = "handson" }
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

# ─── Launch Template ──────────────────────────────────────────────────────────

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name" values = ["al2023-ami-*-x86_64"] }
}

resource "aws_launch_template" "app" {
  name_prefix   = "app-lt-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y nginx
    systemctl start nginx
    systemctl enable nginx
    HOSTNAME=$(hostname)
    AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    cat > /usr/share/nginx/html/index.html << HTML
    <h1>App Server: $HOSTNAME</h1><p>AZ: $AZ</p>
    HTML
    echo "OK" > /usr/share/nginx/html/health
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = { Name = "app-server", Project = "handson" }
  }
}

# ─── Auto Scaling Group ───────────────────────────────────────────────────────

resource "aws_autoscaling_group" "app" {
  name                = "app-asg"
  desired_capacity    = 2
  min_size            = 1
  max_size            = 4
  vpc_zone_identifier = var.private_app_subnet_ids
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  tag {
    key                 = "Project"
    value               = "handson"
    propagate_at_launch = true
  }
}

# ─── RDS ──────────────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "rds-subnet-group"
  subnet_ids = var.private_db_subnet_ids
  tags       = { Project = "handson" }
}

resource "aws_db_instance" "mysql" {
  identifier             = "app-mysql"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "appdb"
  username               = "admin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  tags                   = { Project = "handson" }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "alb_dns_name"   { value = aws_lb.app.dns_name }
output "rds_endpoint"   { value = aws_db_instance.mysql.endpoint }
