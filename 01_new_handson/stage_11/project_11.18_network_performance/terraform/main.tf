terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-18" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "public-11-18" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-11-18" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route  { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.igw.id }
  tags   = { Name = "public-rt-11-18" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Cluster Placement Group
resource "aws_placement_group" "cluster" {
  name     = "pg-cluster-11-18"
  strategy = "cluster"
  tags     = { Name = "pg-cluster-11-18" }
}

# Security Group — allow SSH + iperf3 between instances
resource "aws_security_group" "perf" {
  name   = "sg-perf-11-18"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 22;   to_port = 22;   protocol = "tcp"; cidr_blocks = [var.my_ip] }
  ingress { from_port = 5201; to_port = 5201; protocol = "tcp"; cidr_blocks = ["10.0.0.0/16"] }
  ingress { from_port = 5201; to_port = 5201; protocol = "udp"; cidr_blocks = ["10.0.0.0/16"] }
  ingress { from_port = -1;   to_port = -1;   protocol = "icmp"; cidr_blocks = ["10.0.0.0/16"] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";   cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "sg-perf-11-18" }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name"; values = ["al2023-ami-*-x86_64"] }
}

# EC2-A (iperf3 server)
resource "aws_instance" "a" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.perf.id]
  key_name               = var.key_name
  placement_group        = aws_placement_group.cluster.id
  user_data              = "#!/bin/bash\nyum install -y iperf3"
  tags = { Name = "ec2-a-11-18" }
}

# EC2-B (iperf3 client)
resource "aws_instance" "b" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.perf.id]
  key_name               = var.key_name
  placement_group        = aws_placement_group.cluster.id
  user_data              = "#!/bin/bash\nyum install -y iperf3"
  tags = { Name = "ec2-b-11-18" }
}
