terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  alias  = "east"
  region = "us-east-1"
}

provider "aws" {
  alias  = "west"
  region = "us-west-2"
}

# VPC East
resource "aws_vpc" "east" {
  provider             = aws.east
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-east-11-10" }
}

resource "aws_subnet" "east" {
  provider                = aws.east
  vpc_id                  = aws_vpc.east.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags = { Name = "subnet-east-11-10" }
}

# VPC West
resource "aws_vpc" "west" {
  provider             = aws.west
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-west-11-10" }
}

resource "aws_subnet" "west" {
  provider                = aws.west
  vpc_id                  = aws_vpc.west.id
  cidr_block              = "10.1.1.0/24"
  availability_zone       = "us-west-2a"
  map_public_ip_on_launch = true
  tags = { Name = "subnet-west-11-10" }
}

# Inter-region VPC Peering
resource "aws_vpc_peering_connection" "peer" {
  provider    = aws.east
  vpc_id      = aws_vpc.east.id
  peer_vpc_id = aws_vpc.west.id
  peer_region = "us-west-2"
  tags        = { Name = "pcx-east-west-11-10" }
}

resource "aws_vpc_peering_connection_accepter" "peer" {
  provider                  = aws.west
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
  auto_accept               = true
}

# Routes on both sides
resource "aws_route" "east_to_west" {
  provider                  = aws.east
  route_table_id            = aws_vpc.east.default_route_table_id
  destination_cidr_block    = "10.1.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

resource "aws_route" "west_to_east" {
  provider                  = aws.west
  route_table_id            = aws_vpc.west.default_route_table_id
  destination_cidr_block    = "10.0.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}
