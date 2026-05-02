terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "scalable-webapp/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "scalable-webapp"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

variable "environment"    { type = string; default = "prod" }
variable "aws_region"     { type = string; default = "us-east-1" }
variable "app_name"       { type = string; default = "myapp" }
variable "instance_type"  { type = string; default = "t3.medium" }
variable "db_password"    { type = string; sensitive = true }
variable "acm_cert_arn"   { type = string; default = "" }

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name"; values = ["al2023-ami-*-x86_64"] }
}

# ── VPC (using reusable module) ───────────────────────────────────────────────
module "vpc" {
  source      = "../../utils/terraform/modules/vpc"
  vpc_cidr    = "10.0.0.0/16"
  environment = var.environment
  app_name    = var.app_name
}

# ── KMS Key ───────────────────────────────────────────────────────────────────
resource "aws_kms_key" "main" {
  description             = "${var.environment} encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.app_name}-${var.environment}"
  target_key_id = aws_kms_key.main.key_id
}

# ── Security Groups ───────────────────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-alb-"
  vpc_id      = module.vpc.vpc_id
  ingress { from_port = 80;  to_port = 80;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;   to_port = 0;   protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.environment}-app-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "db" {
  name_prefix = "${var.environment}-db-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "cache" {
  name_prefix = "${var.environment}-cache-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  lifecycle { create_before_destroy = true }
}

# ── S3 Bucket ─────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "assets" {
  bucket = "${data.aws_caller_identity.current.account_id}-${var.environment}-assets"
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# ── ALB ───────────────────────────────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnet_ids
  enable_deletion_protection = var.environment == "prod"
}

resource "aws_lb_target_group" "app" {
  name     = "${var.environment}-app-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
  deregistration_delay = 60
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_cert_arn
  default_action { type = "forward"; target_group_arn = aws_lb_target_group.app.arn }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect { port = "443"; protocol = "HTTPS"; status_code = "HTTP_301" }
  }
}

# ── IAM Role for EC2 ──────────────────────────────────────────────────────────
resource "aws_iam_role" "app" {
  name = "${var.environment}-webapp-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow"; Principal = { Service = "ec2.amazonaws.com" }; Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.environment}-webapp-profile"
  role = aws_iam_role.app.name
}

# ── ASG (using reusable module) ───────────────────────────────────────────────
module "asg" {
  source               = "../../utils/terraform/modules/ec2"
  app_name             = var.app_name
  environment          = var.environment
  instance_type        = var.instance_type
  ami_id               = data.aws_ami.amazon_linux.id
  subnet_ids           = module.vpc.private_subnet_ids
  security_group_ids   = [aws_security_group.app.id]
  target_group_arns    = [aws_lb_target_group.app.arn]
  iam_instance_profile = aws_iam_instance_profile.app.name
  min_size             = 2
  max_size             = 20
  desired_capacity     = 4
  kms_key_arn          = aws_kms_key.main.arn
}

# ── Aurora PostgreSQL (using reusable module) ─────────────────────────────────
module "aurora" {
  source             = "../../utils/terraform/modules/rds"
  app_name           = var.app_name
  environment        = var.environment
  engine             = "aurora-postgresql"
  engine_version     = "15.4"
  instance_class     = "db.r6g.large"
  instance_count     = 2
  db_subnet_group    = module.vpc.db_subnet_group_name
  security_group_ids = [aws_security_group.db.id]
  kms_key_arn        = aws_kms_key.main.arn
  deletion_protection = var.environment == "prod"
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.environment}-cache-subnet"
  subnet_ids = module.vpc.private_subnet_ids
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.environment}-redis"
  description                = "${var.environment} Redis"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.r6g.large"
  num_cache_clusters         = 3
  automatic_failover_enabled = true
  multi_az_enabled           = true
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.cache.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.main.arn
  snapshot_retention_limit   = 7
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "alb_dns"              { value = aws_lb.main.dns_name }
output "db_endpoint"          { value = module.aurora.cluster_endpoint }
output "db_reader_endpoint"   { value = module.aurora.cluster_reader_endpoint }
output "redis_endpoint"       { value = aws_elasticache_replication_group.main.primary_endpoint_address }
output "assets_bucket"        { value = aws_s3_bucket.assets.bucket }
