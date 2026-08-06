# Architecture — Project 10.1 Multi-account AWS Organization

## Account Structure

```
Root (Management Account)
    │
    ├── Security OU
    │   └── Security Account
    │         ├── GuardDuty master detector
    │         ├── Security Hub aggregator
    │         └── CloudTrail organization trail
    │
    ├── Infrastructure OU
    │   └── Shared Services Account
    │         ├── ECR (shared container registry)
    │         ├── Route53 (shared DNS)
    │         └── Transit Gateway
    │
    ├── Workloads OU
    │   ├── Dev Account     ← SCP: t3.micro/small only
    │   ├── Staging Account ← SCP: us-east-1 only
    │   └── Prod Account    ← SCP: deny root, require encryption
    │
    └── Sandbox OU
        └── Developer Sandbox Accounts (auto-expire after 30 days)
```

## SCP Evaluation

```
Request: Create EC2 m5.4xlarge in Dev account
    │
    ├── SCP check: LimitEC2InstanceTypes
    │   → m5.4xlarge NOT in [t3.micro, t3.small]
    │   → DENY
    │
    └── Result: AccessDenied (even if IAM allows it)

SCP + IAM = effective permissions
Both must allow for the action to succeed.
Management account is EXEMPT from SCPs.
```

## Cross-account Access Pattern

```
Developer in Management Account
    │
    │ sts:AssumeRole
    ▼
OrganizationAccountAccessRole in Dev Account
    │
    │ (automatically created when account is created via Organizations)
    ▼
Full access to Dev Account resources
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
