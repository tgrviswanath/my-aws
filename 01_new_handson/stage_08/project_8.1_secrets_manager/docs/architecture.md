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

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
