# Architecture — Project 5.5 Blue-Green Deployment

## Traffic Flow

```
                    ALB Listener :80
                          │
                    ┌─────┴──────┐
                    │            │
              Production     Test Port
              Port :80        :8080
                    │
                    ▼
         ┌──────────────────────┐
         │   CodeDeploy manages │
         │   traffic switching  │
         └──────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
  Target Group: Blue    Target Group: Green
  ECS Tasks v1          ECS Tasks v2
  (current)             (new)

Before deploy:  100% → Blue
During deploy:  100% → Blue (green warming up)
After switch:   100% → Green
Rollback:       100% → Blue (instant)
```

## Deployment Lifecycle Hooks

```
appspec.yml hooks:
  BeforeInstall    → run pre-deployment checks
  AfterInstall     → run smoke tests on green
  AfterAllowTestTraffic → validate on test port :8080
  BeforeAllowTraffic    → final validation
  AfterAllowTraffic     → post-deployment tasks
```

## Canary vs Linear vs All-at-Once

```
ECSCanary10Percent5Minutes:
  0 min: 10% → green, 90% → blue
  5 min: 100% → green (if healthy)

ECSLinear10PercentEvery1Minutes:
  0 min: 10% → green
  1 min: 20% → green
  ...
  10 min: 100% → green

ECSAllAtOnce:
  Instant: 100% → green
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
