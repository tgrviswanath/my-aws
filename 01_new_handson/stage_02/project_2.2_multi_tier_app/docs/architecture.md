# Architecture — Project 2.2 Multi-Tier Web Application

## Diagram

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         AWS Region: us-east-1                         │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    VPC: 10.0.0.0/16                               │ │
│  │                                                                    │ │
│  │  PUBLIC SUBNETS (10.0.1.0/24, 10.0.2.0/24)                       │ │
│  │  ┌────────────────────────────────────────────────────────────┐   │ │
│  │  │              Application Load Balancer (ALB)               │   │ │
│  │  │  alb-sg: inbound 80/443 from 0.0.0.0/0                    │   │ │
│  │  └──────────────────────────┬─────────────────────────────────┘   │ │
│  │                             │ HTTP:80 (from alb-sg only)           │ │
│  │  PRIVATE APP SUBNETS (10.0.3.0/24, 10.0.4.0/24)                  │ │
│  │  ┌────────────────────────────────────────────────────────────┐   │ │
│  │  │           Auto Scaling Group (EC2 t3.micro)                │   │ │
│  │  │  app-sg: inbound 80 from alb-sg only                       │   │ │
│  │  │                                                             │   │ │
│  │  │  ┌──────────────┐    ┌──────────────┐                      │   │ │
│  │  │  │ app-server-1 │    │ app-server-2 │  (desired: 2)        │   │ │
│  │  │  │ AZ: 1a       │    │ AZ: 1b       │  (max: 4)            │   │ │
│  │  │  └──────────────┘    └──────────────┘                      │   │ │
│  │  └──────────────────────────┬─────────────────────────────────┘   │ │
│  │                             │ MySQL:3306 (from app-sg only)        │ │
│  │  PRIVATE DB SUBNETS (10.0.5.0/24, 10.0.6.0/24)                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐   │ │
│  │  │                  RDS MySQL (Multi-AZ)                      │   │ │
│  │  │  rds-sg: inbound 3306 from app-sg only                     │   │ │
│  │  └────────────────────────────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────── ┘
```

## Security Group Chain

```
Internet → [alb-sg] → ALB → [app-sg] → EC2 → [rds-sg] → RDS

Each tier only accepts traffic from the tier directly above it.
RDS is completely unreachable from the internet.
```

## High Availability

| Component | HA Strategy |
|-----------|-------------|
| ALB | Spans 2 AZs automatically |
| EC2 | ASG distributes across 2 private subnets |
| RDS | Multi-AZ standby (optional for learning) |
| Subnets | 2 per tier across 2 AZs |
