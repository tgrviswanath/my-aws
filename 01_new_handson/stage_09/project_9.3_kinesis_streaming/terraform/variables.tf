# variables.tf — Project 9.3 Kinesis Streaming Pipeline
# ─────────────────────────────────────────────────────────────────────────────
# All configurable parameters. Defaults are set for a minimal learning setup.
# Override in terraform.tfvars — never hardcode values in main.tf.
# ─────────────────────────────────────────────────────────────────────────────

variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix — used in all resource names"
  type        = string
  default     = "handson"
}

# ── Kinesis Stream ───────────────────────────────────────────────────────────

variable "shard_count" {
  description = <<-EOT
    Number of shards for the Kinesis stream (PROVISIONED mode).
    1 shard = 1 MB/s inbound, 2 MB/s outbound, 1,000 records/s.
    Cost: $0.015/shard-hour = $10.80/month per shard.
    For learning: 1 shard is sufficient.
    Scale when: throughput > 800 KB/s or > 900 records/s.
  EOT
  type    = number
  default = 1
  validation {
    condition     = var.shard_count >= 1 && var.shard_count <= 10
    error_message = "Shard count must be between 1 and 10 for this project."
  }
}

variable "retention_hours" {
  description = <<-EOT
    How long Kinesis keeps records available for consumption (hours).
    Default 24h is the minimum. Max is 8760h (365 days).
    Longer retention = higher cost ($0.02/GB/hr beyond 24h).
    For learning: 24h (default minimum) is sufficient.
  EOT
  type    = number
  default = 24
  validation {
    condition     = var.retention_hours >= 24 && var.retention_hours <= 8760
    error_message = "Retention must be between 24 and 8760 hours."
  }
}

# ── Lambda Consumer ──────────────────────────────────────────────────────────

variable "lambda_runtime" {
  description = "Lambda Python runtime version"
  type        = string
  default     = "python3.11"
  validation {
    condition     = contains(["python3.9", "python3.10", "python3.11", "python3.12"], var.lambda_runtime)
    error_message = "Runtime must be a supported Python version."
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds (max 900). Kinesis batches of 100 records process in < 5s."
  type        = number
  default     = 60
}

variable "batch_size" {
  description = <<-EOT
    Maximum records per Lambda invocation (1–10000).
    Larger batch = fewer invocations = cheaper Lambda.
    Smaller batch = lower per-invocation latency.
    100 is a good default for most streaming workloads.
  EOT
  type    = number
  default = 100
  validation {
    condition     = var.batch_size >= 1 && var.batch_size <= 10000
    error_message = "Batch size must be between 1 and 10000."
  }
}

variable "max_retry_attempts" {
  description = "Max retry attempts for failed Lambda batches before routing to DLQ (0–10000, -1 = unlimited)"
  type        = number
  default     = 3
}
