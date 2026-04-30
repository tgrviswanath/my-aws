# Core AWS Services — Overview

This section provides a high-level overview of core AWS services. Each service has a dedicated deep-dive in its respective folder.

## Service Map

```
Compute          → /compute/
Storage          → /storage/
Networking       → /networking/
Databases        → /databases/
DevOps           → /devops/
Security         → /security/
Monitoring       → /monitoring/
Architecture     → /architecture/
```

## Core Services Quick Reference

### Compute
| Service | Type | Key Feature |
|---------|------|-------------|
| EC2 | IaaS | Full VM control, 400+ instance types |
| Lambda | Serverless | Event-driven, pay-per-invocation |
| ECS | Container | AWS-native orchestration |
| EKS | Container | Managed Kubernetes |
| Fargate | Serverless Container | No node management |
| Elastic Beanstalk | PaaS | Auto-managed deployment |

### Storage
| Service | Type | Durability |
|---------|------|-----------|
| S3 | Object | 11 nines |
| EBS | Block | 99.8-99.9% |
| EFS | File (NFS) | 11 nines |
| FSx | File (Windows/Lustre) | 11 nines |
| Glacier | Archive | 11 nines |

### Networking
| Service | Purpose |
|---------|---------|
| VPC | Private network isolation |
| Route 53 | DNS + health checks |
| CloudFront | CDN + edge caching |
| ALB/NLB | Load balancing |
| API Gateway | API management |
| Direct Connect | Dedicated connectivity |

### Databases
| Service | Type | Use Case |
|---------|------|---------|
| RDS | Relational | MySQL, PostgreSQL, Oracle |
| Aurora | Relational | High-performance, cloud-native |
| DynamoDB | NoSQL | Serverless, millisecond latency |
| ElastiCache | In-memory | Redis/Memcached caching |
| Redshift | Data Warehouse | Analytics, petabyte scale |
| DocumentDB | Document | MongoDB-compatible |

### Security
| Service | Purpose |
|---------|---------|
| IAM | Identity & access management |
| KMS | Encryption key management |
| Secrets Manager | Secret storage & rotation |
| WAF | Web application firewall |
| Shield | DDoS protection |
| GuardDuty | Threat detection |
| Security Hub | Centralized security findings |
| Macie | Sensitive data discovery |

### DevOps
| Service | Purpose |
|---------|---------|
| CodePipeline | CI/CD orchestration |
| CodeBuild | Build & test |
| CodeDeploy | Deployment automation |
| CodeCommit | Git repository |
| CloudFormation | Infrastructure as Code |
| Systems Manager | Operations management |
| CDK | IaC with programming languages |

### Monitoring
| Service | Purpose |
|---------|---------|
| CloudWatch | Metrics, logs, alarms |
| CloudTrail | API audit logging |
| X-Ray | Distributed tracing |
| Config | Configuration compliance |
| Health Dashboard | AWS service health |

### Integration & Messaging
| Service | Pattern |
|---------|---------|
| SQS | Message queue |
| SNS | Pub/Sub |
| EventBridge | Event bus |
| Step Functions | Workflow orchestration |
| Kinesis | Real-time streaming |
| MSK | Managed Kafka |

## AWS Global Infrastructure (2024)

- **Regions**: 33+ geographic regions
- **Availability Zones**: 105+ AZs
- **Edge Locations**: 400+ (CloudFront, Route 53)
- **Local Zones**: 30+ (low-latency for specific cities)
- **Wavelength Zones**: 5G edge computing

## Service Selection Decision Trees

### Compute Decision
```
Need full OS control? → EC2
Event-driven, < 15 min? → Lambda
Containerized app?
  ├── Simple, AWS-only → ECS Fargate
  ├── Kubernetes needed → EKS
  └── No infra management → App Runner
Long-running batch? → ECS/Fargate or EC2 Spot
```

### Database Decision
```
Relational data?
  ├── High performance, cloud-native → Aurora
  ├── Standard MySQL/PostgreSQL → RDS
  └── Need full DB control → EC2 + DB
NoSQL?
  ├── Key-value, serverless → DynamoDB
  ├── Document (MongoDB) → DocumentDB
  └── In-memory cache → ElastiCache
Analytics?
  ├── SQL queries on S3 → Athena
  ├── Data warehouse → Redshift
  └── Real-time → Kinesis + Lambda
```

### Storage Decision
```
Files/objects via HTTP? → S3
Block storage for EC2? → EBS
Shared filesystem? → EFS
Windows file shares? → FSx for Windows
HPC/ML workloads? → FSx for Lustre
Long-term archive? → S3 Glacier
```
