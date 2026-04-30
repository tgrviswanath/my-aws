# Lab 03: Configure IAM Roles, Policies & Cross-Account Access

## Objective
Practice IAM fundamentals: create users, groups, roles, custom policies, permission boundaries, and cross-account role assumption.

## Estimated Time: 45 minutes
## Estimated Cost: $0.00 (IAM is free)

---

## Step 1: Create IAM Groups and Users

```bash
# Create groups
aws iam create-group --group-name Developers
aws iam create-group --group-name ReadOnly

# Attach managed policies to groups
aws iam attach-group-policy \
  --group-name ReadOnly \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Create custom developer policy
aws iam create-policy \
  --policy-name DeveloperPolicy \
  --description "Developer access to dev resources" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowDevEC2",
        "Effect": "Allow",
        "Action": [
          "ec2:Describe*",
          "ec2:RunInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:TerminateInstances"
        ],
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "aws:RequestedRegion": "us-east-1"
          }
        }
      },
      {
        "Sid": "AllowDevS3",
        "Effect": "Allow",
        "Action": ["s3:*"],
        "Resource": [
          "arn:aws:s3:::dev-*",
          "arn:aws:s3:::dev-*/*"
        ]
      },
      {
        "Sid": "AllowLambdaDev",
        "Effect": "Allow",
        "Action": ["lambda:*"],
        "Resource": "arn:aws:lambda:us-east-1:*:function:dev-*"
      },
      {
        "Sid": "DenyIAMEscalation",
        "Effect": "Deny",
        "Action": [
          "iam:CreateUser",
          "iam:DeleteUser",
          "iam:AttachUserPolicy",
          "iam:PutUserPolicy"
        ],
        "Resource": "*"
      }
    ]
  }'

DEV_POLICY_ARN=$(aws iam list-policies \
  --query "Policies[?PolicyName=='DeveloperPolicy'].Arn" \
  --output text)

aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn $DEV_POLICY_ARN

# Create users
aws iam create-user --user-name alice
aws iam create-user --user-name bob

# Add to groups
aws iam add-user-to-group --user-name alice --group-name Developers
aws iam add-user-to-group --user-name bob --group-name ReadOnly

echo "Users and groups created"
```

## Step 2: Create Access Keys and Test

```bash
# Create access key for alice
ALICE_KEYS=$(aws iam create-access-key --user-name alice)
ALICE_KEY_ID=$(echo $ALICE_KEYS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['AccessKey']['AccessKeyId'])")
ALICE_SECRET=$(echo $ALICE_KEYS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['AccessKey']['SecretAccessKey'])")

echo "Alice Key ID: $ALICE_KEY_ID"

# Configure alice profile
aws configure set aws_access_key_id $ALICE_KEY_ID --profile alice
aws configure set aws_secret_access_key $ALICE_SECRET --profile alice
aws configure set region us-east-1 --profile alice

# Test alice's permissions
echo "Testing alice's permissions..."

# Should succeed (allowed)
aws s3 ls --profile alice 2>&1 | head -5

# Should fail (not allowed - wrong prefix)
aws s3 ls s3://prod-bucket --profile alice 2>&1

# Should fail (IAM denied)
aws iam create-user --user-name test --profile alice 2>&1
```

## Step 3: Create Service Role with Permission Boundary

```bash
# Create permission boundary policy
aws iam create-policy \
  --policy-name AppRoleBoundary \
  --description "Maximum permissions for app roles" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "secretsmanager:GetSecretValue"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Deny",
        "Action": [
          "iam:*",
          "organizations:*",
          "account:*"
        ],
        "Resource": "*"
      }
    ]
  }'

BOUNDARY_ARN=$(aws iam list-policies \
  --query "Policies[?PolicyName=='AppRoleBoundary'].Arn" \
  --output text)

# Create app role with permission boundary
aws iam create-role \
  --role-name lab-app-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --permissions-boundary $BOUNDARY_ARN

# Attach a broader policy (boundary will limit it)
aws iam attach-role-policy \
  --role-name lab-app-role \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

echo "Role created with permission boundary"
echo "Even though AdministratorAccess is attached,"
echo "the boundary limits actual permissions to the boundary policy"
```

## Step 4: Cross-Account Role Assumption (Simulated)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create a role that can be assumed by the same account (simulating cross-account)
aws iam create-role \
  --role-name lab-cross-account-role \
  --assume-role-policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Principal\": {
        \"AWS\": \"arn:aws:iam::${ACCOUNT_ID}:root\"
      },
      \"Action\": \"sts:AssumeRole\",
      \"Condition\": {
        \"StringEquals\": {
          \"sts:ExternalId\": \"lab-external-id-12345\"
        }
      }
    }]
  }'

# Attach read-only policy
aws iam attach-role-policy \
  --role-name lab-cross-account-role \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/lab-cross-account-role"

# Assume the role
ASSUMED=$(aws sts assume-role \
  --role-arn $ROLE_ARN \
  --role-session-name lab-session \
  --external-id lab-external-id-12345 \
  --duration-seconds 900)

# Extract temporary credentials
TEMP_KEY=$(echo $ASSUMED | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Credentials']['AccessKeyId'])")
TEMP_SECRET=$(echo $ASSUMED | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Credentials']['SecretAccessKey'])")
TEMP_TOKEN=$(echo $ASSUMED | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Credentials']['SessionToken'])")

# Configure assumed role profile
aws configure set aws_access_key_id $TEMP_KEY --profile assumed-role
aws configure set aws_secret_access_key $TEMP_SECRET --profile assumed-role
aws configure set aws_session_token $TEMP_TOKEN --profile assumed-role
aws configure set region us-east-1 --profile assumed-role

# Verify assumed identity
aws sts get-caller-identity --profile assumed-role

# Test permissions (read-only)
aws s3 ls --profile assumed-role 2>&1 | head -5

# Try to create (should fail - read-only)
aws s3 mb s3://test-bucket-should-fail --profile assumed-role 2>&1
```

## Step 5: IAM Policy Simulator

```bash
# Simulate if alice can perform actions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::${ACCOUNT_ID}:user/alice \
  --action-names s3:GetObject s3:DeleteObject iam:CreateUser \
  --resource-arns \
    arn:aws:s3:::dev-mybucket/file.txt \
    arn:aws:s3:::dev-mybucket/file.txt \
    arn:aws:iam::${ACCOUNT_ID}:user/newuser \
  --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}'

# Check last accessed services for alice
JOB_ID=$(aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::${ACCOUNT_ID}:user/alice \
  --query JobId --output text)

sleep 5

aws iam get-service-last-accessed-details \
  --job-id $JOB_ID \
  --query 'ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].{Service:ServiceName,LastAccess:LastAuthenticated}' \
  --output table
```

## Step 6: Generate Credential Report

```bash
# Generate credential report
aws iam generate-credential-report

sleep 5

# Download and parse
aws iam get-credential-report \
  --query 'Content' \
  --output text | base64 -d > /tmp/credential-report.csv

echo "Credential report:"
cat /tmp/credential-report.csv | python3 -c "
import sys, csv
reader = csv.DictReader(sys.stdin)
for row in reader:
    print(f\"User: {row['user']}, MFA: {row['mfa_active']}, Password: {row['password_enabled']}, Keys: {row['access_key_1_active']}\")
"
```

## Step 7: Cleanup

```bash
# Delete access keys
aws iam delete-access-key \
  --user-name alice \
  --access-key-id $ALICE_KEY_ID

# Remove users from groups
aws iam remove-user-from-group --user-name alice --group-name Developers
aws iam remove-user-from-group --user-name bob --group-name ReadOnly

# Delete users
aws iam delete-user --user-name alice
aws iam delete-user --user-name bob

# Detach and delete group policies
aws iam detach-group-policy \
  --group-name Developers \
  --policy-arn $DEV_POLICY_ARN
aws iam detach-group-policy \
  --group-name ReadOnly \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Delete groups
aws iam delete-group --group-name Developers
aws iam delete-group --group-name ReadOnly

# Delete policies
aws iam delete-policy --policy-arn $DEV_POLICY_ARN
aws iam delete-policy --policy-arn $BOUNDARY_ARN

# Delete roles
aws iam detach-role-policy \
  --role-name lab-app-role \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam delete-role --role-name lab-app-role

aws iam detach-role-policy \
  --role-name lab-cross-account-role \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam delete-role --role-name lab-cross-account-role

# Clean up profiles
aws configure --profile alice set aws_access_key_id ""
aws configure --profile assumed-role set aws_access_key_id ""

# Clean up files
rm -f /tmp/credential-report.csv

echo "Cleanup complete!"
```

---

## What You Learned

✅ Create IAM users, groups, and custom policies
✅ Apply least-privilege principle with specific resource ARNs
✅ Use permission boundaries to limit maximum permissions
✅ Assume cross-account roles with external ID
✅ Use IAM Policy Simulator to test permissions
✅ Generate and analyze credential reports
✅ Understand the difference between identity and resource policies
