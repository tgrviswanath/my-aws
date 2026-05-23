terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

# Dual-stack VPC
resource "aws_vpc" "main" {
  cidr_block                       = "10.0.0.0/16"
  assign_generated_ipv6_cidr_block = true
  enable_dns_hostnames             = true
  tags = { Name = "vpc-11-19" }
}

# Public subnet — dual-stack
resource "aws_subnet" "public" {
  vpc_id                          = aws_vpc.main.id
  cidr_block                      = "10.0.1.0/24"
  availability_zone               = "${var.region}a"
  map_public_ip_on_launch         = true
  assign_ipv6_address_on_creation = true
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 0)
  tags = { Name = "public-ipv6-11-19" }
}

# Private subnet — dual-stack
resource "aws_subnet" "private" {
  vpc_id                          = aws_vpc.main.id
  cidr_block                      = "10.0.2.0/24"
  availability_zone               = "${var.region}a"
  assign_ipv6_address_on_creation = true
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 1)
  tags = { Name = "private-ipv6-11-19" }
}

# Internet Gateway (IPv4 + IPv6 for public subnet)
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-11-19" }
}

# Egress-Only Internet Gateway (IPv6 outbound for private subnet)
resource "aws_egress_only_internet_gateway" "eigw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "eigw-11-19" }
}

# Public route table — IPv4 + IPv6 via IGW
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  route {
    ipv6_cidr_block = "::/0"
    gateway_id      = aws_internet_gateway.igw.id
  }
  tags = { Name = "public-rt-11-19" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Private route table — IPv6 via EIGW (outbound only)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    ipv6_cidr_block        = "::/0"
    egress_only_gateway_id = aws_egress_only_internet_gateway.eigw.id
  }
  tags = { Name = "private-rt-11-19" }
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# Security Group — allow SSH + ICMPv6 for both IPv4 and IPv6
resource "aws_security_group" "ec2" {
  name   = "sg-ec2-11-19"
  vpc_id = aws_vpc.main.id

  ingress { from_port = 22; to_port = 22; protocol = "tcp"; cidr_blocks      = [var.my_ip] }
  ingress { from_port = 22; to_port = 22; protocol = "tcp"; ipv6_cidr_blocks = ["::/0"] }
  ingress { from_port = -1; to_port = -1; protocol = "58";  ipv6_cidr_blocks = ["::/0"] }  # ICMPv6
  ingress { from_port = -1; to_port = -1; protocol = "icmp"; cidr_blocks     = ["10.0.0.0/16"] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  cidr_blocks      = ["0.0.0.0/0"] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  ipv6_cidr_blocks = ["::/0"] }
  tags = { Name = "sg-ec2-11-19" }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name"; values = ["al2023-ami-*-x86_64"] }
}

resource "aws_instance" "public" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = var.key_name
  tags = { Name = "ec2-public-11-19" }
}

resource "aws_instance" "private" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.private.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = var.key_name
  tags = { Name = "ec2-private-11-19" }
}
