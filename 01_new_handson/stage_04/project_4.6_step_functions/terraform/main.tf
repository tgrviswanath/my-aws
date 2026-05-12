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
  name_prefix = "${var.project}-doc-proc"
  common_tags = { Project = var.project, Stage = "stage-04", ManagedBy = "terraform" }
  steps = ["validate", "extract_text", "classify", "check_compliance", "store_results", "notify"]
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

# ─── Lambda Functions (one per step) ─────────────────────────────────────────

data "archive_file" "steps" {
  type        = "zip"
  source_file = "${path.module}/../src/steps.py"
  output_path = "${path.module}/steps.zip"
}

locals {
  handler_map = {
    validate         = "steps.validate"
    extract_text     = "steps.extract_text"
    classify         = "steps.classify"
    check_compliance = "steps.check_compliance"
    store_results    = "steps.store_results"
    notify           = "steps.notify"
  }
}

resource "aws_lambda_function" "step" {
  for_each         = local.handler_map
  filename         = data.archive_file.steps.output_path
  function_name    = "${local.name_prefix}-${each.key}"
  role             = aws_iam_role.lambda.arn
  handler          = each.value
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.steps.output_base64sha256
  tags             = merge(local.common_tags, { Step = each.key })
}

# ─── Step Functions IAM Role ──────────────────────────────────────────────────

resource "aws_iam_role" "sfn" {
  name = "${local.name_prefix}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow" Principal = { Service = "states.amazonaws.com" } Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "sfn_lambda" {
  name = "invoke-lambdas"
  role = aws_iam_role.sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = [for fn in aws_lambda_function.step : fn.arn]
    }]
  })
}

# ─── State Machine ────────────────────────────────────────────────────────────

resource "aws_sfn_state_machine" "doc_processor" {
  name     = "${local.name_prefix}-state-machine"
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    Comment = "Document processing workflow"
    StartAt = "Validate"
    States = {
      Validate = {
        Type     = "Task"
        Resource = aws_lambda_function.step["validate"].arn
        Retry    = [{ ErrorEquals = ["Lambda.ServiceException"], IntervalSeconds = 2, MaxAttempts = 3, BackoffRate = 2 }]
        Catch    = [{ ErrorEquals = ["ValueError"], Next = "ValidationFailed", ResultPath = "$.error" }]
        Next     = "ExtractText"
      }
      ExtractText = {
        Type     = "Task"
        Resource = aws_lambda_function.step["extract_text"].arn
        Next     = "ParallelAnalysis"
      }
      ParallelAnalysis = {
        Type = "Parallel"
        Branches = [
          {
            StartAt = "Classify"
            States = { Classify = { Type = "Task" Resource = aws_lambda_function.step["classify"].arn End = true } }
          },
          {
            StartAt = "CheckCompliance"
            States = { CheckCompliance = { Type = "Task" Resource = aws_lambda_function.step["check_compliance"].arn End = true } }
          }
        ]
        ResultSelector = { "classification.$" = "$[0].classification", "compliance.$" = "$[1].compliance" }
        ResultPath     = "$.analysis"
        Next           = "StoreResults"
      }
      StoreResults = {
        Type     = "Task"
        Resource = aws_lambda_function.step["store_results"].arn
        Next     = "Notify"
      }
      Notify = {
        Type     = "Task"
        Resource = aws_lambda_function.step["notify"].arn
        Next     = "Success"
      }
      Success          = { Type = "Succeed" }
      ValidationFailed = { Type = "Fail" Error = "ValidationError" Cause = "Document failed validation" }
    }
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-state-machine" })
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "state_machine_arn"  { value = aws_sfn_state_machine.doc_processor.arn }
output "state_machine_name" { value = aws_sfn_state_machine.doc_processor.name }
