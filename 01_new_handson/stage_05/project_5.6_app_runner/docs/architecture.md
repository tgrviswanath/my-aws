# Architecture — Project 5.6 AWS App Runner Deployment

## Diagram

```
Internet
    │ HTTPS (automatic — no ACM needed)
    ▼
┌──────────────────────────────────────────────────────┐
│              AWS App Runner                           │
│                                                        │
│  Service: handson-app-runner                          │
│  ├── Auto-scales: 0 → N instances on demand          │
│  ├── Built-in load balancer                           │
│  ├── Built-in health checks (/health)                 │
│  ├── Auto-deploy: watches ECR for new images          │
│  └── HTTPS endpoint: https://xxxxx.awsapprunner.com  │
│                                                        │
│  Source: ECR image                                    │
│  CPU: 0.25 vCPU | Memory: 0.5 GB                     │
└──────────────────────────────────────────────────────┘
    │
    │ Pulls image on deploy
    ▼
ECR: handson-flask-api:latest
```

## App Runner vs ECS Fargate

```
App Runner:
  ✅ Zero config — just point at ECR image
  ✅ HTTPS automatic
  ✅ Auto-deploy on ECR push
  ✅ Scales to zero when idle
  ❌ No VPC by default (optional)
  ❌ More expensive per compute unit
  ❌ Less control over networking

ECS Fargate:
  ✅ Full VPC control
  ✅ Cheaper at scale
  ✅ Fine-grained networking
  ❌ Requires ALB, target groups, listeners
  ❌ More setup required
  ❌ No auto-deploy (need CI/CD pipeline)

Use App Runner for: prototypes, small teams, simple APIs
Use ECS Fargate for: production microservices, complex networking
```

## Auto-deployment Flow

```
Developer pushes new image to ECR
    │
    │ App Runner polls ECR every few minutes
    ▼
App Runner detects new image tag
    │
    ▼
App Runner starts new instances with new image
    │
    ▼
Health check passes
    │
    ▼
Traffic shifts to new instances
Old instances terminated
```
