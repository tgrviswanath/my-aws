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
