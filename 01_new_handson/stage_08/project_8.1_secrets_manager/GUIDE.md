# Project 8.1 — AWS Secrets Manager
## Store RDS Credentials with Automatic Rotation

---

## Prerequisites Check

Before starting, verify the following:

- [ ] AWS CLI installed and configured (`aws --version`, `aws sts get-caller-identity`)
- [ ] IAM permissions: `secretsmanager:*`, `rds:*`, `lambda:*`, `iam:CreateRole`, `iam:AttachRolePolicy`
- [ ] AWS region set: `aws configure get region` (use `us-east-1` for this guide)
- [ ] RDS instance running (or use parameter `--db-instance-identifier` for an existing one)
- [ ] Python 3.8+ with boto3: `pip install boto3`
- [ ] jq installed for JSON parsing: `jq --version`

```bash
# Verify AWS CLI access
aws sts get-caller-identity
aws configure get region
```

---

## Decision Point 1

**Should you use Secrets Manager, SSM Parameter Store, or environment variables?**

| Option | Cost | Rotation | Best For |
|--------|------|----------|----------|
| **Secrets Manager** ✅ | $0.40/secret/month | ✅ Automatic | RDS, API keys, production |
| **SSM Parameter Store** | Free (standard) / $0.05/param (advanced) | ❌ Manual | Config values, non-sensitive |
| **Environment Variables** | Free | ❌ Manual | Local dev only — never production |

**Choose Secrets Manager when:**
- You need automatic credential rotation
- Storing database passwords, OAuth tokens, API keys
- Compliance requires secret lifecycle management (SOC2, PCI-DSS)

**Choose SSM Parameter Store when:**
- Storing non-sensitive config (feature flags, URLs)
- You want free tier parameter storage
- No rotation needed

**Verdict for this project:** Secrets Manager ✅ — RDS credentials require rotation.

---

## 1. Architecture Overview

```
Application (Lambda / EC2 / ECS)
        │
        │  boto3 get_secret_value()
        ▼
  Secrets Manager ◄──── Rotation Lambda (every 30 days)
        │                       │
        │                       ▼
        └──────────────► RDS Instance (password updated)
```

**Key concepts:**
- **Secret**: Encrypted key-value pair stored in AWS KMS
- **Rotation Lambda**: AWS-managed function that updates both Secrets Manager and RDS
- **Resource Policy**: Controls which principals can access the secret
- **VPC Endpoint**: Required if Lambda/App runs in private subnet (no NAT)

---

## 2. Create KMS Key (Optional but Recommended)

By default, Secrets Manager uses the AWS-managed key `aws/secretsmanager`. For production, create a customer-managed key (CMK):

```bash
# Create CMK for Secrets Manager
KEY_ID=$(aws kms create-key \
  --description "Secrets Manager CMK for RDS credentials" \
  --key-usage ENCRYPT_DECRYPT \
  --query 'KeyMetadata.KeyId' \
  --output text)

echo "KMS Key ID: $KEY_ID"

# Create alias
aws kms create-alias \
  --alias-name alias/secrets-manager-rds \
  --target-key-id $KEY_ID

# Verify
aws kms describe-key --key-id alias/secrets-manager-rds \
  --query 'KeyMetadata.{KeyId:KeyId,State:KeyState}'
```

---

## 3. Create the Secret (5B CLI Path)

```bash
# Set variables
SECRET_NAME="prod/myapp/rds-credentials"
DB_HOST="mydb.cluster-xxxx.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="myapp"
DB_USER="admin"
DB_PASS="InitialPassword123!"  # Will be rotated

# Create secret with JSON structure
SECRET_ARN=$(aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --description "RDS PostgreSQL credentials for myapp production" \
  --kms-key-id alias/secrets-manager-rds \
  --secret-string "{
    \"username\": \"$DB_USER\",
    \"password\": \"$DB_PASS\",
    \"engine\": \"postgres\",
    \"host\": \"$DB_HOST\",
    \"port\": $DB_PORT,
    \"dbname\": \"$DB_NAME\",
    \"dbInstanceIdentifier\": \"myapp-prod-db\"
  }" \
  --tags '[
    {"Key":"Environment","Value":"production"},
    {"Key":"Project","Value":"myapp"},
    {"Key":"ManagedBy","Value":"secrets-manager"}
  ]' \
  --query 'ARN' \
  --output text)

echo "Secret ARN: $SECRET_ARN"
```

---

## 4. Retrieve Secret Value

```bash
# Retrieve current secret value
aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --query 'SecretString' \
  --output text | jq .

# Retrieve specific fields
aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --query 'SecretString' \
  --output text | jq -r '.password'

# Get secret metadata (not the value)
aws secretsmanager describe-secret \
  --secret-id "$SECRET_NAME"
```

---

## 5A. Console: Create Secret with RDS Rotation

**Step-by-step in AWS Management Console:**

1. Navigate to **AWS Secrets Manager** → **Store a new secret**
2. Secret type: **Credentials for Amazon RDS database**
3. Enter username and password
4. Select your RDS database from the dropdown
5. Click **Next** → Set **Secret name**: `prod/myapp/rds-credentials`
6. Add tags: `Environment=production`, `Project=myapp`
7. **Configure rotation:**
   - Enable automatic rotation: ✅
   - Rotation schedule: **30 days**
   - Rotation function: **Create a new Lambda function**
   - Lambda function name: `SecretsManagerRDSPostgreSQLRotation`
8. Review and **Store**

---

## 5B. CLI: Configure Automatic Rotation

```bash
# Get the RDS instance ARN
DB_INSTANCE_ARN=$(aws rds describe-db-instances \
  --db-instance-identifier myapp-prod-db \
  --query 'DBInstances[0].DBInstanceArn' \
  --output text)

# Enable rotation with 30-day schedule
# AWS creates the rotation Lambda automatically for RDS secrets
aws secretsmanager rotate-secret \
  --secret-id "$SECRET_NAME" \
  --rotation-rules "{
    \"AutomaticallyAfterDays\": 30
  }"

# Check rotation status
aws secretsmanager describe-secret \
  --secret-id "$SECRET_NAME" \
  --query '{
    RotationEnabled: RotationEnabled,
    RotationLambdaARN: RotationLambdaARN,
    LastRotatedDate: LastRotatedDate,
    NextRotationDate: NextRotationDate
  }'
```

---

## 6. Create IAM Policy for Application Access

```bash
# Create policy allowing app to read specific secret
cat > /tmp/secrets-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadRDSSecret",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:prod/myapp/*"
    },
    {
      "Sid": "AllowKMSDecrypt",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name SecretsManagerReadRDS \
  --policy-document file:///tmp/secrets-policy.json \
  --description "Allow application to read RDS credentials from Secrets Manager"
```

---

## 7. Retrieve Secret via boto3 (Python SDK)

```python
# app/db_connection.py
import boto3
import json
import psycopg2
from botocore.exceptions import ClientError


def get_rds_credentials(secret_name: str, region: str = "us-east-1") -> dict:
    """Retrieve RDS credentials from Secrets Manager at runtime."""
    client = boto3.client("secretsmanager", region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Secret {secret_name} not found")
        elif error_code == "AccessDeniedException":
            raise PermissionError(f"No access to secret {secret_name}")
        raise


def get_db_connection():
    """Get database connection using credentials from Secrets Manager."""
    creds = get_rds_credentials("prod/myapp/rds-credentials")
    
    conn = psycopg2.connect(
        host=creds["host"],
        port=creds["port"],
        database=creds["dbname"],
        user=creds["username"],
        password=creds["password"],
        connect_timeout=5,
    )
    return conn


# Cache credentials to avoid excessive API calls (respect rotation window)
import functools
import time

_cache = {}

def get_credentials_cached(secret_name: str, ttl_seconds: int = 300) -> dict:
    """Cache credentials for TTL seconds to reduce Secrets Manager API calls."""
    now = time.time()
    if secret_name in _cache:
        creds, timestamp = _cache[secret_name]
        if now - timestamp < ttl_seconds:
            return creds
    
    creds = get_rds_credentials(secret_name)
    _cache[secret_name] = (creds, now)
    return creds
```

---

## 8. Add Resource Policy to Secret

```bash
# Restrict secret access to specific IAM role only
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
APP_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/myapp-ec2-role"

cat > /tmp/resource-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAppRoleOnly",
      "Effect": "Allow",
      "Principal": {
        "AWS": "$APP_ROLE_ARN"
      },
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyAllOthers",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "ArnNotEquals": {
          "aws:PrincipalArn": "$APP_ROLE_ARN"
        }
      }
    }
  ]
}
EOF

aws secretsmanager put-resource-policy \
  --secret-id "$SECRET_NAME" \
  --resource-policy file:///tmp/resource-policy.json \
  --block-public-policy
```

---

## 9. Force Manual Rotation (Testing)

```bash
# Trigger immediate rotation (for testing — does not reset 30-day timer)
aws secretsmanager rotate-secret \
  --secret-id "$SECRET_NAME" \
  --rotate-immediately

# Monitor rotation progress
watch -n 5 "aws secretsmanager describe-secret \
  --secret-id '$SECRET_NAME' \
  --query '{RotationEnabled:RotationEnabled,LastRotatedDate:LastRotatedDate}'"

# List secret versions after rotation
aws secretsmanager list-secret-version-ids \
  --secret-id "$SECRET_NAME" \
  --include-deprecated
```

---

## 10. Verify Complete Setup

```bash
# Full verification checklist
echo "=== Secrets Manager Verification ==="

# 1. Secret exists and is accessible
aws secretsmanager describe-secret --secret-id "$SECRET_NAME" \
  --query '{Name:Name,ARN:ARN,RotationEnabled:RotationEnabled}' | jq .

# 2. Can retrieve value
aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" \
  --query 'SecretString' --output text | jq 'keys'

# 3. Rotation is configured
aws secretsmanager describe-secret --secret-id "$SECRET_NAME" \
  --query 'RotationRules' | jq .

# 4. Check CloudTrail for access events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue \
  --max-results 5 | jq '.Events[].EventName'

echo "=== Setup Complete ==="
```

---

## Troubleshooting

**Error: `ResourceNotFoundException`**
```bash
# Verify secret name (case-sensitive)
aws secretsmanager list-secrets --query 'SecretList[].Name'
```

**Error: `AccessDeniedException`**
```bash
# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns "$SECRET_ARN"
```

**Rotation Lambda fails:**
```bash
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/SecretsManager
aws logs filter-log-events \
  --log-group-name /aws/lambda/SecretsManagerRDSPostgreSQLRotation \
  --filter-pattern "ERROR"
```

**VPC: Lambda can't reach Secrets Manager:**
```bash
# Create VPC endpoint for Secrets Manager
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxx \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --vpc-endpoint-type Interface
```

---

## Expected Outcome

After completing this guide:
- ✅ Secret `prod/myapp/rds-credentials` stored encrypted with CMK
- ✅ Automatic rotation every 30 days via Lambda
- ✅ Application retrieves credentials at runtime — zero hardcoded passwords
- ✅ IAM resource policy limits access to specific role
- ✅ CloudTrail auditing all `GetSecretValue` calls
- ✅ boto3 integration with optional credential caching

---

## Cleanup

```bash
# WARNING: --force-delete-without-recovery skips the 30-day recovery window
aws secretsmanager delete-secret \
  --secret-id "$SECRET_NAME" \
  --force-delete-without-recovery

# Standard deletion (7-30 day recovery window)
aws secretsmanager delete-secret \
  --secret-id "$SECRET_NAME" \
  --recovery-window-in-days 7

# Delete KMS key (schedule deletion — minimum 7 days)
aws kms schedule-key-deletion \
  --key-id alias/secrets-manager-rds \
  --pending-window-in-days 7

# Delete rotation Lambda (if created manually)
aws lambda delete-function \
  --function-name SecretsManagerRDSPostgreSQLRotation

echo "Cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
