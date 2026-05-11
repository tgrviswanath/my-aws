# Architecture — Project 8.1 Secrets Manager + Parameter Store

## Secret Retrieval Flow

```
ECS Task starts
    │
    │ Task Execution Role has secretsmanager:GetSecretValue
    ▼
ECS Agent retrieves secrets BEFORE container starts
    │
    │ Injects as environment variables (encrypted in transit)
    ▼
Container starts with DB_PASSWORD already set
    │
    │ App reads os.environ["DB_PASSWORD"]
    ▼
App connects to database
```

## Secrets Manager vs SSM Parameter Store

| Feature | Secrets Manager | SSM Parameter Store |
|---------|----------------|---------------------|
| Cost | $0.40/secret/month | Free (standard) |
| Auto-rotation | ✅ Built-in | ❌ Manual |
| Max size | 65 KB | 4 KB (standard) |
| Cross-account | ✅ Yes | ✅ Yes |
| Use for | Passwords, API keys, certs | Config, feature flags |

## SSM Parameter Hierarchy

```
/handson/
  prod/
    db_host          → String
    db_port          → String
    redis_host       → String
    feature_new_ui   → String (true/false)
    db-credentials   → SecureString (encrypted)
  dev/
    db_host          → String (different value)
    ...
```
