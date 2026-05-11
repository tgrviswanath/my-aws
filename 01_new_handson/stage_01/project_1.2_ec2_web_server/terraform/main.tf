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

variable "region"      { default = "us-east-1" }
variable "my_ip"       { description = "Your IP address for SSH access (e.g. 1.2.3.4/32)" }
variable "key_name"    { description = "Name of existing EC2 key pair" }

# Latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# Security Group
resource "aws_security_group" "web_server" {
  name        = "web-server-sg"
  description = "Allow HTTP, HTTPS, SSH"

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from my IP only"
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

  tags = { Project = "handson", Stage = "stage-01" }
}

# EC2 Instance
resource "aws_instance" "web_server" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.web_server.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y nginx
    systemctl start nginx
    systemctl enable nginx
    echo "<h1>Hello from EC2 + Terraform!</h1>" > /usr/share/nginx/html/index.html
  EOF

  tags = {
    Name        = "web-server-01"
    Project     = "handson"
    Stage       = "stage-01"
    Environment = "learning"
  }
}

output "instance_public_ip"  { value = aws_instance.web_server.public_ip }
output "instance_public_dns" { value = aws_instance.web_server.public_dns }
output "ssh_command"         { value = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.web_server.public_ip}" }
