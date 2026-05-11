terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "us-east-1" }
variable "project"     { default = "handson" }
variable "environment" { default = "prod" }
variable "db_password" { type = string sensitive = true }
variable "api_key"     { type = string sensitive = true default = "placeholder-api-key" }

locals {
  path_prefix = "/${var.project}/${var.environment}"
  common_tags = { Project = var.project, Stage = "stage-08", ManagedBy = "terraform" }
}

# ─── KMS Key for encryption ───────────────────────────────────────────────────

resource "aws_kms_key" "secrets" {
  description             = "KMS key for ${var.project} secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = merge(local.common_tags, { Name = "${var.project}-secrets-key" })
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# ─── Secrets Manager — DB Credentials ────────────────────────────────────────

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.path_prefix}/db-credentials"
  description = "RDS database credentials"
  kms_key_id  = aws_kms_key.secrets.arn

  recovery_window_in_days = 7   # 7-day recovery window before permanent deletion

  tags = merge(local.common_tags, { Name = "db-credentials" })
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id

  secret_string = jsonencode({
    username = "admin"
    password = var.db_password
    host     = "your-rds-endpoint.us-east-1.rds.amazonaws.com"
    port     = 3306
    dbname   = "appdb"
  })
}

# ─── Secrets Manager — API Key ────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "api_key" {
  name        = "${local.path_prefix}/third-party-api-key"
  description = "Third-party API key"
  kms_key_id  = aws_kms_key.secrets.arn
  tags        = merge(local.common_tags, { Name = "api-key" })
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = jsonencode({ api_key = var.api_key })
}

# ─── SSM Parameter Store — App Config ────────────────────────────────────────

resource "aws_ssm_parameter" "db_host" {
  name  = "${local.path_prefix}/db_host"
  type  = "String"
  value = "your-rds-endpoint.us-east-1.rds.amazonaws.com"
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "redis_host" {
  name  = "${local.path_prefix}/redis_host"
  type  = "String"
  value = "your-elasticache-endpoint.us-east-1.cache.amazonaws.com"
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "feature_flag" {
  name  = "${local.path_prefix}/feature_new_ui"
  type  = "String"
  value = "false"
  tags  = local.common_tags
}

# ─── IAM Policy for ECS/Lambda to read secrets ───────────────────────────────

resource "aws_iam_policy" "read_secrets" {
  name        = "${var.project}-read-secrets-policy"
  description = "Allow reading secrets for ${var.project}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.api_key.arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
        Resource = "arn:aws:ssm:${var.region}:*:parameter${local.path_prefix}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = aws_kms_key.secrets.arn
      }
    ]
  })

  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "db_secret_arn"      { value = aws_secretsmanager_secret.db_credentials.arn }
output "api_key_secret_arn" { value = aws_secretsmanager_secret.api_key.arn }
output "read_policy_arn"    { value = aws_iam_policy.read_secrets.arn }
output "kms_key_arn"        { value = aws_kms_key.secrets.arn }
output "ssm_path_prefix"    { value = local.path_prefix }
