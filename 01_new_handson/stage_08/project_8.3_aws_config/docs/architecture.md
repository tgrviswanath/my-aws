# Architecture — Project 8.3 AWS Config Compliance Automation

## How Config Works

```
Resource created/modified (EC2, S3, RDS, etc.)
    │
    │ Config records configuration change
    ▼
Config Configuration Recorder
    │
    ├── Stores snapshot in S3 bucket
    └── Evaluates against Config Rules
          │
          ├── COMPLIANT   → no action
          └── NON_COMPLIANT → EventBridge event
                                │
                                ▼
                          SNS → Email alert
```

## Rules Evaluation

```
Config Rule: s3-bucket-server-side-encryption-enabled

Trigger: Configuration change (S3 bucket created/modified)

Evaluation:
  Check: does bucket have SSE enabled?
  YES → COMPLIANT
  NO  → NON_COMPLIANT → alert

Config Rule: required-tags

Trigger: Configuration change + periodic (every 24h)

Evaluation:
  Check: does resource have Project, Environment, ManagedBy tags?
  YES → COMPLIANT
  NO  → NON_COMPLIANT → alert
```

## Compliance Dashboard

```
AWS Config Dashboard
    ├── Overall compliance: 85% (17/20 rules passing)
    ├── Non-compliant resources: 3
    │   ├── S3 bucket: my-old-bucket (no encryption)
    │   ├── EC2 instance: i-xxx (missing tags)
    │   └── RDS: db-old (publicly accessible)
    └── Configuration history: full audit trail
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
