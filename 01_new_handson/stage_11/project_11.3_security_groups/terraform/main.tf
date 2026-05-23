terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-3" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "public-subnet-11-3" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "private-subnet-11-3" }
}

# Security Groups
resource "aws_security_group" "alb" {
  name   = "alb-sg-11-3"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 80;  to_port = 80;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;   to_port = 0;   protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "alb-sg-11-3" }
}

resource "aws_security_group" "web" {
  name   = "web-sg-11-3"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  ingress { from_port = 22; to_port = 22; protocol = "tcp"; cidr_blocks = [var.my_ip] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "web-sg-11-3" }
}

resource "aws_security_group" "app" {
  name   = "app-sg-11-3"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 8080; to_port = 8080; protocol = "tcp"; security_groups = [aws_security_group.web.id] }
  ingress { from_port = 22;   to_port = 22;   protocol = "tcp"; security_groups = [aws_security_group.web.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "app-sg-11-3" }
}

resource "aws_security_group" "db" {
  name   = "db-sg-11-3"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 3306; to_port = 3306; protocol = "tcp"; security_groups = [aws_security_group.app.id] }
  ingress { from_port = 22;   to_port = 22;   protocol = "tcp"; security_groups = [aws_security_group.app.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "db-sg-11-3" }
}
