terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    archive = { source = "hashicorp/archive" version = "~> 2.0" }
  }
}

provider "aws" { region = var.region }

variable "region"  { default = "us-east-1" }
variable "project" { default = "handson" }

locals {
  name_prefix = "${var.project}-img-proc"
  common_tags = { Project = var.project, Stage = "stage-04", ManagedBy = "terraform" }
}

data "aws_caller_identity" "current" {}

# ─── S3 Buckets ───────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "source" {
  bucket = "${local.name_prefix}-source-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "image-source" })
}

resource "aws_s3_bucket" "output" {
  bucket = "${local.name_prefix}-output-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "image-output" })
}

# ─── DynamoDB for metadata ────────────────────────────────────────────────────

resource "aws_dynamodb_table" "metadata" {
  name         = "${local.name_prefix}-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "image_key"
  attribute { name = "image_key" type = "S" }
  tags = local.common_tags
}

# ─── Lambda IAM Role ──────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "lambda.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "s3_dynamo" {
  name = "s3-dynamo-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.source.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.output.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.metadata.arn
      }
    ]
  })
}

# ─── Lambda Function ──────────────────────────────────────────────────────────

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/handler.py"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "processor" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "${local.name_prefix}-processor"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.output.bucket
      TABLE_NAME    = aws_dynamodb_table.metadata.name
    }
  }

  layers = []  # Add Pillow layer ARN here after creating it
  tags   = local.common_tags
}

# ─── S3 Event Notification → Lambda ──────────────────────────────────────────

resource "aws_lambda_permission" "s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.source.arn
}

resource "aws_s3_bucket_notification" "source" {
  bucket = aws_s3_bucket.source.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".jpg"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".png"
  }

  depends_on = [aws_lambda_permission.s3]
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "source_bucket" { value = aws_s3_bucket.source.bucket }
output "output_bucket" { value = aws_s3_bucket.output.bucket }
output "lambda_name"   { value = aws_lambda_function.processor.function_name }
output "table_name"    { value = aws_dynamodb_table.metadata.name }
