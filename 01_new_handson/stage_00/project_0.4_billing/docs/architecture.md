# Architecture — Project 0.4 AWS Cost & Billing Fundamentals

## Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        AWS Account                            │
│                                                               │
│  ┌─────────────────────┐    ┌──────────────────────────────┐ │
│  │   CloudWatch         │    │        AWS Budgets           │ │
│  │   Billing Alarm      │    │   $20/month limit            │ │
│  │   Threshold: $10     │    │   Alert: 50% / 80% / 100%   │ │
│  │   Region: us-east-1  │    │   Type: ACTUAL + FORECASTED  │ │
│  └──────────┬──────────┘    └──────────────┬───────────────┘ │
│             │                               │                  │
│             └───────────────┬───────────────┘                  │
│                             ▼                                   │
│                    ┌─────────────────┐                         │
│                    │   SNS Topic     │                         │
│                    │ billing-alerts  │                         │
│                    └────────┬────────┘                         │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────── ┘
                              ▼
                    📧 your@email.com
                    (confirmed subscription)
```

## Alert Flow

```
AWS spends money
      │
      ├── CloudWatch checks EstimatedCharges daily
      │         └── > $10 → SNS → Email
      │
      └── AWS Budgets checks monthly spend
                ├── > 50% of $20 → Email
                ├── > 80% of $20 → Email
                └── Forecasted > 100% of $20 → Email
```

## Important Notes

| Topic | Detail |
|-------|--------|
| Billing region | Always `us-east-1` for billing metrics |
| Alarm check frequency | Once per day (period = 86400s) |
| Budget reset | Resets on the 1st of each month |
| Free budgets | First 2 budgets are free |

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
