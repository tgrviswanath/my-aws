# AWS Cloud Learning & Interview Preparation Repository

A comprehensive, production-grade AWS learning repository progressing from beginner to expert level. Covers cloud architecture, scalability, DevOps, security, cost optimization, and real-world implementations.

---

## Repository Structure

```
aws-cloud/
├── fundamentals/          # Cloud basics, CLI, pricing
├── compute/               # EC2, Auto Scaling, Lambda, ECS/EKS
├── storage/               # S3, EBS, EFS, Glacier
├── networking/            # VPC, Route 53, VPN, Direct Connect
├── databases/             # RDS, Aurora, DynamoDB, ElastiCache
├── devops/                # CI/CD, CloudFormation, Terraform
├── security/              # IAM, KMS, Secrets Manager, WAF
├── monitoring/            # CloudWatch, CloudTrail, X-Ray
├── architecture/          # HA/DR, Microservices, Cost Optimization
├── projects/              # 5 end-to-end real-world projects
├── interview-prep/        # Q&A for all certification levels
├── labs/                  # Hands-on step-by-step exercises
├── utils/                 # Reusable IaC templates and scripts
├── EVALUATION.md          # Self-evaluation and gaps
└── README.md              # This file
```

---

## Quick Start

### Prerequisites

```bash
# 1. Create AWS Account (free tier)
# https://aws.amazon.com/free/

# 2. Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Windows
winget install Amazon.AWSCLI

# 3. Configure CLI
aws configure
# AWS Access Key ID: [your key]
# AWS Secret Access Key: [your secret]
# Default region: us-east-1
# Default output format: json

# 4. Verify
aws sts get-caller-identity

# 5. Install additional tools
pip install aws-sam-cli          # Serverless Application Model
brew install terraform           # Infrastructure as Code
brew install eksctl              # EKS cluster management
```

---

## Learning Roadmap

### 🟢 Beginner (Week 1-2)
| Topic | File | Time |
|-------|------|------|
| Cloud concepts & AWS basics | `fundamentals/01_cloud_concepts.md` | 2hr |
| AWS CLI setup | `fundamentals/02_aws_cli_basics.sh` | 1hr |
| Pricing & billing | `fundamentals/03_pricing_calculator.md` | 1hr |
| **Lab**: Launch EC2 | `labs/01_ec2_networking_lab.md` | 1hr |

### 🟡 Intermediate (Week 3-6)
| Topic | File | Time |
|-------|------|------|
| EC2 deep dive | `compute/01_ec2_deep_dive.md` | 3hr |
| Auto Scaling | `compute/02_auto_scaling.md` | 2hr |
| Load Balancers | `compute/03_load_balancers.md` | 2hr |
| Lambda & Serverless | `compute/04_lambda_serverless.md` | 3hr |
| S3 deep dive | `storage/01_s3_deep_dive.md` | 2hr |
| EBS, EFS, Glacier | `storage/02_ebs_efs_glacier.md` | 2hr |
| VPC deep dive | `networking/01_vpc_deep_dive.md` | 3hr |
| Route 53 & Hybrid | `networking/02_route53_hybrid.md` | 2hr |
| RDS & Aurora | `databases/01_rds_aurora.md` | 3hr |
| DynamoDB | `databases/02_dynamodb.md` | 3hr |
| ElastiCache | `databases/03_elasticache.md` | 2hr |
| **Lab**: Lambda + S3 | `labs/02_lambda_s3_lab.md` | 1.5hr |
| **Lab**: IAM Roles | `labs/03_iam_roles_lab.md` | 1hr |

### 🔴 Advanced (Week 7-10)
| Topic | File | Time |
|-------|------|------|
| IAM deep dive | `security/01_iam_deep_dive.md` | 3hr |
| KMS, Secrets, WAF | `security/02_kms_secrets_waf.md` | 2hr |
| CloudWatch, CloudTrail, X-Ray | `monitoring/01_cloudwatch_cloudtrail_xray.md` | 3hr |
| CI/CD Pipeline | `devops/01_cicd_pipeline.md` | 3hr |
| CloudFormation & Terraform | `devops/02_infrastructure_as_code.md` | 4hr |
| Containers (ECS/EKS) | `compute/05_containers_ecs_eks.md` | 3hr |

### ⚫ Expert (Week 11-12)
| Topic | File | Time |
|-------|------|------|
| HA & Disaster Recovery | `architecture/01_high_availability_dr.md` | 3hr |
| Microservices & Event-Driven | `architecture/02_microservices_event_driven.md` | 3hr |
| Cost Optimization (FinOps) | `architecture/03_cost_optimization.md` | 2hr |
| **Project**: Scalable Web App | `projects/01_scalable_webapp/` | 4hr |
| **Project**: Serverless App | `projects/02_serverless_app/` | 4hr |
| **Project**: Data Pipeline | `projects/04_data_pipeline/` | 3hr |
| **Project**: CI/CD Pipeline | `projects/05_cicd_pipeline/` | 3hr |

---

## 30/60/90 Day Study Plan

### 30 Days — Cloud Practitioner Ready
- Week 1-2: Fundamentals + Core services overview
- Week 3-4: Compute, Storage, Networking basics
- Goal: Pass AWS Cloud Practitioner exam

### 60 Days — Solutions Architect Associate Ready
- Week 5-6: Databases, Security, Monitoring
- Week 7-8: Architecture patterns, HA/DR, Cost optimization
- Week 9: Practice exams + review weak areas
- Goal: Pass AWS Solutions Architect Associate

### 90 Days — Job Ready
- Week 10-11: DevOps, IaC, Containers
- Week 12: Complete all 5 projects
- Week 13: Interview prep Q&A
- Goal: Ready for Cloud/DevOps Engineer roles

---

## Certification Guide

| Certification | Difficulty | Prerequisites | Study Time |
|--------------|-----------|--------------|-----------|
| Cloud Practitioner | ⭐ | None | 2-4 weeks |
| Solutions Architect Associate | ⭐⭐⭐ | Cloud Practitioner | 4-8 weeks |
| Developer Associate | ⭐⭐⭐ | Cloud Practitioner | 4-8 weeks |
| SysOps Administrator | ⭐⭐⭐ | Cloud Practitioner | 4-8 weeks |
| Solutions Architect Professional | ⭐⭐⭐⭐⭐ | SAA | 8-12 weeks |
| DevOps Engineer Professional | ⭐⭐⭐⭐⭐ | SAA or Dev | 8-12 weeks |

### Recommended Order
1. Cloud Practitioner (foundation)
2. Solutions Architect Associate (most valuable)
3. Developer Associate (if developer role)
4. DevOps Engineer Professional (if DevOps role)

---

## Projects Overview

| # | Project | Services | Difficulty |
|---|---------|---------|-----------|
| 01 | Scalable Web App | EC2, ALB, ASG, RDS Aurora, ElastiCache, CloudFront | ⭐⭐⭐ |
| 02 | Serverless App | Lambda, API Gateway, DynamoDB, SQS, Cognito | ⭐⭐⭐ |
| 03 | Microservices (EKS) | EKS, ECR, ALB, RDS, ElastiCache, Istio | ⭐⭐⭐⭐⭐ |
| 04 | Data Pipeline | S3, Kinesis, Glue, Athena, QuickSight | ⭐⭐⭐⭐ |
| 05 | CI/CD Pipeline | CodePipeline, CodeBuild, CodeDeploy, ECS | ⭐⭐⭐⭐ |

---

## Key AWS Services Quick Reference

### Compute
| Service | Use Case |
|---------|---------|
| EC2 | Virtual machines, full control |
| Lambda | Serverless functions, event-driven |
| ECS Fargate | Serverless containers |
| EKS | Managed Kubernetes |
| Elastic Beanstalk | PaaS, simple deployment |

### Storage
| Service | Use Case |
|---------|---------|
| S3 | Object storage, static websites, data lake |
| EBS | Block storage for EC2 |
| EFS | Shared file system for EC2 |
| FSx | Managed Windows/Lustre file systems |
| Glacier | Long-term archival |

### Database
| Service | Use Case |
|---------|---------|
| RDS | Managed relational (MySQL, PostgreSQL) |
| Aurora | High-performance relational |
| DynamoDB | NoSQL, serverless, millisecond latency |
| ElastiCache | In-memory cache (Redis/Memcached) |
| Redshift | Data warehouse |

### Networking
| Service | Use Case |
|---------|---------|
| VPC | Private network |
| Route 53 | DNS, health checks, routing |
| CloudFront | CDN, edge caching |
| ALB/NLB | Load balancing |
| API Gateway | REST/HTTP/WebSocket APIs |

### DevOps
| Service | Use Case |
|---------|---------|
| CodePipeline | CI/CD orchestration |
| CodeBuild | Build and test |
| CodeDeploy | Deployment automation |
| CloudFormation | Infrastructure as Code |
| Systems Manager | Operations management |

---

## AWS Well-Architected Framework

The 6 pillars every architect must know:

1. **Operational Excellence** — Run and monitor systems, improve processes
2. **Security** — Protect data, systems, and assets
3. **Reliability** — Recover from failures, meet demand
4. **Performance Efficiency** — Use resources efficiently
5. **Cost Optimization** — Avoid unnecessary costs
6. **Sustainability** — Minimize environmental impact

---

## Resources

- [AWS Documentation](https://docs.aws.amazon.com/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Skill Builder](https://skillbuilder.aws/) (practice exams)
- [AWS Architecture Center](https://aws.amazon.com/architecture/)
- [AWS Whitepapers](https://aws.amazon.com/whitepapers/)
- [AWS re:Invent Videos](https://www.youtube.com/@AWSEventsChannel)

---

## Contributing

This repository follows a consistent format for all modules:
- Theory with diagrams
- CLI examples
- CloudFormation/Terraform IaC
- Security considerations
- Cost considerations
- Interview Q&A

---

*Last updated: 2024 | Covers AWS services as of 2024*
