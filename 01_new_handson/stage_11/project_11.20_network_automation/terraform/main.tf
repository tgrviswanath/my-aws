terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    # Fill in after creating the bucket:
    # bucket         = "tf-state-11-20-<ACCOUNT_ID>"
    # key            = "stage11/project-11-20/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "tf-lock-11-20"
    # encrypt        = true
  }
}
provider "aws" { region = var.region }

# ── Reusable VPC Module (inline for simplicity) ──────────────

locals {
  name_prefix = "${var.environment}-11-20"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = {
    Name        = "vpc-${local.name_prefix}"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = "${var.region}${count.index == 0 ? "a" : "b"}"
  map_public_ip_on_launch = true
  tags = {
    Name        = "public-${local.name_prefix}-${count.index + 1}"
    Environment = var.environment
    Tier        = "public"
  }
}

resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 3)
  availability_zone = "${var.region}${count.index == 0 ? "a" : "b"}"
  tags = {
    Name        = "private-app-${local.name_prefix}-${count.index + 1}"
    Environment = var.environment
    Tier        = "app"
  }
}

resource "aws_subnet" "private_db" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 5)
  availability_zone = "${var.region}${count.index == 0 ? "a" : "b"}"
  tags = {
    Name        = "private-db-${local.name_prefix}-${count.index + 1}"
    Environment = var.environment
    Tier        = "db"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name        = "igw-${local.name_prefix}"
    Environment = var.environment
  }
}

resource "aws_eip" "nat" {
  count  = var.enable_nat ? 1 : 0
  domain = "vpc"
}

resource "aws_nat_gateway" "nat" {
  count         = var.enable_nat ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  tags = {
    Name        = "nat-${local.name_prefix}"
    Environment = var.environment
  }
  depends_on = [aws_internet_gateway.igw]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route  { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.igw.id }
  tags = { Name = "public-rt-${local.name_prefix}"; Environment = var.environment }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  dynamic "route" {
    for_each = var.enable_nat ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat[0].id
    }
  }
  tags = { Name = "private-rt-${local.name_prefix}"; Environment = var.environment }
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
