terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# Management account provider
provider "aws" {
  alias   = "mgmt"
  region  = var.region
  profile = var.mgmt_profile
}

# Dev account provider
provider "aws" {
  alias   = "dev"
  region  = var.region
  profile = var.dev_profile
}

# Shared VPC in Management account
resource "aws_vpc" "shared" {
  provider             = aws.mgmt
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-shared-11-15" }
}

resource "aws_subnet" "shared_a" {
  provider          = aws.mgmt
  vpc_id            = aws_vpc.shared.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "shared-subnet-a-11-15" }
}

resource "aws_subnet" "shared_b" {
  provider          = aws.mgmt
  vpc_id            = aws_vpc.shared.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}b"
  tags = { Name = "shared-subnet-b-11-15" }
}

# RAM Resource Share
resource "aws_ram_resource_share" "share" {
  provider                  = aws.mgmt
  name                      = "share-subnets-11-15"
  allow_external_principals = false
  tags = { Name = "share-subnets-11-15" }
}

resource "aws_ram_resource_association" "subnet_a" {
  provider           = aws.mgmt
  resource_share_arn = aws_ram_resource_share.share.arn
  resource_arn       = aws_subnet.shared_a.arn
}

resource "aws_ram_resource_association" "subnet_b" {
  provider           = aws.mgmt
  resource_share_arn = aws_ram_resource_share.share.arn
  resource_arn       = aws_subnet.shared_b.arn
}

resource "aws_ram_principal_association" "dev_account" {
  provider           = aws.mgmt
  resource_share_arn = aws_ram_resource_share.share.arn
  principal          = var.dev_account_id
}

# Route 53 Private Hosted Zone
resource "aws_route53_zone" "internal" {
  provider = aws.mgmt
  name     = "internal.company.com"

  vpc {
    vpc_id = aws_vpc.shared.id
  }
  tags = { Name = "internal.company.com" }
}

resource "aws_route53_record" "app" {
  provider = aws.mgmt
  zone_id  = aws_route53_zone.internal.zone_id
  name     = "app.internal.company.com"
  type     = "A"
  ttl      = 300
  records  = ["10.0.1.10"]
}
