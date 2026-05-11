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

variable "region" { default = "us-east-1" }

variable "vpc_cidr" { default = "10.0.0.0/16" }

variable "azs" {
  default = ["us-east-1a", "us-east-1b"]
}

# ─── VPC ──────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "handson-vpc", Project = "handson", Stage = "stage-02" }
}

# ─── Subnets ──────────────────────────────────────────────────────────────────

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name    = "public-subnet-${count.index == 0 ? "a" : "b"}"
    Tier    = "public"
    Project = "handson"
  }
}

resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 3}.0/24"
  availability_zone = var.azs[count.index]

  tags = {
    Name    = "private-app-${count.index == 0 ? "a" : "b"}"
    Tier    = "app"
    Project = "handson"
  }
}

resource "aws_subnet" "private_db" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 5}.0/24"
  availability_zone = var.azs[count.index]

  tags = {
    Name    = "private-db-${count.index == 0 ? "a" : "b"}"
    Tier    = "db"
    Project = "handson"
  }
}

# ─── Internet Gateway ─────────────────────────────────────────────────────────

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "handson-igw", Project = "handson" }
}

# ─── NAT Gateway (single, in public-subnet-a) ────────────────────────────────

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "handson-nat-eip", Project = "handson" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
  tags          = { Name = "handson-nat", Project = "handson" }
}

# ─── Route Tables ─────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "public-rt", Project = "handson" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = { Name = "private-rt", Project = "handson" }
}

resource "aws_route_table_association" "private_app" {
  count          = 2
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_db" {
  count          = 2
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private.id
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "vpc_id"              { value = aws_vpc.main.id }
output "public_subnet_ids"   { value = aws_subnet.public[*].id }
output "private_app_subnet_ids" { value = aws_subnet.private_app[*].id }
output "private_db_subnet_ids"  { value = aws_subnet.private_db[*].id }
output "nat_gateway_ip"      { value = aws_eip.nat.public_ip }
