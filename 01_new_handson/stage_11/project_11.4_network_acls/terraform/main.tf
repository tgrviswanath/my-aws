terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-4" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "public-11-4" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "private-11-4" }
}

# Public NACL
resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.public.id]
  tags       = { Name = "nacl-public-11-4" }

  ingress { rule_no = 100; action = "allow"; protocol = "tcp"; from_port = 80;   to_port = 80;    cidr_block = "0.0.0.0/0" }
  ingress { rule_no = 110; action = "allow"; protocol = "tcp"; from_port = 443;  to_port = 443;   cidr_block = "0.0.0.0/0" }
  ingress { rule_no = 120; action = "allow"; protocol = "tcp"; from_port = 22;   to_port = 22;    cidr_block = var.my_ip }
  ingress { rule_no = 130; action = "allow"; protocol = "tcp"; from_port = 1024; to_port = 65535; cidr_block = "0.0.0.0/0" }

  egress  { rule_no = 100; action = "allow"; protocol = "tcp"; from_port = 80;   to_port = 80;    cidr_block = "0.0.0.0/0" }
  egress  { rule_no = 110; action = "allow"; protocol = "tcp"; from_port = 443;  to_port = 443;   cidr_block = "0.0.0.0/0" }
  egress  { rule_no = 120; action = "allow"; protocol = "tcp"; from_port = 1024; to_port = 65535; cidr_block = "0.0.0.0/0" }
}

# Private NACL
resource "aws_network_acl" "private" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.private.id]
  tags       = { Name = "nacl-private-11-4" }

  ingress { rule_no = 100; action = "allow"; protocol = "tcp"; from_port = 0;    to_port = 65535; cidr_block = "10.0.1.0/24" }
  ingress { rule_no = 110; action = "allow"; protocol = "tcp"; from_port = 1024; to_port = 65535; cidr_block = "0.0.0.0/0" }

  egress  { rule_no = 100; action = "allow"; protocol = "tcp"; from_port = 0;    to_port = 65535; cidr_block = "10.0.1.0/24" }
  egress  { rule_no = 110; action = "allow"; protocol = "tcp"; from_port = 1024; to_port = 65535; cidr_block = "0.0.0.0/0" }
}
