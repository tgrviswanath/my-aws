terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

# Primary region
provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

# DR region
provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

variable "project"      { default = "handson" }
variable "db_password"  { type = string sensitive = true }
variable "primary_vpc_id"    { description = "Primary VPC ID" }
variable "primary_subnet_ids" { type = list(string) }
variable "dr_vpc_id"          { description = "DR VPC ID" }
variable "dr_subnet_ids"      { type = list(string) }

locals {
  common_tags = { Project = var.project, Stage = "stage-10", ManagedBy = "terraform" }
}

# ─── S3 Cross-Region Replication ──────────────────────────────────────────────

resource "aws_s3_bucket" "primary" {
  provider = aws.primary
  bucket   = "${var.project}-primary-data"
  tags     = local.common_tags
}

resource "aws_s3_bucket_versioning" "primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket" "dr" {
  provider = aws.dr
  bucket   = "${var.project}-dr-data"
  tags     = local.common_tags
}

resource "aws_s3_bucket_versioning" "dr" {
  provider = aws.dr
  bucket   = aws_s3_bucket.dr.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_iam_role" "replication" {
  provider = aws.primary
  name     = "${var.project}-s3-replication-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "s3.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "replication" {
  provider = aws.primary
  name     = "replication-policy"
  role     = aws_iam_role.replication.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetReplicationConfiguration", "s3:ListBucket"]
        Resource = aws_s3_bucket.primary.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObjectVersionForReplication", "s3:GetObjectVersionAcl", "s3:GetObjectVersionTagging"]
        Resource = "${aws_s3_bucket.primary.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ReplicateObject", "s3:ReplicateDelete", "s3:ReplicateTags"]
        Resource = "${aws_s3_bucket.dr.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_replication_configuration" "primary_to_dr" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id
  role     = aws_iam_role.replication.arn

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.dr.arn
      storage_class = "STANDARD_IA"
    }
  }

  depends_on = [aws_s3_bucket_versioning.primary]
}

# ─── RDS Read Replica in DR Region ───────────────────────────────────────────

resource "aws_db_subnet_group" "primary" {
  provider   = aws.primary
  name       = "${var.project}-primary-db-subnet"
  subnet_ids = var.primary_subnet_ids
  tags       = local.common_tags
}

resource "aws_db_instance" "primary" {
  provider               = aws.primary
  identifier             = "${var.project}-primary-db"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "appdb"
  username               = "admin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.primary.name
  publicly_accessible    = false
  backup_retention_period = 7
  skip_final_snapshot    = true
  tags                   = merge(local.common_tags, { Name = "${var.project}-primary-db" })
}

resource "aws_db_instance" "dr_replica" {
  provider            = aws.dr
  identifier          = "${var.project}-dr-replica"
  replicate_source_db = aws_db_instance.primary.arn
  instance_class      = "db.t3.micro"
  publicly_accessible = false
  skip_final_snapshot = true
  tags                = merge(local.common_tags, { Name = "${var.project}-dr-replica" })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "primary_db_endpoint"  { value = aws_db_instance.primary.endpoint }
output "dr_replica_endpoint"  { value = aws_db_instance.dr_replica.endpoint }
output "primary_s3_bucket"    { value = aws_s3_bucket.primary.bucket }
output "dr_s3_bucket"         { value = aws_s3_bucket.dr.bucket }
