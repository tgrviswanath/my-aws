terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-11-5" }
}

locals {
  subnets = {
    "web-public-a"  = { cidr = "10.0.1.0/24", az = "a", public = true }
    "web-public-b"  = { cidr = "10.0.2.0/24", az = "b", public = true }
    "app-private-a" = { cidr = "10.0.3.0/24", az = "a", public = false }
    "app-private-b" = { cidr = "10.0.4.0/24", az = "b", public = false }
    "db-private-a"  = { cidr = "10.0.5.0/24", az = "a", public = false }
    "db-private-b"  = { cidr = "10.0.6.0/24", az = "b", public = false }
  }
}

resource "aws_subnet" "all" {
  for_each                = local.subnets
  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr
  availability_zone       = "${var.region}${each.value.az}"
  map_public_ip_on_launch = each.value.public
  tags = { Name = each.key }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-11-5" }
}

resource "aws_eip" "nat_a" { domain = "vpc" }
resource "aws_eip" "nat_b" { domain = "vpc" }

resource "aws_nat_gateway" "nat_a" {
  allocation_id = aws_eip.nat_a.id
  subnet_id     = aws_subnet.all["web-public-a"].id
  tags          = { Name = "nat-11-5-a" }
  depends_on    = [aws_internet_gateway.igw]
}

resource "aws_nat_gateway" "nat_b" {
  allocation_id = aws_eip.nat_b.id
  subnet_id     = aws_subnet.all["web-public-b"].id
  tags          = { Name = "nat-11-5-b" }
  depends_on    = [aws_internet_gateway.igw]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.igw.id }
  tags = { Name = "public-rt-11-5" }
}

resource "aws_route_table_association" "pub_a" {
  subnet_id      = aws_subnet.all["web-public-a"].id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "pub_b" {
  subnet_id      = aws_subnet.all["web-public-b"].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_a" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; nat_gateway_id = aws_nat_gateway.nat_a.id }
  tags = { Name = "private-rt-a-11-5" }
}

resource "aws_route_table" "private_b" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; nat_gateway_id = aws_nat_gateway.nat_b.id }
  tags = { Name = "private-rt-b-11-5" }
}

resource "aws_route_table_association" "priv_app_a" {
  subnet_id      = aws_subnet.all["app-private-a"].id
  route_table_id = aws_route_table.private_a.id
}
resource "aws_route_table_association" "priv_app_b" {
  subnet_id      = aws_subnet.all["app-private-b"].id
  route_table_id = aws_route_table.private_b.id
}
resource "aws_route_table_association" "priv_db_a" {
  subnet_id      = aws_subnet.all["db-private-a"].id
  route_table_id = aws_route_table.private_a.id
}
resource "aws_route_table_association" "priv_db_b" {
  subnet_id      = aws_subnet.all["db-private-b"].id
  route_table_id = aws_route_table.private_b.id
}
