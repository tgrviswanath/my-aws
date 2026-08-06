# Verification & Validation — Project 8.1 Secrets Manager + Parameter Store

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Secret | Secrets Manager → Secrets | `handson/db/credentials` listed |
| Secret rotation | Secrets Manager → Secret → Rotation tab | Rotation enabled, Lambda ARN shown |
| SSM Parameters | Systems Manager → Parameter Store | `/handson/prod/db_host`, `/handson/prod/db_port` listed |
| SSM SecureString | Parameter Store → parameter → Type | Type = **SecureString** for sensitive params |
| ECS Task Definition | ECS → Task Definitions | `secrets` field references Secrets Manager ARN (not env vars) |
| IAM Role | IAM → Roles → ECS task role | `secretsmanager:GetSecretValue` policy attached |
| KMS Key | KMS → Customer managed keys | Key used for SecureString encryption |

📸 Screenshot: Secrets Manager showing `handson/db/credentials` with rotation enabled  
📸 Screenshot: SSM Parameter Store hierarchy `/handson/prod/`  
📸 Screenshot: ECS task definition using `secrets` field (not environment variables)

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm secret exists
aws secretsmanager describe-secret \
  --secret-id handson/db/credentials \
  --query "{Name:Name,ARN:ARN,RotationEnabled:RotationEnabled,LastRotated:LastRotatedDate}"
# Expected: RotationEnabled=true (if rotation configured)

# 2.2 Retrieve secret value (confirms access)
aws secretsmanager get-secret-value \
  --secret-id handson/db/credentials \
  --query "SecretString" --output text | python3 -m json.tool
# Expected: {"username": "admin", "password": "..."}

# 2.3 List all secrets with handson prefix
aws secretsmanager list-secrets \
  --filters Key=name,Values=handson \
  --query "SecretList[*].{Name:Name,ARN:ARN}"
# Expected: handson/db/credentials listed

# 2.4 Confirm SSM parameters exist
aws ssm get-parameters-by-path \
  --path /handson/prod \
  --with-decryption \
  --query "Parameters[*].{Name:Name,Type:Type,Value:Value}"
# Expected: db_host, db_port, feature flags listed

# 2.5 Get a specific SSM parameter
aws ssm get-parameter \
  --name /handson/prod/db_host \
  --query "Parameter.{Name:Name,Type:Type,Value:Value}"
# Expected: Type=String, Value=hostname

# 2.6 Confirm ECS task role has secrets access
TASK_ROLE=$(aws ecs describe-task-definition \
  --task-definition handson-flask-api \
  --query "taskDefinition.taskRoleArn" --output text)
aws iam simulate-principal-policy \
  --policy-source-arn $TASK_ROLE \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns $(aws secretsmanager describe-secret \
    --secret-id handson/db/credentials \
    --query "ARN" --output text) \
  --query "EvaluationResults[0].EvalDecision"
# Expected: "allowed"

# 2.7 Run secrets client
python src/secrets_client.py
# Expected: prints retrieved credentials (masked password)
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_secretsmanager_secret.db_credentials
# aws_secretsmanager_secret_version.db_credentials
# aws_ssm_parameter.db_host
# aws_ssm_parameter.db_port
# aws_iam_role_policy.secrets_access
# aws_kms_key.secrets (if custom KMS key)

# 3.2 Inspect secret
terraform state show aws_secretsmanager_secret.db_credentials
# Shows: name, rotation_enabled, kms_key_id

# 3.3 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Secret Retrieval

```bash
# Verify secret retrieval works from Python
python3 -c "
import boto3, json
client = boto3.client('secretsmanager', region_name='us-east-1')
resp = client.get_secret_value(SecretId='handson/db/credentials')
secret = json.loads(resp['SecretString'])
print('username:', secret['username'])
print('password: ***MASKED***')
print('✅ Secret retrieved successfully')
"
# Expected: username printed, no exception

# Verify SSM parameter retrieval
python3 -c "
import boto3
ssm = boto3.client('ssm', region_name='us-east-1')
resp = ssm.get_parameter(Name='/handson/prod/db_host', WithDecryption=True)
print('db_host:', resp['Parameter']['Value'])
print('✅ SSM parameter retrieved successfully')
"
# Expected: hostname printed
```

---

## 5. Expected Successful Outputs

**CLI — get-secret-value:**
```json
{ "username": "admin", "password": "Sup3rS3cr3t!" }
```

**CLI — get-parameters-by-path:**
```json
[
  { "Name": "/handson/prod/db_host", "Type": "String",       "Value": "mydb.abc123.us-east-1.rds.amazonaws.com" },
  { "Name": "/handson/prod/db_port", "Type": "String",       "Value": "3306" },
  { "Name": "/handson/prod/api_key", "Type": "SecureString", "Value": "sk-abc123..." }
]
```

**terraform output:**
```
secret_arn       = "arn:aws:secretsmanager:us-east-1:123456789012:secret:handson/db/credentials-abc123"
parameter_prefix = "/handson/prod"
```

---

## 6. Verification Checklist

- [ ] Secret `handson/db/credentials` exists in Secrets Manager
- [ ] Secret value is valid JSON with `username` and `password` keys
- [ ] SSM parameters exist under `/handson/prod/` hierarchy
- [ ] Sensitive SSM params use `SecureString` type (KMS encrypted)
- [ ] ECS task definition uses `secrets` field (not `environment` for credentials)
- [ ] ECS task role allows `secretsmanager:GetSecretValue` on specific ARN
- [ ] Python `get_secret_value` call succeeds without exception
- [ ] Python SSM `get_parameter` call succeeds
- [ ] No hardcoded credentials in any code or environment variables
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
