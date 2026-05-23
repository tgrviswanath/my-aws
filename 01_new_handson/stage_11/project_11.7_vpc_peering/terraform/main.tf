terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "a" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-a-11-7" }
}

resource "aws_vpc" "b" {
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-b-11-7" }
}

resource "aws_subnet" "a" {
  vpc_id                  = aws_vpc.a.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "subnet-a-11-7" }
}

resource "aws_subnet" "b" {
  vpc_id                  = aws_vpc.b.id
  cidr_block              = "10.1.1.0/24"
  availability_zone       = "${var.region}b"
  map_public_ip_on_launch = true
  tags = { Name = "subnet-b-11-7" }
}

# VPC Peering
resource "aws_vpc_peering_connection" "peer" {
  vpc_id      = aws_vpc.a.id
  peer_vpc_id = aws_vpc.b.id
  auto_accept = true
  tags        = { Name = "pcx-11-7" }
}

# Route tables — add peering routes on BOTH sides
resource "aws_route" "a_to_b" {
  route_table_id            = aws_vpc.a.default_route_table_id
  destination_cidr_block    = "10.1.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

resource "aws_route" "b_to_a" {
  route_table_id            = aws_vpc.b.default_route_table_id
  destination_cidr_block    = "10.0.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}
