# Architecture — Project 5.4 ECS Fargate Deployment

## Diagram

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AWS Region: us-east-1                          │
│                                                                    │
│  PUBLIC SUBNETS                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  ALB: handson-flask-api-alb               │    │
│  │  alb-sg: 80/443 from 0.0.0.0/0                           │    │
│  └──────────────────────────┬─────────────────────────────── ┘   │
│                             │ :5000 (from alb-sg only)            │
│  PRIVATE SUBNETS                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              ECS Cluster: handson-cluster                 │    │
│  │                                                            │    │
│  │  ┌─────────────────────┐  ┌─────────────────────────┐   │    │
│  │  │  Fargate Task #1    │  │  Fargate Task #2         │   │    │
│  │  │  flask-api:latest   │  │  flask-api:latest        │   │    │
│  │  │  0.25 vCPU / 512MB  │  │  0.25 vCPU / 512MB      │   │    │
│  │  │  Private IP: 10.x.x │  │  Private IP: 10.x.x     │   │    │
│  │  └─────────────────────┘  └─────────────────────────┘   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ECR: handson-flask-api ← tasks pull image on startup             │
│  CloudWatch: /ecs/handson-flask-api ← container logs              │
└────────────────────────────────────────────────────────────────────┘
```

## IAM Role Separation

```
Task Execution Role (ECS infrastructure):
  - ecr:GetAuthorizationToken
  - ecr:BatchGetImage
  - logs:CreateLogStream
  - logs:PutLogEvents

Task Role (application code):
  - Whatever your app needs (S3, DynamoDB, etc.)
  - Empty by default — add permissions as needed
```

## Rolling Deployment

```
Before deploy: 2 tasks running (v1)

Deploy starts:
  Step 1: Launch 1 new task (v2) → 3 tasks total
  Step 2: Wait for new task to pass health check
  Step 3: Drain and stop 1 old task (v1) → 2 tasks (1 v1, 1 v2)
  Step 4: Launch 1 more new task (v2) → 3 tasks
  Step 5: Stop last old task → 2 tasks (both v2)

Zero downtime throughout — ALB always has healthy targets
```
