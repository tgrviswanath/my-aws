# Project 1.3 — IAM Security Fundamentals

## 1. Overview

**Problem:** Every new AWS account starts with a root user that has unlimited permissions. Teams often share credentials or give everyone `AdministratorAccess` "just to avoid permission errors." This creates serious security risks: compromised credentials have unlimited blast radius, no audit trail of who did what, and no ability to revoke specific access.

**Solution:** AWS Identity and Access Management (IAM) lets you create identities with precise permissions, enforce MFA, and use temporary credentials via roles instead of permanent access keys.

**Objectives:**
- Create a user group `developers` with least-privilege permissions (ReadOnly)
- Create an IAM user and add them to the group
- Enable MFA (Multi-Factor Authentication) for the user
- Create an IAM role with S3 read access and assume it via STS
- Apply a password policy for the account
- Understand the difference between IAM users, groups, roles, and policies

**Expected Result:** A secure IAM setup with users in groups, MFA enforced, and roles ready for services to assume — with zero shared root credentials.

---

## 2. Architecture

```
AWS Account (Root)
│
├── Account Password Policy (min length, complexity, rotation)
│
├── IAM Groups
│   ├── developers
│   │   └── Policy: ReadOnlyAccess (AWS managed)
│   └── admins
│       └── Policy: AdministratorAccess (AWS managed)
│
├── IAM Users
│   └── dev-user-01
│       ├── Member of: developers group
│       ├── MFA Device: Virtual MFA (Google Authenticator / Authy)
│       └── Permissions: inherited from developers group
│
├── IAM Roles
│   └── s3-read-role
│       ├── Trust Policy: allows specific IAM user to assume this role
│       ├── Permission Policy: AmazonS3ReadOnlyAccess
│       └── Usage: aws sts assume-role → temporary credentials
│
└── IAM Policies
    ├── AWS Managed: ReadOnlyAccess, AmazonS3ReadOnlyAccess
    └── Custom: inline policies for specific needs
```

**Credential Chain (STS Assume Role):**
```
IAM User → aws sts assume-role → STS → Temporary credentials (15min–12hr)
                                          ├── AccessKeyId
                                          ├── SecretAccessKey
                                          └── SessionToken
```

---

## 3. Prerequisites

### AWS Account & Permissions
- [ ] Logged in as root user or an IAM user with `IAMFullAccess`
- [ ] AWS CLI installed and configured as root or admin user
- [ ] MFA app installed on your phone: Google Authenticator, Authy, or Microsoft Authenticator

### Tools
- [ ] AWS CLI v2: `aws --version`
- [ ] `jq` (optional, for parsing JSON): `jq --version`
- [ ] MFA authenticator app

### Verify Access
```bash
aws sts get-caller-identity
# Check the Account field matches your AWS account ID

aws iam get-account-summary
# Should return account IAM summary without error
```

---

## 4. Folder Structure

```
project_1.3_iam/
├── GUIDE.md                      ← This file
├── steps_awsconsoleui.md         ← Console walkthrough
├── cost_estimate.md              ← Cost breakdown (IAM = free)
├── policies/
│   ├── developer-policy.json     ← Custom developer permissions
│   ├── s3-read-policy.json       ← S3 read-only policy
│   └── trust-policy.json         ← Role trust relationship
└── scripts/
    ├── setup_iam.sh              ← CLI setup script
    ├── assume_role.sh            ← STS assume-role example
    └── cleanup.sh                ← Teardown script
```

**Sample `trust-policy.json`:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/dev-user-01"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## 5. Implementation

### Decision Point 1: IAM User vs IAM Role

| Feature | IAM User | IAM Role |
|---------|----------|---------|
| Credentials | Long-term (access key) | Temporary (STS, 15min–12hr) |
| Best for | Human users, CLI access | AWS services, cross-account, applications |
| Rotation | Manual | Automatic (STS rotates) |
| Risk if leaked | High (permanent) | Low (expires automatically) ✅ |
| MFA support | ✅ Yes | ✅ Yes (with session policies) |
| Recommended for EC2/Lambda | ❌ No (use role) | ✅ Yes, always use a role |

**Decision:** Use IAM roles for services. Use IAM users with MFA for human access. Never embed access keys in application code.

---

### Prerequisites Check

```bash
# 1. Confirm you have IAM admin access
aws iam list-users --query 'Users[*].UserName' --output table

# 2. Check current account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# 3. Check password policy
aws iam get-account-password-policy 2>/dev/null || echo "No password policy set"

# 4. List existing groups
aws iam list-groups --query 'Groups[*].GroupName' --output table
```

---

### 5A. Console Implementation

See `steps_awsconsoleui.md` for the full AWS Console walkthrough.

**High-level Console steps:**
1. IAM → Account settings → Set password policy (min 12 chars, require MFA)
2. IAM → User groups → Create group `developers` → attach `ReadOnlyAccess`
3. IAM → Users → Create user `dev-user-01` → console access → add to `developers`
4. IAM → Users → `dev-user-01` → Security credentials → Assign MFA device
5. IAM → Roles → Create role → trusted entity: IAM user → attach `AmazonS3ReadOnlyAccess`
6. Test: switch role in console, verify S3 access

---

### 5B. CLI Implementation

#### Step 1: Set Account Password Policy

```bash
aws iam update-account-password-policy \
  --minimum-password-length 12 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --allow-users-to-change-password \
  --max-password-age 90 \
  --password-reuse-prevention 5

echo "✅ Password policy applied"
```

#### Step 2: Create Developer Group

```bash
aws iam create-group --group-name developers
echo "✅ Group 'developers' created"

# Attach AWS managed ReadOnlyAccess policy
aws iam attach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

echo "✅ ReadOnlyAccess policy attached to developers group"
```

#### Step 3: Create IAM User

```bash
USERNAME="dev-user-01"

aws iam create-user --user-name $USERNAME
echo "✅ User '$USERNAME' created"

# Create login profile (console password)
TEMP_PASSWORD="TempPass123!$(date +%s)"
aws iam create-login-profile \
  --user-name $USERNAME \
  --password "$TEMP_PASSWORD" \
  --password-reset-required

echo "Temporary password: $TEMP_PASSWORD"
echo "(User will be required to reset on first login)"
```

#### Step 4: Add User to Group

```bash
aws iam add-user-to-group \
  --user-name $USERNAME \
  --group-name developers

echo "✅ '$USERNAME' added to 'developers' group"

# Verify
aws iam list-groups-for-user --user-name $USERNAME \
  --query 'Groups[*].GroupName' --output table
```

#### Step 5: Create Access Key (for CLI use)

```bash
# Create access key for programmatic access
ACCESS_KEY=$(aws iam create-access-key --user-name $USERNAME)

ACCESS_KEY_ID=$(echo $ACCESS_KEY | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['AccessKey']['AccessKeyId'])")
SECRET_KEY=$(echo $ACCESS_KEY | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['AccessKey']['SecretAccessKey'])")

echo "Access Key ID: $ACCESS_KEY_ID"
echo "Secret Access Key: $SECRET_KEY"
echo "⚠️  Save these securely — the secret key is shown only once!"
```

#### Step 6: Create IAM Role with S3 Read Access

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="s3-read-role"

# Trust policy — allow our dev user to assume this role
cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::$ACCOUNT_ID:user/$USERNAME"
      },
      "Action": "sts:AssumeRole",
      "Condition": {}
    }
  ]
}
EOF

# Create the role
ROLE_ARN=$(aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Role for S3 read access - dev users" \
  --query 'Role.Arn' --output text)

echo "✅ Role created: $ROLE_ARN"

# Attach S3 read-only policy
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

echo "✅ AmazonS3ReadOnlyAccess attached to role"
```

#### Step 7: Allow User to Assume the Role

```bash
# Create inline policy on the user allowing them to assume the role
cat > /tmp/assume-role-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "$ROLE_ARN"
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name $USERNAME \
  --policy-name "AllowAssumeS3ReadRole" \
  --policy-document file:///tmp/assume-role-policy.json

echo "✅ User can now assume the S3 read role"
```

#### Step 8: Test STS Assume Role

```bash
# Configure AWS CLI with the dev user's credentials
aws configure set aws_access_key_id $ACCESS_KEY_ID --profile dev-user
aws configure set aws_secret_access_key $SECRET_KEY --profile dev-user
aws configure set region us-east-1 --profile dev-user

# Assume the role as the dev user
ASSUMED=$(aws sts assume-role \
  --role-arn $ROLE_ARN \
  --role-session-name "dev-session-$(date +%s)" \
  --profile dev-user)

# Extract temporary credentials
TEMP_ACCESS_KEY=$(echo $ASSUMED | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")
TEMP_SECRET=$(echo $ASSUMED | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")
TEMP_TOKEN=$(echo $ASSUMED | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SessionToken'])")

echo "✅ Role assumed successfully"
echo "Temporary credentials expire at:"
echo $ASSUMED | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['Expiration'])"

# Use temporary credentials to list S3 buckets
export AWS_ACCESS_KEY_ID=$TEMP_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$TEMP_SECRET
export AWS_SESSION_TOKEN=$TEMP_TOKEN

aws s3 ls  # Should work — S3 read access
# aws ec2 describe-instances  # Should FAIL — no EC2 access (tests least privilege)

# Unset temp credentials
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

---

## 6. Code Deep Dive

### IAM Policy Structure Explained

```json
{
  "Version": "2012-10-17",       // Policy language version — always use this date
  "Statement": [                  // Array of permission statements
    {
      "Sid": "AllowS3Read",       // Statement ID — optional human-readable label
      "Effect": "Allow",          // Allow or Deny
      "Principal": "*",           // Who (for resource-based policies)
      "Action": [                 // What actions
        "s3:GetObject",           // Read individual objects
        "s3:ListBucket"           // List bucket contents
      ],
      "Resource": [               // On what resources
        "arn:aws:s3:::my-bucket",        // The bucket itself (for ListBucket)
        "arn:aws:s3:::my-bucket/*"       // Objects in the bucket (for GetObject)
      ],
      "Condition": {              // Optional: when this applies
        "StringEquals": {
          "s3:prefix": ["public/"]  // Only objects with prefix "public/"
        }
      }
    }
  ]
}
```

### Trust Policy vs Permission Policy

```
Trust Policy (WHO can assume the role):
  "Principal": { "AWS": "arn:aws:iam::123456789:user/dev-user-01" }
  → Answers: "Who is allowed to use this role?"

Permission Policy (WHAT the role can do):
  "Action": "s3:GetObject", "Resource": "arn:aws:s3:::my-bucket/*"
  → Answers: "What can entities using this role do?"
```

### MFA with CLI (Virtual MFA)

```bash
# Get your MFA device ARN
aws iam list-mfa-devices --user-name $USERNAME \
  --query 'MFADevices[0].SerialNumber' --output text

# Get temporary session token with MFA
aws sts get-session-token \
  --serial-number arn:aws:iam::$ACCOUNT_ID:mfa/$USERNAME \
  --token-code 123456 \
  --duration-seconds 3600
# Replace 123456 with the 6-digit code from your MFA app
```

---

## 7. Verification

```bash
# List all users
aws iam list-users --query 'Users[*].[UserName,CreateDate]' --output table

# List groups and their policies
aws iam list-groups --query 'Groups[*].GroupName' --output table
aws iam list-attached-group-policies --group-name developers --output table

# Verify user is in group
aws iam list-groups-for-user --user-name dev-user-01 \
  --query 'Groups[*].GroupName' --output table

# Verify role and its policies
aws iam list-attached-role-policies --role-name s3-read-role --output table

# Simulate permissions (policy simulator)
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::$ACCOUNT_ID:user/dev-user-01" \
  --action-names s3:ListBuckets ec2:DescribeInstances \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' \
  --output table
```

---

## 8. Observations

### Principle of Least Privilege in Practice

- `ReadOnlyAccess` gives `Describe*`, `List*`, `Get*` on almost all services — 0 write permissions
- Test by trying to create a resource as `dev-user-01` — all write operations should return `AccessDenied`
- Gradually add permissions as needed rather than starting broad

### IAM Access Advisor

```bash
# See when services were last accessed by a user
aws iam generate-service-last-accessed-details \
  --arn "arn:aws:iam::$ACCOUNT_ID:user/dev-user-01"
# Returns a JobId — check results with:
aws iam get-service-last-accessed-details --job-id <JobId>
```

### Credential Report

```bash
# Generate account-wide credential report
aws iam generate-credential-report
aws iam get-credential-report \
  --query 'Content' --output text | base64 -d | head -20
# Shows: user, ARN, password enabled, MFA active, last used dates
```

---

## 9. Screenshots

Capture at these key steps:
1. IAM Groups page showing `developers` group with `ReadOnlyAccess` policy attached
2. IAM Users page showing `dev-user-01` with group membership
3. MFA device assignment confirmation dialog
4. IAM Role `s3-read-role` showing trust relationships and permissions
5. Terminal showing successful `aws sts assume-role` output with temporary credentials
6. Terminal showing `aws s3 ls` succeeding with temporary credentials
7. Terminal showing `aws ec2 describe-instances` failing (AccessDenied) — proving least privilege

---

## 10. Cleanup

```bash
# 1. Detach and delete user policies
aws iam delete-user-policy \
  --user-name dev-user-01 \
  --policy-name AllowAssumeS3ReadRole

# 2. Remove user from group
aws iam remove-user-from-group \
  --user-name dev-user-01 \
  --group-name developers

# 3. Delete user's access keys
ACCESS_KEY_ID=$(aws iam list-access-keys \
  --user-name dev-user-01 \
  --query 'AccessKeyMetadata[0].AccessKeyId' --output text)
aws iam delete-access-key \
  --user-name dev-user-01 \
  --access-key-id $ACCESS_KEY_ID

# 4. Delete login profile
aws iam delete-login-profile --user-name dev-user-01

# 5. Delete user
aws iam delete-user --user-name dev-user-01
echo "✅ User deleted"

# 6. Detach role policies and delete role
aws iam detach-role-policy \
  --role-name s3-read-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam delete-role --role-name s3-read-role
echo "✅ Role deleted"

# 7. Detach group policies and delete group
aws iam detach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

aws iam delete-group --group-name developers
echo "✅ Group deleted"
```

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
