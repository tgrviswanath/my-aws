terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

# ── PRIMARY REGION ──────────────────────────────────────────
resource "aws_vpc" "primary" {
  provider             = aws.primary
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-primary-11-16" }
}

resource "aws_subnet" "primary_pub_a" {
  provider                = aws.primary
  vpc_id                  = aws_vpc.primary.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags = { Name = "primary-pub-a-11-16" }
}

resource "aws_subnet" "primary_pub_b" {
  provider                = aws.primary
  vpc_id                  = aws_vpc.primary.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true
  tags = { Name = "primary-pub-b-11-16" }
}

resource "aws_internet_gateway" "primary" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id
  tags     = { Name = "igw-primary-11-16" }
}

resource "aws_lb" "primary" {
  provider           = aws.primary
  name               = "alb-primary-11-16"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.primary_pub_a.id, aws_subnet.primary_pub_b.id]
  tags               = { Name = "alb-primary-11-16" }
}

# ── DR REGION ───────────────────────────────────────────────
resource "aws_vpc" "dr" {
  provider             = aws.dr
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-dr-11-16" }
}

resource "aws_subnet" "dr_pub_a" {
  provider                = aws.dr
  vpc_id                  = aws_vpc.dr.id
  cidr_block              = "10.1.1.0/24"
  availability_zone       = "us-west-2a"
  map_public_ip_on_launch = true
  tags = { Name = "dr-pub-a-11-16" }
}

resource "aws_subnet" "dr_pub_b" {
  provider                = aws.dr
  vpc_id                  = aws_vpc.dr.id
  cidr_block              = "10.1.2.0/24"
  availability_zone       = "us-west-2b"
  map_public_ip_on_launch = true
  tags = { Name = "dr-pub-b-11-16" }
}

resource "aws_internet_gateway" "dr" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr.id
  tags     = { Name = "igw-dr-11-16" }
}

resource "aws_lb" "dr" {
  provider           = aws.dr
  name               = "alb-dr-11-16"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.dr_pub_a.id, aws_subnet.dr_pub_b.id]
  tags               = { Name = "alb-dr-11-16" }
}

# ── ROUTE 53 HEALTH CHECK + FAILOVER ────────────────────────
resource "aws_route53_health_check" "primary" {
  fqdn              = aws_lb.primary.dns_name
  port              = 80
  type              = "HTTP"
  resource_path     = "/health"
  request_interval  = 10
  failure_threshold = 3
  tags = { Name = "hc-primary-11-16" }
}
