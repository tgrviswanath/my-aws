# IAM — Real-World Use Cases

## Use Case 1: Least-Privilege Role for a Microservice

**Business Problem**: An order service Lambda needs to read from DynamoDB, write to SQS, and read secrets — nothing else.

```bash
# 1. Create the role
aws iam create-role \
  --role-name "order-service-role" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 2. Attach ONLY what the service needs (least privilege)
aws iam put-role-policy \
  --role-name "order-service-role" \
  --policy-name "OrderServicePermissions" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DynamoDBReadOrders",
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:us-east-1:123456789:table/orders"
      },
      {
        "Sid": "SQSSendToOrderQueue",
        "Effect": "Allow",
        "Action": ["sqs:SendMessage"],
        "Resource": "arn:aws:sqs:us-east-1:123456789:order-processing"
      },
      {
        "Sid": "SecretsManagerReadDBPassword",
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:us-east-1:123456789:secret:prod/orders/db-*"
      },
      {
        "Sid": "CloudWatchLogs",
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": "arn:aws:logs:us-east-1:123456789:log-group:/aws/lambda/order-service:*"
      }
    ]
  }'

# 3. Verify what the role can do (simulate)
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789:role/order-service-role \
  --action-names dynamodb:GetItem dynamodb:DeleteItem sqs:SendMessage s3:GetObject \
  --resource-arns \
    arn:aws:dynamodb:us-east-1:123456789:table/orders \
    arn:aws:dynamodb:us-east-1:123456789:table/orders \
    arn:aws:sqs:us-east-1:123456789:order-processing \
    arn:aws:s3:::any-bucket \
  --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}'
```

**What you learn**: Least privilege, resource-level permissions, wildcard in ARN, policy simulation.

---

## Use Case 2: Cross-Account Role Assumption

**Business Problem**: Data team in Account A needs to query production data in Account B's S3 bucket, but only during business hours.

```bash
ACCOUNT_A="111111111111"  # Data team
ACCOUNT_B="222222222222"  # Production

# ── In Account B (production) ─────────────────────────────────────────────────
# Create role that Account A can assume
aws iam create-role \
  --role-name "DataTeamCrossAccountRole" \
  --assume-role-policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Principal\": {\"AWS\": \"arn:aws:iam::${ACCOUNT_A}:root\"},
      \"Action\": \"sts:AssumeRole\",
      \"Condition\": {
        \"StringEquals\": {\"sts:ExternalId\": \"data-team-secret-id-12345\"},
        \"DateGreaterThan\": {\"aws:CurrentTime\": \"2024-01-01T08:00:00Z\"},
        \"DateLessThan\":    {\"aws:CurrentTime\": \"2024-01-01T18:00:00Z\"}
      }
    }]
  }"

# Grant read access to specific S3 prefix
aws iam put-role-policy \
  --role-name "DataTeamCrossAccountRole" \
  --policy-name "S3ReadAccess" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::prod-data-bucket",
        "arn:aws:s3:::prod-data-bucket/analytics/*"
      ]
    }]
  }'

# ── In Account A (data team) ──────────────────────────────────────────────────
# Allow data analysts to assume the cross-account role
aws iam put-user-policy \
  --user-name "data-analyst-alice" \
  --policy-name "AssumeProductionRole" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": \"sts:AssumeRole\",
      \"Resource\": \"arn:aws:iam::${ACCOUNT_B}:role/DataTeamCrossAccountRole\"
    }]
  }"

# ── Usage (data analyst assumes the role) ─────────────────────────────────────
CREDS=$(aws sts assume-role \
  --role-arn "arn:aws:iam::${ACCOUNT_B}:role/DataTeamCrossAccountRole" \
  --role-session-name "alice-analytics-session" \
  --external-id "data-team-secret-id-12345" \
  --duration-seconds 3600)

export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDS | jq -r '.Credentials.SessionToken')

# Now can access prod S3 with temporary credentials
aws s3 ls s3://prod-data-bucket/analytics/
```

**What you learn**: Cross-account roles, ExternalId for third-party access, time-based conditions, temporary credentials.

---

## Use Case 3: Attribute-Based Access Control (ABAC)

**Business Problem**: 50 teams each need access to their own resources. Instead of 50 policies, use tags to control access dynamically.

```bash
# 1. Tag all resources with team name
aws s3api put-bucket-tagging \
  --bucket "team-alpha-data" \
  --tagging 'TagSet=[{Key=Team,Value=alpha}]'

aws dynamodb tag-resource \
  --resource-arn arn:aws:dynamodb:us-east-1:123456789:table/alpha-orders \
  --tags Key=Team,Value=alpha

# 2. Create ONE policy that works for ALL teams
aws iam create-policy \
  --policy-name "TeamBasedAccess" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "S3TeamAccess",
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "s3:ResourceTag/Team": "${aws:PrincipalTag/Team}"
          }
        }
      },
      {
        "Sid": "DynamoDBTeamAccess",
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "dynamodb:ResourceTag/Team": "${aws:PrincipalTag/Team}"
          }
        }
      }
    ]
  }'

# 3. Tag IAM users/roles with their team
aws iam tag-user \
  --user-name "alice" \
  --tags Key=Team,Value=alpha

aws iam tag-user \
  --user-name "bob" \
  --tags Key=Team,Value=beta

# 4. Attach the SAME policy to all users
aws iam attach-user-policy \
  --user-name "alice" \
  --policy-arn arn:aws:iam::123456789:policy/TeamBasedAccess

aws iam attach-user-policy \
  --user-name "bob" \
  --policy-arn arn:aws:iam::123456789:policy/TeamBasedAccess

# Now: alice can only access resources tagged Team=alpha
#      bob can only access resources tagged Team=beta
# One policy scales to 1000 teams!
```

**What you learn**: ABAC with tags, `aws:PrincipalTag`, scalable access control without policy explosion.

---

## Use Case 4: Emergency Break-Glass Access

**Business Problem**: Production is down at 3 AM. On-call engineer needs temporary admin access but normally has read-only.

```bash
# 1. Create break-glass role (admin, but requires MFA + approval)
aws iam create-role \
  --role-name "BreakGlassAdminRole" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789:root"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "NumericLessThan": {"aws:MultiFactorAuthAge": "300"}
      }
    }]
  }'

aws iam attach-role-policy \
  --role-name "BreakGlassAdminRole" \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 2. CloudTrail alert when break-glass is used
aws events put-rule \
  --name "BreakGlassUsed" \
  --event-pattern '{
    "source": ["aws.sts"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventName": ["AssumeRole"],
      "requestParameters": {
        "roleArn": ["arn:aws:iam::123456789:role/BreakGlassAdminRole"]
      }
    }
  }' \
  --state ENABLED

aws events put-targets \
  --rule "BreakGlassUsed" \
  --targets '[{
    "Id": "AlertSecurityTeam",
    "Arn": "arn:aws:sns:us-east-1:123456789:security-alerts",
    "InputTransformer": {
      "InputPathsMap": {"user": "$.detail.userIdentity.arn", "time": "$.time"},
      "InputTemplate": "\"🚨 BREAK-GLASS USED: <user> assumed admin role at <time>\""
    }
  }]'

# 3. On-call engineer uses break-glass (with MFA)
aws sts assume-role \
  --role-arn arn:aws:iam::123456789:role/BreakGlassAdminRole \
  --role-session-name "oncall-alice-incident-2024" \
  --serial-number arn:aws:iam::123456789:mfa/alice \
  --token-code 123456 \
  --duration-seconds 3600
```

**What you learn**: MFA-required roles, break-glass pattern, CloudTrail alerting on sensitive actions.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using root account for daily work | Catastrophic if compromised | Create IAM users, lock root with MFA |
| `"Resource": "*"` on sensitive actions | Over-permissive | Specify exact resource ARNs |
| Storing access keys in code | Credential exposure | Use IAM roles (EC2/Lambda) or environment variables |
| No MFA on privileged accounts | Account takeover risk | Enforce MFA with SCP |
| Not rotating access keys | Long-lived credentials = risk | Rotate every 90 days or use roles |
| Inline policies instead of managed | Hard to audit and reuse | Use customer-managed policies |
