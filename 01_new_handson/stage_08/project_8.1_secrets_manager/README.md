# Project 8.1 — AWS Secrets Manager

**Stage:** 08 | **Level:** Intermediate | **Est. Time:** 60 min | **Cost:** ~$0.40/secret/month

Store RDS MySQL credentials securely in AWS Secrets Manager, retrieve them from a Python Lambda using
boto3 without any hardcoded values, and enable 30-day automatic rotation so both Secrets Manager and
the RDS instance stay in sync. The project also compares Secrets Manager against SSM Parameter Store
SecureString to clarify when each service is the right tool.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS Secrets Manager | Store and rotate DB credentials (host, user, password) | $0.40/secret/month |
| AWS Lambda | Retrieve secret via GetSecretValue; rotation function | $0.20/1M requests |
| Amazon RDS MySQL | Target database whose password is rotated | Instance cost varies |
| AWS IAM | Grant Lambda permission to call secretsmanager:GetSecretValue | Free |
| Amazon VPC | Lambda rotator runs inside same VPC as RDS | Free |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| DB host | rds-mysql-endpoint.us-east-1.rds.amazonaws.com | RDS endpoint |
| DB username | app_user | MySQL user to rotate |
| DB password | InitialPassword123! | Stored as SecretString JSON |
| Rotation interval | 30 days | Lambda rotator schedule |
| Secret name | prod/myapp/db-credentials | Path-style naming convention |

### Output

| Artifact | Description |
|---|---|
| Secret ARN | arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/myapp/db-credentials |
| Lambda function | retrieve_db_secret — calls GetSecretValue, parses JSON |
| Rotation Lambda | SecretsManagerRDSMySQLRotationSingleUser (AWS-managed) |
| Rotation schedule | Every 30 days, password updated in RDS and Secrets Manager atomically |
| No hardcoded creds | Lambda reads secret at runtime; zero credentials in source code |

---

## Architecture

```
Developer / App
      |
      v
 Lambda Function
 (retrieve_db_secret)
      |
      | GetSecretValue API
      v
+-------------------+
| Secrets Manager   |  <---- rotation trigger (every 30 days)
| prod/myapp/db-    |              |
| credentials       |              v
+-------------------+    Rotation Lambda
      |                  (update MySQL password
      | SecretString      then update secret)
      | {host, user, pw}        |
      v                         v
 boto3 parses JSON         RDS MySQL
 -> connects to RDS    (password changed atomically)
```

---

## Quick Start

```cmd
REM 1. Create the secret with DB credentials as JSON
aws secretsmanager create-secret ^
  --name prod/myapp/db-credentials ^
  --description "RDS MySQL credentials for myapp" ^
  --secret-string "{\"host\":\"rds-endpoint.us-east-1.rds.amazonaws.com\",\"username\":\"app_user\",\"password\":\"InitialPassword123!\",\"dbname\":\"myappdb\"}"

REM 2. Retrieve and verify the secret value
aws secretsmanager get-secret-value ^
  --secret-id prod/myapp/db-credentials ^
  --query SecretString ^
  --output text

REM 3. Enable automatic rotation (30-day interval, single-user strategy)
aws secretsmanager rotate-secret ^
  --secret-id prod/myapp/db-credentials ^
  --rotation-rules AutomaticallyAfterDays=30

REM 4. Describe the secret to confirm rotation is enabled
aws secretsmanager describe-secret ^
  --secret-id prod/myapp/db-credentials ^
  --query "{ARN:ARN,RotationEnabled:RotationEnabled,NextRotationDate:NextRotationDate}"

REM 5. Deploy retrieval Lambda (assumes zip already built)
aws lambda create-function ^
  --function-name retrieve_db_secret ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/lambda-secrets-role ^
  --handler lambda_function.lambda_handler ^
  --zip-file fileb://retrieve_db_secret.zip

REM 6. Test the Lambda
aws lambda invoke ^
  --function-name retrieve_db_secret ^
  --payload "{}" ^
  response.json && type response.json
```

---

## Data Flow

1. Lambda function starts — no credentials in environment variables or source code.
2. Lambda calls `secretsmanager.get_secret_value(SecretId='prod/myapp/db-credentials')`.
3. Secrets Manager authenticates the Lambda's IAM role and returns the `SecretString` JSON payload.
4. Python `json.loads()` extracts `host`, `username`, `password`, `dbname` fields.
5. Lambda opens a MySQL connection using those values, executes the query, and returns results.
6. Every 30 days the rotation Lambda fires: generates a new password, updates RDS MySQL, then updates the secret in Secrets Manager — both changes are atomic.
7. On the next Lambda invocation, `GetSecretValue` returns the new password automatically.

---

## Project Files

| File | Description |
|---|---|
| `lambda_function.py` | Python Lambda — retrieves secret, connects to RDS, runs sample query |
| `rotation_test.py` | Script to manually trigger rotation and verify new password works |
| `iam_policy.json` | IAM policy granting Lambda secretsmanager:GetSecretValue on the specific ARN |
| `create_secret.sh` | Shell script wrapping the create-secret CLI call with JSON payload |
| `compare_ssm.md` | Side-by-side comparison: Secrets Manager vs SSM Parameter Store SecureString |

---

## Lessons Learned

- Never hardcode credentials — `SecretString` stores a JSON object; `SecretBinary` stores base64-encoded binary blobs like TLS certificates.
- Automatic rotation updates the password in both Secrets Manager and RDS MySQL simultaneously using a four-step Lambda lifecycle: `createSecret`, `setSecret`, `testSecret`, `finishSecret`.
- `GetSecretValue` API calls cost $0.05 per 10,000 calls — cache the secret in Lambda memory for the function lifetime to avoid per-invocation charges.
- The rotation Lambda needs network access to RDS: place it in the same VPC/subnet as the RDS instance, or use a Secrets Manager VPC endpoint so rotation traffic stays within the AWS network.
- SSM Parameter Store `SecureString` is free up to 10,000 parameters and suits static credentials; use Secrets Manager specifically when automated rotation is required.
- Secret versioning is automatic — Secrets Manager keeps `AWSCURRENT` and `AWSPREVIOUS` stages so a rollback is a single API call.
- IAM resource-level policies on Secrets Manager ARNs enforce least-privilege: a Lambda role can be restricted to a single secret rather than all secrets in the account.
