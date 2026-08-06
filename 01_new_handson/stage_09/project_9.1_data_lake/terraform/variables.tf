variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix used in all resource names"
  type        = string
  default     = "handson"
}

variable "raw_lifecycle_glacier_days" {
  description = "Days after which raw/ objects transition to Glacier"
  type        = number
  default     = 90
}

variable "temp_lifecycle_expire_days" {
  description = "Days after which temp/ objects are permanently deleted"
  type        = number
  default     = 7
}

variable "athena_scan_limit_gb" {
  description = "Maximum GB per Athena query (cost protection). Default: 1 GB"
  type        = number
  default     = 1
}

variable "crawler_schedule" {
  description = "Cron expression for Glue crawler. Default: daily at 6am UTC"
  type        = string
  default     = "cron(0 6 * * ? *)"
}
