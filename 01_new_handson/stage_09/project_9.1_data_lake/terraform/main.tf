terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  common_tags = { Project = var.project, Stage = "stage-09", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── Data Lake S3 Bucket ──────────────────────────────────────────────────────

resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project}-data-lake-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "data-lake" })
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "archive-raw-data"
    status = "Enabled"
    filter { prefix = "raw/" }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "expire-temp-data"
    status = "Enabled"
    filter { prefix = "temp/" }
    expiration { days = 7 }
  }
}

# ─── Glue Database ────────────────────────────────────────────────────────────

resource "aws_glue_catalog_database" "data_lake" {
  name        = "${var.project}_data_lake"
  description = "Data lake catalog for ${var.project}"
}

# ─── Glue IAM Role ────────────────────────────────────────────────────────────

resource "aws_iam_role" "glue" {
  name = "${var.project}-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  name = "s3-access"
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.data_lake.arn, "${aws_s3_bucket.data_lake.arn}/*"]
    }]
  })
}

# ─── Glue Crawler ─────────────────────────────────────────────────────────────

resource "aws_glue_crawler" "raw_data" {
  name          = "${var.project}-raw-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.data_lake.name

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.bucket}/processed/"
  }

  schedule = "cron(0 6 * * ? *)"   # daily at 6am UTC

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = local.common_tags
}

# ─── Athena Workgroup ─────────────────────────────────────────────────────────

resource "aws_s3_bucket" "athena_results" {
  bucket = "${var.project}-athena-results-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_athena_workgroup" "data_lake" {
  name = "${var.project}-data-lake"
  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }
    bytes_scanned_cutoff_per_query = 1073741824   # 1 GB limit
  }
  tags = local.common_tags
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "data_lake_bucket"   { value = aws_s3_bucket.data_lake.bucket }
output "glue_database"      { value = aws_glue_catalog_database.data_lake.name }
output "glue_role_arn"      { value = aws_iam_role.glue.arn }
output "athena_workgroup"   { value = aws_athena_workgroup.data_lake.name }
