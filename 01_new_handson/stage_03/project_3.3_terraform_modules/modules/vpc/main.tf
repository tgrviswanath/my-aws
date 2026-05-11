# modules/vpc/main.tf
# Reusable VPC module — accepts inputs, creates VPC infrastructure, exports outputs.

variable "name_prefix"  { type = string }
variable "vpc_cidr"     { default = "10.0.0.0/16" }
variable "azs"          { type = list(string) }
variable "common_tags"  { type = map(string) default = {} }

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-public-${count.index}", Tier = "public" })
}

resource "aws_subnet" "private_app" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = var.azs[count.index]
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-private-app-${count.index}", Tier = "app" })
}

resource "aws_subnet" "private_db" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 20)
  availability_zone = var.azs[count.index]
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-private-db-${count.index}", Tier = "db" })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = merge(var.common_tags, { Name = "${var.name_prefix}-igw" })
}

resource "aws_eip" "nat" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
  tags          = merge(var.common_tags, { Name = "${var.name_prefix}-nat" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0" gateway_id = aws_internet_gateway.main.id }
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-public-rt" })
}

resource "aws_route_table_association" "public" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0" nat_gateway_id = aws_nat_gateway.main.id }
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-private-rt" })
}

resource "aws_route_table_association" "private_app" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_db" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private.id
}

# ─── Outputs ──────────────────────────────────────────────────────────────────
output "vpc_id"                  { value = aws_vpc.main.id }
output "public_subnet_ids"       { value = aws_subnet.public[*].id }
output "private_app_subnet_ids"  { value = aws_subnet.private_app[*].id }
output "private_db_subnet_ids"   { value = aws_subnet.private_db[*].id }
output "nat_gateway_ip"          { value = aws_eip.nat.public_ip }
