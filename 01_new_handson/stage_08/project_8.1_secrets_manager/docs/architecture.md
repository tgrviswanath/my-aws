# Architecture — Project 8.1 Secrets Manager + Parameter Store

## Secret Retrieval at Runtime

```
ECS Task starts
    │
    │ Task Execution Role has secretsmanager:GetSecretValue
    ▼
ECS Agent retrieves secrets BEFORE container starts
    │ Injects as environment variables (encrypted in transit)
    ▼
Container starts with DB_PASSWORD already set
    │ App reads os.environ["DB_PASSWORD"]
    ▼
App connects to database

No secrets ever stored in:
  ❌ Dockerfile
  ❌ docker-compose.yml
  ❌ ECS task definition environment block
  ❌ Git repository
```

## Secrets Manager vs SSM Parameter Store

| Feature | Secrets Manager | SSM Parameter Store |
|---------|----------------|---------------------|
| Cost | $0.40/secret/month | Free (standard) |
| Auto-rotation | ✅ Built-in Lambda | ❌ Manual |
| Max size | 65 KB | 4 KB (standard) |
| Use for | Passwords, API keys | Config, feature flags |

## SSM Parameter Hierarchy

```
/handson/
  prod/
    db_host          → String (plaintext)
    db_port          → String (plaintext)
    redis_host       → String (plaintext)
    feature_new_ui   → String (true/false)
  dev/
    db_host          → String (different value)
    ...

Access all prod config at once:
  aws ssm get-parameters-by-path --path /handson/prod/ --with-decryption
```
