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
  name_prefix = "${var.project}-auth"
  common_tags = { Project = var.project, Stage = "stage-04", ManagedBy = "terraform" }
}

# ─── Cognito User Pool ────────────────────────────────────────────────────────

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  auto_verified_attributes = ["email"]

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "${local.name_prefix}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 1    # hours
  id_token_validity      = 1    # hours
  refresh_token_validity = 30   # days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# Cognito Groups for RBAC
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Admin users with full access"
}

resource "aws_cognito_user_group" "users" {
  name         = "users"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Regular users with read access"
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

resource "aws_iam_role_policy" "cognito" {
  name = "cognito-access"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cognito-idp:SignUp", "cognito-idp:AdminConfirmSignUp",
                  "cognito-idp:InitiateAuth", "cognito-idp:AdminGetUser"]
      Resource = aws_cognito_user_pool.main.arn
    }]
  })
}

# ─── Lambda Functions ─────────────────────────────────────────────────────────

data "archive_file" "auth" {
  type        = "zip"
  source_file = "${path.module}/../src/auth_handler.py"
  output_path = "${path.module}/auth_lambda.zip"
}

data "archive_file" "protected" {
  type        = "zip"
  source_file = "${path.module}/../src/protected_handler.py"
  output_path = "${path.module}/protected_lambda.zip"
}

resource "aws_lambda_function" "auth" {
  filename         = data.archive_file.auth.output_path
  function_name    = "${local.name_prefix}-auth"
  role             = aws_iam_role.lambda.arn
  handler          = "auth_handler.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.auth.output_base64sha256

  environment {
    variables = {
      COGNITO_CLIENT_ID = aws_cognito_user_pool_client.app.id
      USER_POOL_ID      = aws_cognito_user_pool.main.id
    }
  }

  tags = local.common_tags
}

resource "aws_lambda_function" "protected" {
  filename         = data.archive_file.protected.output_path
  function_name    = "${local.name_prefix}-protected"
  role             = aws_iam_role.lambda.arn
  handler          = "protected_handler.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.protected.output_base64sha256
  tags             = local.common_tags
}

# ─── API Gateway ──────────────────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-gateway"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
  tags = local.common_tags
}

# JWT Authorizer — validates Cognito tokens automatically
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.app.id]
    issuer   = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

resource "aws_apigatewayv2_integration" "auth" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "protected" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.protected.invoke_arn
  payload_format_version = "2.0"
}

# Public routes (no auth)
resource "aws_apigatewayv2_route" "register" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/register"
  target    = "integrations/${aws_apigatewayv2_integration.auth.id}"
}

resource "aws_apigatewayv2_route" "login" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/login"
  target    = "integrations/${aws_apigatewayv2_integration.auth.id}"
}

# Protected routes (JWT required)
resource "aws_apigatewayv2_route" "protected" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /protected"
  target             = "integrations/${aws_apigatewayv2_integration.protected.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
  tags        = local.common_tags
}

resource "aws_lambda_permission" "auth_gw" {
  statement_id  = "AllowAPIGatewayAuth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "protected_gw" {
  statement_id  = "AllowAPIGatewayProtected"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.protected.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "api_url"          { value = aws_apigatewayv2_stage.default.invoke_url }
output "user_pool_id"     { value = aws_cognito_user_pool.main.id }
output "client_id"        { value = aws_cognito_user_pool_client.app.id }
output "register_url"     { value = "${aws_apigatewayv2_stage.default.invoke_url}/auth/register" }
output "login_url"        { value = "${aws_apigatewayv2_stage.default.invoke_url}/auth/login" }
output "protected_url"    { value = "${aws_apigatewayv2_stage.default.invoke_url}/protected" }
