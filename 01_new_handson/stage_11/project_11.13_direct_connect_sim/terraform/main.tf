terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

resource "aws_vpc" "aws_side" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "vpc-aws-11-13" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.aws_side.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "private-aws-11-13" }
}

# VGW with custom ASN (simulates Direct Connect Gateway ASN)
resource "aws_vpn_gateway" "vgw" {
  vpc_id          = aws_vpc.aws_side.id
  amazon_side_asn = 64512
  tags = { Name = "vgw-11-13" }
}

resource "aws_vpn_gateway_route_propagation" "propagate" {
  vpn_gateway_id = aws_vpn_gateway.vgw.id
  route_table_id = aws_vpc.aws_side.default_route_table_id
}

# Customer Gateway with BGP ASN
resource "aws_customer_gateway" "cgw" {
  bgp_asn    = 65000
  ip_address = var.bgp_router_public_ip
  type       = "ipsec.1"
  tags = { Name = "cgw-bgp-11-13" }
}

# VPN Connection — Dynamic (BGP)
resource "aws_vpn_connection" "vpn" {
  vpn_gateway_id      = aws_vpn_gateway.vgw.id
  customer_gateway_id = aws_customer_gateway.cgw.id
  type                = "ipsec.1"
  static_routes_only  = false   # false = BGP/dynamic routing
  tags = { Name = "vpn-bgp-11-13" }
}
