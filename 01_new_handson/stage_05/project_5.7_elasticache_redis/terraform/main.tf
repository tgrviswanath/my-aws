terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"             { default = "us-east-1" }
variable "project"            { default = "handson" }
variable "vpc_id"             { description = "VPC ID" }
variable "private_subnet_ids" { type = list(string) }
variable "app_sg_id"          { description = "ECS tasks security group ID" }

locals {
  name_prefix = "${var.project}-redis"
  common_tags = { Project = var.project, Stage = "stage-05", ManagedBy = "terraform" }
}

# ─── Security Group ───────────────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name   = "${local.name_prefix}-sg"
  vpc_id = var.vpc_id

  ingress {
    description     = "Redis from ECS tasks only"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.app_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-sg" })
}

# ─── ElastiCache Subnet Group ─────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = local.common_tags
}

# ─── ElastiCache Redis Cluster ────────────────────────────────────────────────

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name_prefix}-cluster"
  description          = "Redis cache for ${var.project}"

  node_type            = "cache.t3.micro"   # free tier eligible
  num_cache_clusters   = 1                  # single node for dev (use 2+ for HA)
  port                 = 6379
  engine               = "redis"
  engine_version       = "7.1"

  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true

  # Eviction policy: remove least recently used keys when memory is full
  parameter_group_name = aws_elasticache_parameter_group.redis.name

  automatic_failover_enabled = false  # requires num_cache_clusters >= 2

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-cluster" })
}

resource "aws_elasticache_parameter_group" "redis" {
  name   = "${local.name_prefix}-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"   # evict LRU keys when memory full
  }

  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "redis_endpoint"      { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "redis_port"          { value = aws_elasticache_replication_group.redis.port }
output "redis_sg_id"         { value = aws_security_group.redis.id }
