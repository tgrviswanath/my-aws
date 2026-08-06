# Architecture — Project 2.3 ALB vs NLB Comparison

## Side-by-Side Diagram

```
                    Internet
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
  ┌───────────────┐         ┌───────────────┐
  │  ALB (Layer 7)│         │  NLB (Layer 4)│
  │  compare-alb  │         │  compare-nlb  │
  │               │         │  Static EIP   │
  │  Path routing:│         │               │
  │  /     → web  │         │  TCP:80 → all │
  │  /api/ → api  │         │               │
  └───────┬───────┘         └───────┬───────┘
          │                         │
    ┌─────┴─────┐             ┌─────┴─────┐
    ▼           ▼             ▼           ▼
  tg-web     tg-api         tg-nlb     tg-nlb
  EC2 #1     EC2 #2         EC2 #1     EC2 #2
```

## Decision Guide

```
Need HTTP routing by path/host/header?  → ALB
Need WebSocket support?                 → ALB or NLB
Need static IP for firewall whitelisting? → NLB
Need ultra-low latency (<1ms)?          → NLB
Need to preserve client source IP?      → NLB
Building a REST API or web app?         → ALB (99% of cases)
Building a game server or VoIP?         → NLB
```

## ALB Path Routing Rules

```
Listener: HTTP:80
  Rule 1 (priority 10): path = /api/*  → forward to tg-api
  Rule 2 (default):     all other      → forward to tg-web
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
