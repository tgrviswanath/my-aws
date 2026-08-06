# IAM — Identity and Access Management Deep Dive

## What is IAM?
IAM controls who (authentication) can do what (authorization) in AWS. It's the foundation of AWS security.

---

## Core Components

```
IAM
├── Users       — Long-term credentials for humans/applications
├── Groups      — Collection of users with shared permissions
├── Roles       — Temporary credentials for services/cross-account
├── Policies    — JSON documents defining permissions
└── Identity Providers — SAML/OIDC federation
```

---

## IAM Policies

### Policy Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadOnSpecificBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        },
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    },
    {
      "Sid": "DenyDeleteActions",
      "Effect": "Deny",
      "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

### Policy Evaluation Logic

```
Explicit Deny → DENY (always wins)
     ↓
No matching Allow → DENY (default)
     ↓
Explicit Allow → ALLOW
```

**Key rule**: Explicit Deny always overrides Allow. Default is Deny.

### Policy Types

| Type | Attached To | Use Case |
|------|------------|---------|
| AWS Managed | Users/Groups/Roles | Common permissions (ReadOnlyAccess) |
| Customer Managed | Users/Groups/Roles | Custom permissions |
| Inline | Single user/group/role | Strict 1:1 relationship |
| Resource-based | Resources (S3, SQS) | Cross-account access |
| Permission Boundary | Users/Roles | Max permissions ceiling |
| SCP (Service Control Policy) | AWS Organizations | Account-level guardrails |
| Session Policy | Assumed role sessions | Restrict temporary credentials |

---

## IAM Roles

### EC2 Instance Profile

```bash
# Create role
aws iam create-role \
  --role-name EC2AppRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policy
aws iam put-role-policy \
  --role-name EC2AppRole \
  --policy-name AppPermissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject"],
        "Resource": "arn:aws:s3:::my-app-bucket/*"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:us-east-1:123456789:secret:prod/*"
      },
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
        "Resource": "arn:aws:dynamodb:us-east-1:123456789:table/Orders"
      }
    ]
  }'

# Create instance profile
aws iam create-instance-profile --instance-profile-name EC2AppProfile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2AppProfile \
  --role-name EC2AppRole
```

### Cross-Account Role

```bash
# In Account B (target): Create role that Account A can assume
aws iam create-role \
  --role-name CrossAccountRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT-A-ID:root"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"}
      }
    }]
  }'

# In Account A: Assume the role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT-B-ID:role/CrossAccountRole \
  --role-session-name MySession \
  --serial-number arn:aws:iam::ACCOUNT-A-ID:mfa/alice \
  --token-code 123456
```

### Lambda Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789:table/MyTable"
    },
    {
      "Effect": "Allow",
      "Action": ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DeleteNetworkInterface"],
      "Resource": "*"
    }
  ]
}
```

---

## Least Privilege Principle

```bash
# Use IAM Access Analyzer to find unused permissions
aws accessanalyzer create-analyzer \
  --analyzer-name prod-analyzer \
  --type ACCOUNT

# Generate least-privilege policy from CloudTrail
aws accessanalyzer generate-policy \
  --trail-arn arn:aws:cloudtrail:us-east-1:123456789:trail/my-trail \
  --output-format JSON

# Use IAM Access Advisor to see last used services
aws iam get-service-last-accessed-details \
  --job-id $(aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::123456789:role/MyRole \
    --query JobId --output text)
```

---

## Permission Boundaries

Limit the maximum permissions a user or role can have, even if their policies allow more.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*", "dynamodb:*", "lambda:*"],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": ["iam:*", "organizations:*"],
      "Resource": "*"
    }
  ]
}
```

```bash
# Apply permission boundary to role
aws iam put-role-permissions-boundary \
  --role-name DeveloperRole \
  --permissions-boundary arn:aws:iam::123456789:policy/DeveloperBoundary
```

---

## Service Control Policies (SCPs)

Organization-level guardrails. Apply to all accounts in an OU.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeavingOrganization",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    },
    {
      "Sid": "RequireIMDSv2",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    },
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*", "sts:*", "cloudfront:*",
        "route53:*", "support:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        }
      }
    }
  ]
}
```

---

## IAM Best Practices

```bash
# 1. Enable MFA for root and all IAM users
aws iam enable-mfa-device \
  --user-name alice \
  --serial-number arn:aws:iam::123456789:mfa/alice \
  --authentication-code1 123456 \
  --authentication-code2 789012

# 2. Rotate access keys
aws iam create-access-key --user-name alice
# Update application with new key
aws iam delete-access-key \
  --user-name alice \
  --access-key-id YOUR_ACCESS_KEY_ID

# 3. Use IAM roles instead of access keys for EC2/Lambda
# 4. Never use root account for daily operations
# 5. Use AWS Organizations + SCPs for guardrails
# 6. Enable CloudTrail for all IAM actions
# 7. Use IAM Access Analyzer to find external access

# Check for root account usage
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=root \
  --start-time 2024-01-01T00:00:00Z

# Find users without MFA
aws iam generate-credential-report
aws iam get-credential-report --query 'Content' --output text | \
  base64 -d | grep -v ',true,' | grep -v 'mfa_active'
```

---

## CloudFormation Template

```yaml
Resources:
  AppRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: AppRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
      Policies:
        - PolicyName: AppPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "arn:aws:s3:::${DataBucket}/*"
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource: !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:prod/*"

  InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref AppRole
```

---

## Interview Q&A

### Q1: What is the difference between IAM users, groups, and roles?
**Users**: Long-term credentials (password + access keys) for humans or applications. Avoid for applications — use roles.
**Groups**: Collection of users. Attach policies to groups, not individual users. Simplifies permission management.
**Roles**: Temporary credentials via STS. No long-term credentials. Used by: EC2 instances, Lambda, ECS tasks, cross-account access, federated users. Always prefer roles over access keys.

### Q2: How does IAM policy evaluation work?
1. Start with implicit Deny (default)
2. Evaluate all applicable policies (identity + resource + SCP + permission boundary)
3. If any explicit Deny → DENY (final)
4. If Allow in identity policy AND resource policy (for cross-account) → ALLOW
5. If Allow in identity policy (same account) → ALLOW
6. Otherwise → DENY

### Q3: What is the difference between an IAM role and a resource-based policy?
**IAM role**: Identity-based. Principal assumes the role and gets temporary credentials. Used for cross-account access, EC2/Lambda, federated users.
**Resource-based policy**: Attached to the resource (S3 bucket, SQS queue, Lambda). Grants access to specified principals without them needing to assume a role. Simpler for cross-account S3 access. Both can be used together.

### Q4: What is a Permission Boundary?
A permission boundary is an IAM managed policy that sets the maximum permissions an IAM entity can have. Even if the entity's policies allow more, the boundary limits what's actually allowed. Use case: Allow developers to create IAM roles for their applications, but prevent them from creating roles with more permissions than they themselves have (privilege escalation prevention).

### Q5: How do you implement least privilege in practice?
1. Start with no permissions, add only what's needed
2. Use IAM Access Analyzer to generate policies from CloudTrail activity
3. Use IAM Access Advisor to identify unused permissions
4. Set permission boundaries for developer-created roles
5. Use SCPs at organization level for hard limits
6. Regular access reviews — remove unused permissions
7. Use conditions to restrict by IP, MFA, time, region
8. Prefer AWS managed policies as starting point, then restrict
