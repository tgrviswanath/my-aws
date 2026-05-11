terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

variable "project" { default = "handson" }

# ─── AWS Organization ─────────────────────────────────────────────────────────

resource "aws_organizations_organization" "main" {
  aws_service_access_principals = [
    "cloudtrail.amazonaws.com",
    "config.amazonaws.com",
    "guardduty.amazonaws.com",
    "securityhub.amazonaws.com",
    "sso.amazonaws.com",
  ]
  feature_set = "ALL"   # enables SCPs
}

# ─── Organizational Units ─────────────────────────────────────────────────────

resource "aws_organizations_organizational_unit" "security" {
  name      = "Security"
  parent_id = aws_organizations_organization.main.roots[0].id
}

resource "aws_organizations_organizational_unit" "workloads" {
  name      = "Workloads"
  parent_id = aws_organizations_organization.main.roots[0].id
}

resource "aws_organizations_organizational_unit" "dev" {
  name      = "Dev"
  parent_id = aws_organizations_organizational_unit.workloads.id
}

resource "aws_organizations_organizational_unit" "prod" {
  name      = "Prod"
  parent_id = aws_organizations_organizational_unit.workloads.id
}

resource "aws_organizations_organizational_unit" "sandbox" {
  name      = "Sandbox"
  parent_id = aws_organizations_organization.main.roots[0].id
}

# ─── SCP: Deny Root Usage ─────────────────────────────────────────────────────

resource "aws_organizations_policy" "deny_root" {
  name        = "DenyRootUsage"
  description = "Prevent use of root account credentials"
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DenyRootUser"
      Effect   = "Deny"
      Action   = "*"
      Resource = "*"
      Condition = {
        StringLike = {
          "aws:PrincipalArn" = ["arn:aws:iam::*:root"]
        }
      }
    }]
  })
}

resource "aws_organizations_policy_attachment" "deny_root_workloads" {
  policy_id = aws_organizations_policy.deny_root.id
  target_id = aws_organizations_organizational_unit.workloads.id
}

# ─── SCP: Restrict to Approved Regions ───────────────────────────────────────

resource "aws_organizations_policy" "restrict_regions" {
  name        = "RestrictToApprovedRegions"
  description = "Only allow us-east-1 and eu-west-1"
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DenyUnapprovedRegions"
      Effect = "Deny"
      NotAction = [
        "iam:*", "sts:*", "support:*",
        "cloudfront:*", "route53:*", "waf:*"
      ]
      Resource = "*"
      Condition = {
        StringNotIn = {
          "aws:RequestedRegion" = ["us-east-1", "eu-west-1"]
        }
      }
    }]
  })
}

resource "aws_organizations_policy_attachment" "restrict_regions_workloads" {
  policy_id = aws_organizations_policy.restrict_regions.id
  target_id = aws_organizations_organizational_unit.workloads.id
}

# ─── SCP: Require S3 Encryption ──────────────────────────────────────────────

resource "aws_organizations_policy" "require_s3_encryption" {
  name        = "RequireS3Encryption"
  description = "Deny creation of unencrypted S3 buckets"
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DenyUnencryptedS3"
      Effect = "Deny"
      Action = ["s3:PutObject"]
      Resource = "*"
      Condition = {
        StringNotEquals = {
          "s3:x-amz-server-side-encryption" = ["AES256", "aws:kms"]
        }
      }
    }]
  })
}

resource "aws_organizations_policy_attachment" "require_s3_encryption_workloads" {
  policy_id = aws_organizations_policy.require_s3_encryption.id
  target_id = aws_organizations_organizational_unit.workloads.id
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "org_id"          { value = aws_organizations_organization.main.id }
output "workloads_ou_id" { value = aws_organizations_organizational_unit.workloads.id }
output "dev_ou_id"       { value = aws_organizations_organizational_unit.dev.id }
output "prod_ou_id"      { value = aws_organizations_organizational_unit.prod.id }
