terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.region }

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "vpc-11-17" }
}

resource "aws_subnet" "pub_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags = { Name = "pub-a-11-17" }
}
resource "aws_subnet" "pub_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.region}b"
  map_public_ip_on_launch = true
  tags = { Name = "pub-b-11-17" }
}
resource "aws_subnet" "priv_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "${var.region}a"
  tags = { Name = "priv-a-11-17" }
}
resource "aws_subnet" "priv_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = "${var.region}b"
  tags = { Name = "priv-b-11-17" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-11-17" }
}

resource "aws_eip" "nat" { domain = "vpc" }
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.pub_a.id
  tags          = { Name = "nat-11-17" }
  depends_on    = [aws_internet_gateway.igw]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.igw.id }
  tags = { Name = "public-rt-11-17" }
}
resource "aws_route_table_association" "pub_a" {
  subnet_id      = aws_subnet.pub_a.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "pub_b" {
  subnet_id      = aws_subnet.pub_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0"; nat_gateway_id = aws_nat_gateway.nat.id }
  tags = { Name = "private-rt-11-17" }
}
resource "aws_route_table_association" "priv_a" {
  subnet_id      = aws_subnet.priv_a.id
  route_table_id = aws_route_table.private.id
}
resource "aws_route_table_association" "priv_b" {
  subnet_id      = aws_subnet.priv_b.id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name   = "sg-alb-11-17"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "sg-alb-11-17" }
}
resource "aws_security_group" "web" {
  name   = "sg-web-11-17"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0;  to_port = 0;  protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "sg-web-11-17" }
}
resource "aws_security_group" "api" {
  name   = "sg-api-11-17"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 8080; to_port = 8080; protocol = "tcp"; security_groups = [aws_security_group.web.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  tags = { Name = "sg-api-11-17" }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "cluster-11-17"
  tags = { Name = "cluster-11-17" }
}

# Cloud Map namespace
resource "aws_service_discovery_private_dns_namespace" "local" {
  name = "local"
  vpc  = aws_vpc.main.id
  tags = { Name = "ns-local-11-17" }
}

# Task execution role
resource "aws_iam_role" "ecs_exec" {
  name = "ecs-exec-role-11-17"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "ecs-tasks.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "ecs_exec" {
  role       = aws_iam_role.ecs_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Web task definition
resource "aws_ecs_task_definition" "web" {
  family                   = "td-web-11-17"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  container_definitions = jsonencode([{
    name         = "web"
    image        = "nginx:latest"
    portMappings = [{ containerPort = 80; protocol = "tcp" }]
    essential    = true
  }])
}

# API task definition
resource "aws_ecs_task_definition" "api" {
  family                   = "td-api-11-17"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  container_definitions = jsonencode([{
    name         = "api"
    image        = "nginx:latest"
    portMappings = [{ containerPort = 8080; protocol = "tcp" }]
    essential    = true
  }])
}

# ALB
resource "aws_lb" "alb" {
  name               = "alb-11-17"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.pub_a.id, aws_subnet.pub_b.id]
  tags               = { Name = "alb-11-17" }
}
resource "aws_lb_target_group" "web" {
  name        = "tg-web-11-17"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check { path = "/"; matcher = "200" }
  tags = { Name = "tg-web-11-17" }
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action { type = "forward"; target_group_arn = aws_lb_target_group.web.arn }
}

# Cloud Map services
resource "aws_service_discovery_service" "web" {
  name = "web"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.local.id
    dns_records  { type = "A"; ttl = 10 }
  }
  health_check_custom_config { failure_threshold = 1 }
}
resource "aws_service_discovery_service" "api" {
  name = "api"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.local.id
    dns_records  { type = "A"; ttl = 10 }
  }
  health_check_custom_config { failure_threshold = 1 }
}

# ECS Services
resource "aws_ecs_service" "web" {
  name            = "svc-web-11-17"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = [aws_subnet.priv_a.id, aws_subnet.priv_b.id]
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 80
  }
  service_registries {
    registry_arn = aws_service_discovery_service.web.arn
  }
  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "api" {
  name            = "svc-api-11-17"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = [aws_subnet.priv_a.id, aws_subnet.priv_b.id]
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.api.arn
  }
}
