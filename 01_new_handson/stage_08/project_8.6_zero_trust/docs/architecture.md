# Architecture — Project 8.6 Zero Trust Security Lab

## Zero Trust Principles Applied

```
Traditional perimeter security:
  "Trust everything inside the network"
  VPN → inside = trusted

Zero Trust:
  "Never trust, always verify"
  Every request authenticated + authorized regardless of location
```

## AWS Zero Trust Controls

```
Identity Layer:
  IAM Identity Center (SSO) → centralized identity
  MFA enforced for all users
  Short-lived credentials (STS, OIDC)

Network Layer:
  Per-service security groups (micro-segmentation)
  VPC Flow Logs (ALL traffic logged)
  No SSH from internet (use SSM Session Manager)
  Private subnets for all services

Application Layer:
  Cognito JWT on every API call
  API Gateway authorizer validates every request
  No implicit trust between services

Data Layer:
  Encryption at rest (KMS)
  Encryption in transit (TLS 1.2+)
  Secrets Manager (no hardcoded credentials)

Monitoring Layer:
  CloudTrail (every API call logged)
  GuardDuty (threat detection)
  VPC Flow Logs (network visibility)
  Security Hub (aggregated findings)
```

## Micro-segmentation vs Traditional

```
Traditional (bad):
  "Private subnet" → all services can talk to each other
  DB accessible from any EC2 in private subnet

Zero Trust (good):
  api-service-sg → only accepts from alb-sg
  db-service-sg  → only accepts from api-service-sg
  redis-sg       → only accepts from api-service-sg
  Each service isolated — breach doesn't spread
```
