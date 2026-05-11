terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket the EC2 role can read"
  type        = string
}

# ─── IAM Groups ───────────────────────────────────────────────────────────────

resource "aws_iam_group" "developers" {
  name = "developers"
}

resource "aws_iam_group" "data_engineers" {
  name = "data-engineers"
}

resource "aws_iam_group_policy_attachment" "dev_ec2_read" {
  group      = aws_iam_group.developers.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
}

resource "aws_iam_group_policy_attachment" "dev_s3_read" {
  group      = aws_iam_group.developers.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_group_policy_attachment" "de_s3_full" {
  group      = aws_iam_group.data_engineers.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# ─── EC2 Role with Restricted S3 Access ──────────────────────────────────────

resource "aws_iam_role" "ec2_s3_read" {
  name = "ec2-s3-read-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Project = "handson", Stage = "stage-01" }
}

resource "aws_iam_policy" "s3_read_specific" {
  name        = "S3ReadSpecificBucket"
  description = "Read access to a specific S3 bucket only"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        var.s3_bucket_arn,
        "${var.s3_bucket_arn}/*"
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_s3_read" {
  role       = aws_iam_role.ec2_s3_read.name
  policy_arn = aws_iam_policy.s3_read_specific.arn
}

resource "aws_iam_instance_profile" "ec2_s3_read" {
  name = "ec2-s3-read-profile"
  role = aws_iam_role.ec2_s3_read.name
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "ec2_role_arn"             { value = aws_iam_role.ec2_s3_read.arn }
output "ec2_instance_profile_name" { value = aws_iam_instance_profile.ec2_s3_read.name }
