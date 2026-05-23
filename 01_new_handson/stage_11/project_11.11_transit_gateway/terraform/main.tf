terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

# Three VPCs
resource "aws_vpc" "a" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-a-11-11" }
}
resource "aws_vpc" "b" {
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-b-11-11" }
}
resource "aws_vpc" "c" {
  cidr_block           = "10.2.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-c-11-11" }
}

# One subnet per VPC
resource "aws_subnet" "a" {
  vpc_id            = aws_vpc.a.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "subnet-a-11-11" }
}
resource "aws_subnet" "b" {
  vpc_id            = aws_vpc.b.id
  cidr_block        = "10.1.1.0/24"
  availability_zone = "${var.region}b"
  tags = { Name = "subnet-b-11-11" }
}
resource "aws_subnet" "c" {
  vpc_id            = aws_vpc.c.id
  cidr_block        = "10.2.1.0/24"
  availability_zone = "${var.region}c"
  tags = { Name = "subnet-c-11-11" }
}

# Transit Gateway
resource "aws_ec2_transit_gateway" "tgw" {
  description                     = "TGW for project 11.11"
  amazon_side_asn                 = 64512
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  tags = { Name = "tgw-11-11" }
}

# TGW Attachments
resource "aws_ec2_transit_gateway_vpc_attachment" "a" {
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.a.id
  subnet_ids         = [aws_subnet.a.id]
  tags = { Name = "tgw-attach-a-11-11" }
}
resource "aws_ec2_transit_gateway_vpc_attachment" "b" {
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.b.id
  subnet_ids         = [aws_subnet.b.id]
  tags = { Name = "tgw-attach-b-11-11" }
}
resource "aws_ec2_transit_gateway_vpc_attachment" "c" {
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.c.id
  subnet_ids         = [aws_subnet.c.id]
  tags = { Name = "tgw-attach-c-11-11" }
}

# VPC route tables — each VPC routes to the other two via TGW
resource "aws_route" "a_to_b" {
  route_table_id         = aws_vpc.a.default_route_table_id
  destination_cidr_block = "10.1.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.a]
}
resource "aws_route" "a_to_c" {
  route_table_id         = aws_vpc.a.default_route_table_id
  destination_cidr_block = "10.2.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.a]
}
resource "aws_route" "b_to_a" {
  route_table_id         = aws_vpc.b.default_route_table_id
  destination_cidr_block = "10.0.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.b]
}
resource "aws_route" "b_to_c" {
  route_table_id         = aws_vpc.b.default_route_table_id
  destination_cidr_block = "10.2.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.b]
}
resource "aws_route" "c_to_a" {
  route_table_id         = aws_vpc.c.default_route_table_id
  destination_cidr_block = "10.0.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.c]
}
resource "aws_route" "c_to_b" {
  route_table_id         = aws_vpc.c.default_route_table_id
  destination_cidr_block = "10.1.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.tgw.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.c]
}
