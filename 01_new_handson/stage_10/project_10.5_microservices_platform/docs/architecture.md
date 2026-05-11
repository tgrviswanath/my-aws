# Architecture — Project 10.5 Production-grade Microservices Platform

## Full System Diagram

```
                        Internet
                           │
                    ┌──────▼──────┐
                    │  CloudFront  │  CDN + WAF + HTTPS
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ API Gateway  │  Auth (Cognito JWT)
                    │             │  Rate limiting
                    │             │  Request routing
                    └──┬──────┬───┘
                       │      │
          ┌────────────┘      └────────────┐
          │                                │
   ┌──────▼──────┐                  ┌──────▼──────┐
   │Order Service│                  │ User Service │
   │ ECS Fargate │                  │ ECS Fargate  │
   │             │                  │             │
   │ RDS MySQL   │                  │ RDS MySQL   │
   │ Redis Cache │                  │             │
   └──────┬──────┘                  └─────────────┘
          │ Events
   ┌──────▼──────────────────────────────────────┐
   │              Kinesis Data Streams            │
   │              (order-events stream)           │
   └──────┬──────────────────────────────────────┘
          │
   ┌──────▼──────┐
   │  Analytics  │
   │  Service    │
   │  (EKS)      │
   │             │
   │ Glue ETL    │
   │ Redshift    │
   └─────────────┘

Observability Layer (all services):
  CloudWatch Logs → OpenSearch → Kibana
  X-Ray distributed tracing
  Prometheus → Grafana dashboards
  CloudTrail audit logs → Athena queries

Security Layer:
  WAF (SQL injection, XSS, rate limiting)
  GuardDuty (threat detection)
  Secrets Manager (all credentials)
  VPC (private subnets for all services)
  Security groups (per-service micro-segmentation)

CI/CD:
  GitHub → GitHub Actions (OIDC) → ECR → ECS/EKS
```

## Service Communication Patterns

```
Synchronous (REST):
  API Gateway → Order Service → User Service
  (for real-time user-facing requests)

Asynchronous (Events):
  Order Service → Kinesis → Analytics Service
  (for non-blocking, decoupled processing)

Cache:
  Order Service → Redis → RDS
  (cache-aside pattern, 60s TTL)
```

## Data Flow

```
User places order
  → API Gateway validates JWT
  → Order Service creates order in RDS
  → Order Service publishes to Kinesis
  → Analytics Lambda processes event
  → Glue ETL runs nightly batch
  → Redshift loads processed data
  → Grafana dashboard shows metrics
```

## Deployment Pipeline

```
Developer pushes code
  → GitHub Actions CI (lint, test, build, scan)
  → Docker image pushed to ECR (tagged with git SHA)
  → ECS/EKS rolling deployment
  → Smoke tests verify deployment
  → Grafana shows metrics stabilize
  → CloudTrail records all changes
```
