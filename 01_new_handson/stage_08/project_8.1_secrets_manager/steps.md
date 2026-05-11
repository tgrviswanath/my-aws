# Steps — Project 8.1 Secrets Manager + Parameter Store

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="db_password=MySecurePass@123" \
  -var="api_key=sk-test-abc123xyz"

terraform output
```

---

## Phase 2 — Retrieve Secrets via CLI

```bash
# Get DB credentials
aws secretsmanager get-secret-value \
  --secret-id /handson/prod/db-credentials \
  --query SecretString --output text | python3 -m json.tool

# Get SSM parameters by path
aws ssm get-parameters-by-path \
  --path /handson/prod/ \
  --with-decryption \
  --query "Parameters[*].{Name:Name,Value:Value}" \
  --output table

# Get single parameter
aws ssm get-parameter \
  --name /handson/prod/db_host \
  --query "Parameter.Value" --output text
```

---

## Phase 3 — Inject Secrets into ECS Task (No Env Vars)

```json
// In ECS task definition — use "secrets" not "environment"
{
  "containerDefinitions": [{
    "name": "flask-api",
    "secrets": [
      {
        "name": "DB_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:/handson/prod/db-credentials:password::"
      }
    ],
    "environment": [
      {"name": "DB_HOST", "valueFrom": "/handson/prod/db_host"}
    ]
  }]
}
```

---

## Phase 4 — Test Secret Rotation

```bash
# Rotate the DB secret manually
aws secretsmanager rotate-secret \
  --secret-id /handson/prod/db-credentials \
  --rotation-rules AutomaticallyAfterDays=30

# Check rotation status
aws secretsmanager describe-secret \
  --secret-id /handson/prod/db-credentials \
  --query "{RotationEnabled:RotationEnabled,LastRotatedDate:LastRotatedDate}"
```

---

## Phase 5 — Test Python Client

```bash
# Set up environment
pip install boto3

# Run the secrets client
python3 src/secrets_client.py

# Or test interactively
python3 << 'EOF'
from src.secrets_client import get_secret, get_parameter

# Get DB credentials
creds = get_secret("/handson/prod/db-credentials")
print("DB host:", creds["host"])
print("DB user:", creds["username"])
# Password is retrieved but not printed

# Get SSM parameter
host = get_parameter("/handson/prod/db_host")
print("DB host from SSM:", host)
EOF
```

---

## Screenshots to Take
- [ ] Secrets Manager console showing secrets
- [ ] Secret value retrieved (password masked)
- [ ] SSM Parameter Store hierarchy
- [ ] ECS task definition using `secrets` field (not env vars)
- [ ] KMS key used for encryption
- [ ] IAM policy with least-privilege secret access
