# Architecture — Project 8.4 GuardDuty + Security Hub

## GuardDuty Data Sources

```
GuardDuty Detector
    ├── VPC Flow Logs    → detect port scanning, unusual traffic
    ├── DNS Logs         → detect C2 communication, crypto mining
    ├── CloudTrail       → detect unusual API calls, credential abuse
    ├── S3 Data Events   → detect data exfiltration
    ├── EKS Audit Logs   → detect Kubernetes threats
    └── EBS Volumes      → detect malware (scan on finding)
```

## Finding Flow

```
GuardDuty detects threat
    │
    │ Finding created (severity 1-10)
    ▼
EventBridge rule (severity >= 7)
    │
    ▼
SNS Topic → Email alert
    │
    ▼
Security Hub (aggregates all findings)
    ├── GuardDuty findings
    ├── Config compliance findings
    ├── Inspector vulnerability findings
    └── IAM Access Analyzer findings
```

## Security Hub Standards

```
CIS AWS Foundations Benchmark v1.4.0
    ├── 1.x IAM controls (MFA, password policy, root usage)
    ├── 2.x Storage controls (S3 encryption, logging)
    ├── 3.x Logging controls (CloudTrail, Config)
    └── 4.x Monitoring controls (alarms for root usage, etc.)

AWS Foundational Security Best Practices
    ├── EC2 controls
    ├── RDS controls
    ├── Lambda controls
    └── ...50+ controls
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
