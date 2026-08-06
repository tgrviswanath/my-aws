# Project 10.5 — Production-grade Microservices Platform

## What This Does
Combines everything from the roadmap into a production-grade microservices platform. This is the capstone project — it integrates EKS/ECS, API Gateway, Kinesis, Redis, RDS, observability, and security into a cohesive system.

## Architecture
```
Internet
  → CloudFront (CDN + WAF)
    → API Gateway (routing, auth, rate limiting)
      ├── Order Service (ECS Fargate)
      │     ├── RDS MySQL (orders DB)
      │     └── ElastiCache Redis (cache)
      ├── User Service (ECS Fargate)
      │     └── RDS MySQL (users DB)
      └── Analytics Service (EKS)
            ├── Kinesis (event stream)
            ├── Glue ETL (batch processing)
            └── Redshift (analytics queries)

Observability:
  CloudWatch + X-Ray + Grafana + Prometheus

Security:
  WAF + GuardDuty + Secrets Manager + CloudTrail

CI/CD:
  GitHub Actions + OIDC + ECR + ECS/EKS deploy
```

## Services Used (All from Previous Projects)
| Service | Project |
|---------|---------|
| ECS Fargate | 5.4 |
| EKS | 6.5, 10.4 |
| API Gateway | 4.1, 4.2 |
| Kinesis | 9.3 |
| Glue ETL | 9.2 |
| Redshift | 9.9 |
| ElastiCache | 5.7 |
| RDS | 1.4 |
| WAF | 8.2 |
| GuardDuty | 8.4 |
| Secrets Manager | 8.1 |
| CloudTrail | 8.5 |
| X-Ray | 7.3 |
| Grafana | 7.5 |
| GitHub Actions | 6.1 |

## How to Deploy
This project assembles all previous Terraform modules. See `terraform/main.tf` for the full composition.

```bash
cd terraform
terraform init
terraform apply -var-file="production.tfvars"
```

## Lessons Learned
- Start simple, add complexity gradually — don't build this on day 1
- Each service should own its data — no shared databases between microservices
- Async communication (Kinesis/SQS) decouples services — failures don't cascade
- Observability is not optional — you can't fix what you can't see
- Security is built-in, not bolted on — WAF, encryption, least privilege from day 1
- Cost awareness at every layer — tag everything, set budgets, review monthly

## Code

### `code/platform_health.py` — Check health of all platform services

```bash
pip install boto3

# Run full platform health check
python code/platform_health.py

# Use a specific region
python code/platform_health.py --region us-east-1

# Use a specific profile
python code/platform_health.py --profile prod
```

Services checked:
| Service | Check |
|---------|-------|
| ECS services | `desiredCount == runningCount` for all services |
| RDS instances | All instances in `available` state |
| ElastiCache | All clusters in `available` state |
| API Gateway | Recent 5xx error rate < 1% |
| Kinesis streams | No shard iterator age > 5 minutes |

Prints a platform health dashboard with overall status: `ALL SYSTEMS HEALTHY` or `DEGRADED`.

---

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription with required permissions | IAM user or role |
| Configuration | Resource settings | Region, names, sizes |
| Source Data | Files or code to deploy | Application source, data files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed and running services | AWS Console / CLI |
| Endpoints | Service URLs and connection strings | Resource overview page |
| Logs | Execution and audit logs | CloudWatch Logs |

## Quick Start
`ash
# Configure AWS CLI
aws configure

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Create resource group
aws ec2 describe-regions --output table
`

## Lessons Learned
- Always tag AWS resources for cost tracking and organization
- Use IAM roles instead of access keys wherever possible
- Delete resources after learning to avoid unexpected charges
- Enable CloudWatch logging for all services in production
- Use the free tier for all lab exercises to minimize cost
