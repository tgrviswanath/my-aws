# Project 9.8 — Schema Evolution & Partitioning
# Creates Glue Schema Registry and configures partition projection on Athena tables.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"          { default = "us-east-1" }
variable "project"         { default = "handson" }
variable "data_lake_bucket" { description = "Data lake S3 bucket" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Glue Schema Registry ─────────────────────────────────────────────────────

resource "aws_glue_registry" "main" {
  registry_name = "${var.project}-registry"
  description   = "Schema registry for ${var.project} data streams"
  tags          = local.common_tags
}

resource "aws_glue_schema" "orders" {
  schema_name       = "orders-schema"
  registry_arn      = aws_glue_registry.main.arn
  data_format       = "AVRO"
  compatibility     = "BACKWARD"
  description       = "Orders event schema — BACKWARD compatible (add nullable fields only)"

  schema_definition = jsonencode({
    type      = "record"
    name      = "Order"
    namespace = "${var.project}.orders"
    fields = [
      { name = "order_id",    type = "string" },
      { name = "customer_id", type = "string" },
      { name = "amount",      type = "double" },
      { name = "order_date",  type = "string" },
    ]
  })

  tags = local.common_tags
}

# ─── Glue Table with Partition Projection ────────────────────────────────────

resource "aws_glue_catalog_database" "schema_demo" {
  name = "${var.project}_schema_demo"
}

resource "aws_glue_catalog_table" "orders_partitioned" {
  name          = "orders_partitioned"
  database_name = aws_glue_catalog_database.schema_demo.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "EXTERNAL"                  = "TRUE"
    # Partition projection — Athena auto-discovers partitions without MSCK REPAIR TABLE
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2023,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "storage.location.template" = "s3://${var.data_lake_bucket}/processed/orders/year=$${year}/month=$${month}/day=$${day}"
  }

  partition_keys = [
    { name = "year"  type = "int" },
    { name = "month" type = "int" },
    { name = "day"   type = "int" },
  ]

  storage_descriptor {
    location      = "s3://${var.data_lake_bucket}/processed/orders/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters            = { "serialization.format" = "1" }
    }

    columns { name = "order_id"    type = "string" }
    columns { name = "customer_id" type = "string" }
    columns { name = "amount"      type = "double" }
    columns { name = "order_date"  type = "date" }
    columns { name = "product"     type = "string" }
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "registry_arn"    { value = aws_glue_registry.main.arn }
output "schema_arn"      { value = aws_glue_schema.orders.arn }
output "database_name"   { value = aws_glue_catalog_database.schema_demo.name }
output "table_name"      { value = aws_glue_catalog_table.orders_partitioned.name }
