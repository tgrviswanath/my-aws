# Project 8.1 — Secrets Manager + Parameter Store Integration

## What This Does
Replaces all hardcoded credentials and config values with AWS Secrets Manager (for secrets) and SSM Parameter Store (for non-secret config). Applications retrieve secrets at runtime — no secrets in code or environment variables.

## What Goes Where
| Type | Service | Example |
|------|---------|---------|
| Database passwords | Secrets Manager | RDS master password |
| API keys | Secrets Manager | Third-party API keys |
| TLS certificates | Secrets Manager | Private keys |
| App config (non-secret) | SSM Parameter Store | DB hostname, port |
| Feature flags | SSM Parameter Store | `enable_feature_x=true` |
| Shared config | SSM Parameter Store | `/app/prod/db_host` |

## Key Features Covered
- Automatic secret rotation (RDS passwords)
- Secret versioning and rollback
- Cross-account secret sharing
- ECS task integration (inject secrets as env vars)
- Lambda integration (retrieve at cold start)
- SSM Parameter Store hierarchy (`/project/env/key`)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- Never put secrets in environment variables in task definitions — use `secrets` field instead
- Secrets Manager auto-rotation: Lambda rotates the secret and updates the DB password
- SSM Parameter Store: free for standard parameters; $0.05/month for advanced (> 4KB)
- Use `SecureString` type in SSM for sensitive values — encrypted with KMS
- Cache secrets in Lambda: retrieve once per cold start, not per invocation
- Least privilege: grant `secretsmanager:GetSecretValue` only for specific secret ARNs
