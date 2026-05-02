# Reusable Terraform module for Aurora PostgreSQL / MySQL cluster
# Usage:
# module "aurora" {
#   source             = "./modules/rds"
#   app_name           = "myapp"
#   environment        = "prod"
#   engine             = "aurora-postgresql"
#   engine_version     = "15.4"
#   instance_class     = "db.r6g.large"
#   instance_count     = 2
#   db_subnet_group    = module.vpc.db_subnet_group_name
#   security_group_ids = [aws_security_group.db.id]
#   kms_key_arn        = aws_kms_key.main.arn
# }

variable "app_name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "engine" {
  description = "Aurora engine type"
  type        = string
  default     = "aurora-postgresql"
  validation {
    condition     = contains(["aurora-postgresql", "aurora-mysql"], var.engine)
    error_message = "Engine must be aurora-postgresql or aurora-mysql."
  }
}

variable "engine_version" {
  description = "Aurora engine version"
  type        = string
  default     = "15.4"
}

variable "instance_class" {
  description = "DB instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "instance_count" {
  description = "Number of DB instances (1 writer + N-1 readers)"
  type        = number
  default     = 1
}

variable "db_subnet_group" {
  description = "DB subnet group name"
  type        = string
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "database_name" {
  description = "Initial database name"
  type        = string
  default     = "appdb"
}

variable "master_username" {
  description = "Master username"
  type        = string
  default     = "dbadmin"
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = null
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "serverless_min_capacity" {
  description = "Aurora Serverless v2 minimum ACUs (0 = scale to zero)"
  type        = number
  default     = null
}

variable "serverless_max_capacity" {
  description = "Aurora Serverless v2 maximum ACUs"
  type        = number
  default     = null
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

locals {
  is_serverless = var.serverless_min_capacity != null
  port          = var.engine == "aurora-postgresql" ? 5432 : 3306
  family        = var.engine == "aurora-postgresql" ? "aurora-postgresql15" : "aurora-mysql8.0"

  common_tags = merge({
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }, var.tags)
}

# ── Secrets Manager — Master Password ────────────────────────────────────────
resource "aws_secretsmanager_secret" "db_password" {
  name       = "${var.app_name}/${var.environment}/db/master-password"
  kms_key_id = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_rotation" "db_password" {
  secret_id           = aws_secretsmanager_secret.db_password.id
  rotation_lambda_arn = null  # Set to rotation Lambda ARN if available
  rotation_rules {
    automatically_after_days = 30
  }

  lifecycle {
    ignore_changes = [rotation_lambda_arn]
  }
}

# ── Parameter Group ───────────────────────────────────────────────────────────
resource "aws_rds_cluster_parameter_group" "main" {
  name   = "${var.app_name}-${var.environment}-cluster-params"
  family = local.family

  dynamic "parameter" {
    for_each = var.engine == "aurora-postgresql" ? [
      { name = "log_min_duration_statement", value = "2000" },
      { name = "log_connections", value = "1" },
      { name = "shared_preload_libraries", value = "pg_stat_statements" }
    ] : [
      { name = "slow_query_log", value = "1" },
      { name = "long_query_time", value = "2" },
      { name = "general_log", value = "0" }
    ]
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }

  tags = local.common_tags
}

# ── Aurora Cluster ────────────────────────────────────────────────────────────
resource "aws_rds_cluster" "main" {
  cluster_identifier     = "${var.app_name}-${var.environment}"
  engine                 = var.engine
  engine_version         = var.engine_version
  database_name          = var.database_name
  master_username        = var.master_username
  manage_master_user_password = true  # Secrets Manager managed
  kms_key_id             = var.kms_key_arn
  storage_encrypted      = true

  db_subnet_group_name   = var.db_subnet_group
  vpc_security_group_ids = var.security_group_ids
  port                   = local.port

  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.main.name

  backup_retention_period   = var.backup_retention_days
  preferred_backup_window   = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.app_name}-${var.environment}-final-snapshot" : null

  enabled_cloudwatch_logs_exports = var.engine == "aurora-postgresql" ? ["postgresql"] : ["error", "slowquery"]

  dynamic "serverlessv2_scaling_configuration" {
    for_each = local.is_serverless ? [1] : []
    content {
      min_capacity = var.serverless_min_capacity
      max_capacity = var.serverless_max_capacity
    }
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [master_password]
  }
}

# ── Aurora Instances ──────────────────────────────────────────────────────────
resource "aws_rds_cluster_instance" "main" {
  count = var.instance_count

  identifier         = "${var.app_name}-${var.environment}-${count.index + 1}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = local.is_serverless ? "db.serverless" : var.instance_class
  engine             = var.engine
  engine_version     = var.engine_version

  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null
  performance_insights_kms_key_id       = var.enable_performance_insights ? var.kms_key_arn : null

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  auto_minor_version_upgrade = true

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-${var.environment}-${count.index == 0 ? "writer" : "reader-${count.index}"}"
  })
}

# ── Enhanced Monitoring Role ──────────────────────────────────────────────────
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.app_name}-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.app_name}-${var.environment}-rds-cpu-high"
  alarm_description   = "Aurora CPU utilization above 80%"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.main.cluster_identifier
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "connections_high" {
  alarm_name          = "${var.app_name}-${var.environment}-rds-connections-high"
  alarm_description   = "Aurora database connections above threshold"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 800
  comparison_operator = "GreaterThanThreshold"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.main.cluster_identifier
  }

  tags = local.common_tags
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "cluster_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.main.endpoint
}

output "cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "cluster_identifier" {
  description = "Aurora cluster identifier"
  value       = aws_rds_cluster.main.cluster_identifier
}

output "cluster_arn" {
  description = "Aurora cluster ARN"
  value       = aws_rds_cluster.main.arn
}

output "port" {
  description = "Database port"
  value       = local.port
}

output "database_name" {
  description = "Database name"
  value       = var.database_name
}

output "master_user_secret_arn" {
  description = "Secrets Manager ARN for master credentials"
  value       = aws_rds_cluster.main.master_user_secret[0].secret_arn
}
