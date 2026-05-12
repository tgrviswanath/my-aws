# Project 0.2 — Linux Foundations Lab
# This project runs locally in Docker — no AWS resources needed.
# Terraform here creates an EC2 instance for practicing Linux on real AWS infrastructure.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "key_name"    { description = "EC2 key pair name for SSH access" }
variable "my_ip"       { description = "Your public IP for SSH access (x.x.x.x/32)" }

locals {
  common_tags = { Project = var.project, Stage = "stage-00", ManagedBy = "terraform" }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group — SSH from your IP only
resource "aws_security_group" "linux_lab" {
  name        = "${var.project}-linux-lab-sg"
  description = "Linux lab — SSH from my IP only"

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  ingress {
    description = "HTTP for Nginx lab"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project}-linux-lab-sg" })
}

# EC2 instance — t3.micro (free tier eligible)
resource "aws_instance" "linux_lab" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.linux_lab.id]

  # User data — install basic tools on launch
  user_data = base64encode(<<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y nginx curl wget vim htop tree
    systemctl enable nginx
    systemctl start nginx
    echo "<h1>Linux Lab — $(hostname)</h1>" > /var/www/html/index.html
  EOF
  )

  tags = merge(local.common_tags, { Name = "${var.project}-linux-lab" })
}

output "instance_id"  { value = aws_instance.linux_lab.id }
output "public_ip"    { value = aws_instance.linux_lab.public_ip }
output "ssh_command"  { value = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.linux_lab.public_ip}" }
output "nginx_url"    { value = "http://${aws_instance.linux_lab.public_ip}" }
