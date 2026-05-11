terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"              { default = "us-east-1" }
variable "project"             { default = "handson" }
variable "cloudtrail_s3_bucket" { description = "S3 bucket containing CloudTrail logs" }
variable "alb_logs_s3_bucket"   { description = "S3 bucket containing ALB access logs" }

locals {
  common_tags = { Project = var.project, Stage = "stage-07", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Athena Query Results Bucket ──────────────────────────────────────────────

resource "aws_s3_bucket" "athena_results" {
  bucket = "${var.project}-athena-results-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    expiration { days = 7 }
  }
}

# ─── Athena Workgroup (with cost controls) ────────────────────────────────────

resource "aws_athena_workgroup" "main" {
  name = "${var.project}-workgroup"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }

    # Limit each query to 1 GB scan — prevents runaway costs
    bytes_scanned_cutoff_per_query = 1073741824   # 1 GB

    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
  }

  tags = local.common_tags
}

# ─── Glue Database ────────────────────────────────────────────────────────────

resource "aws_glue_catalog_database" "logs" {
  name = "${var.project}_logs"
}

# ─── CloudTrail Table ─────────────────────────────────────────────────────────

resource "aws_glue_catalog_table" "cloudtrail" {
  name          = "cloudtrail_logs"
  database_name = aws_glue_catalog_database.logs.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "EXTERNAL"                 = "TRUE"
    "projection.enabled"       = "true"
    "projection.year.type"     = "integer"
    "projection.year.range"    = "2023,2030"
    "projection.month.type"    = "integer"
    "projection.month.range"   = "1,12"
    "projection.month.digits"  = "2"
    "projection.day.type"      = "integer"
    "projection.day.range"     = "1,31"
    "projection.day.digits"    = "2"
    "storage.location.template" = "s3://${var.cloudtrail_s3_bucket}/AWSLogs/${data.aws_caller_identity.current.account_id}/CloudTrail/${var.region}/$${year}/$${month}/$${day}"
  }

  partition_keys = [
    { name = "year"  type = "string" },
    { name = "month" type = "string" },
    { name = "day"   type = "string" },
  ]

  storage_descriptor {
    location      = "s3://${var.cloudtrail_s3_bucket}/AWSLogs/${data.aws_caller_identity.current.account_id}/CloudTrail/${var.region}/"
    input_format  = "com.amazon.emr.cloudtrail.CloudTrailInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "com.amazon.emr.hive.serde.CloudTrailSerde"
    }

    columns {
      name = "eventversion"    type = "string"
    }
    columns {
      name = "useridentity"    type = "struct<type:string,principalid:string,arn:string,accountid:string,invokedby:string,accesskeyid:string,username:string,sessioncontext:struct<attributes:struct<mfaauthenticated:string,creationdate:string>,sessionissuer:struct<type:string,principalid:string,arn:string,accountid:string,username:string>>>"
    }
    columns { name = "eventtime"          type = "string" }
    columns { name = "eventsource"        type = "string" }
    columns { name = "eventname"          type = "string" }
    columns { name = "awsregion"          type = "string" }
    columns { name = "sourceipaddress"    type = "string" }
    columns { name = "useragent"          type = "string" }
    columns { name = "errorcode"          type = "string" }
    columns { name = "errormessage"       type = "string" }
    columns { name = "requestparameters" type = "string" }
    columns { name = "responseelements"  type = "string" }
    columns { name = "requestid"         type = "string" }
    columns { name = "eventid"           type = "string" }
    columns { name = "readonly"          type = "string" }
    columns { name = "resources"         type = "array<struct<arn:string,accountid:string,type:string>>" }
    columns { name = "eventtype"         type = "string" }
    columns { name = "apiversion"        type = "string" }
    columns { name = "recipientaccountid" type = "string" }
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "athena_query_url" {
  value = "https://${var.region}.console.aws.amazon.com/athena/home?region=${var.region}#/query-editor"
}
output "results_bucket"   { value = aws_s3_bucket.athena_results.bucket }
output "workgroup_name"   { value = aws_athena_workgroup.main.name }
output "database_name"    { value = aws_glue_catalog_database.logs.name }
