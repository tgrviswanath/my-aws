# AWS Cloud Practitioner (CLF-C02) Interview Preparation

## Domain 1: Cloud Concepts (24%)

### Q1: What are the six advantages of cloud computing?
1. **Trade fixed expense for variable expense** — pay only for what you use
2. **Benefit from massive economies of scale** — AWS buys in bulk, passes savings on
3. **Stop guessing capacity** — scale up/down as needed
4. **Increase speed and agility** — provision resources in minutes
5. **Stop spending money on data centers** — focus on business, not infrastructure
6. **Go global in minutes** — deploy to multiple regions instantly

### Q2: What is the difference between IaaS, PaaS, and SaaS?
**IaaS** (Infrastructure as a Service): You manage OS and above. AWS manages physical infrastructure. Example: EC2, EBS, VPC. Most control, most responsibility.
**PaaS** (Platform as a Service): You manage app and data. AWS manages OS, runtime, middleware. Example: Elastic Beanstalk, RDS. Less control, less responsibility.
**SaaS** (Software as a Service): You use the software. AWS manages everything. Example: Amazon WorkMail, Chime. No infrastructure management.

### Q3: What is the AWS Shared Responsibility Model?
**AWS is responsible for** (Security OF the cloud): Physical datacenters, hardware, networking, virtualization layer, managed service software (e.g., RDS OS patching).
**Customer is responsible for** (Security IN the cloud): Data encryption, IAM (users, roles, permissions), OS patching on EC2, network configuration (Security Groups, NACLs), application security.
The boundary shifts based on service type — EC2 (more customer responsibility) vs Lambda (less).

### Q4: What is the AWS Well-Architected Framework?
Six pillars for building reliable, secure, efficient, cost-effective systems:
1. **Operational Excellence**: Run and monitor systems, improve processes
2. **Security**: Protect data, systems, and assets
3. **Reliability**: Recover from failures, meet demand
4. **Performance Efficiency**: Use resources efficiently
5. **Cost Optimization**: Avoid unnecessary costs
6. **Sustainability**: Minimize environmental impact

---

## Domain 2: Security and Compliance (30%)

### Q5: What is IAM and what are its main components?
IAM (Identity and Access Management) controls who can do what in AWS.
- **Users**: Long-term credentials for humans
- **Groups**: Collections of users with shared permissions
- **Roles**: Temporary credentials for services and cross-account access
- **Policies**: JSON documents defining permissions
- **Best practice**: Use roles for services, groups for users, least privilege always

### Q6: What is MFA and why is it important?
MFA (Multi-Factor Authentication) requires a second form of verification beyond password. Protects against compromised passwords. AWS supports: virtual MFA (Google Authenticator), hardware MFA (YubiKey), SMS (not recommended). Always enable MFA for root account and all IAM users with console access.

### Q7: What is AWS Shield?
AWS Shield protects against DDoS (Distributed Denial of Service) attacks.
- **Shield Standard**: Free, automatic, protects against common L3/L4 attacks
- **Shield Advanced**: $3,000/month, L7 protection, DDoS cost protection, 24/7 DRT support

### Q8: What is Amazon Inspector?
Inspector automatically assesses EC2 instances and container images for software vulnerabilities and unintended network exposure. Generates findings with severity scores. Integrates with Security Hub.

### Q9: What is AWS Artifact?
AWS Artifact provides on-demand access to AWS compliance reports (SOC 2, PCI DSS, ISO 27001) and agreements. Use it to demonstrate AWS compliance to auditors.

---

## Domain 3: Cloud Technology and Services (34%)

### Q10: What is the difference between EC2 and Lambda?
**EC2**: Virtual machine. You manage OS, patching, scaling. Billed per second when running. Best for: long-running processes, full OS control, stateful applications.
**Lambda**: Serverless function. AWS manages everything. Billed per invocation and duration. Best for: event-driven, short-lived tasks (< 15 min), variable traffic.

### Q11: What is Amazon S3 and what are its storage classes?
S3 is object storage for any amount of data. Storage classes by access frequency:
- **Standard**: Frequent access, highest cost
- **Standard-IA**: Infrequent access, lower storage cost
- **Glacier**: Archive, hours to retrieve
- **Glacier Deep Archive**: Cheapest, 12-48hr retrieval
- **Intelligent-Tiering**: Auto-moves between tiers based on access

### Q12: What is Amazon RDS?
RDS (Relational Database Service) is a managed relational database. AWS handles: provisioning, patching, backups, Multi-AZ failover. Supports: MySQL, PostgreSQL, Oracle, SQL Server, Aurora. You manage: schema, queries, application code.

### Q13: What is Amazon CloudFront?
CloudFront is a CDN (Content Delivery Network) that caches content at 400+ edge locations worldwide. Reduces latency by serving content from the location closest to the user. Integrates with S3, ALB, EC2. Also provides DDoS protection and WAF integration.

### Q14: What is Amazon Route 53?
Route 53 is AWS's DNS service. Features: domain registration, DNS routing, health checks. Routing policies: Simple, Weighted, Latency, Failover, Geolocation, Multi-value.

### Q15: What is Amazon VPC?
VPC (Virtual Private Cloud) is your private, isolated network in AWS. You control: IP ranges, subnets, routing tables, internet gateways, security groups, NACLs. Every AWS account gets a default VPC per region.

---

## Domain 4: Billing, Pricing, and Support (12%)

### Q16: What are the AWS pricing models?
- **On-Demand**: Pay per second/hour, no commitment. Most expensive. Use for unpredictable workloads.
- **Reserved Instances**: 1 or 3-year commitment. Up to 72% savings. Use for steady-state production.
- **Spot Instances**: Bid on unused capacity. Up to 90% savings. Can be interrupted. Use for fault-tolerant batch.
- **Savings Plans**: Commit to $/hour spend. More flexible than Reserved. Up to 66% savings.
- **Free Tier**: 12 months free (EC2 t2.micro, S3 5GB) + always free (Lambda 1M req/mo).

### Q17: What is the AWS Total Cost of Ownership (TCO) Calculator?
TCO Calculator estimates cost savings when migrating from on-premises to AWS. Compares: hardware costs, data center costs, IT staff, power/cooling vs AWS costs. Helps justify cloud migration to management.

### Q18: What is AWS Trusted Advisor?
Trusted Advisor provides recommendations across 5 categories:
1. **Cost Optimization**: Idle resources, underutilized instances
2. **Performance**: Service limits, high utilization
3. **Security**: Open ports, MFA not enabled, public S3 buckets
4. **Fault Tolerance**: Multi-AZ, backups
5. **Service Limits**: Approaching AWS limits

### Q19: What are the AWS Support plans?
| Plan | Cost | Response Time | Features |
|------|------|--------------|---------|
| Basic | Free | — | Documentation, forums |
| Developer | $29/mo | 12-24 hours | Email support |
| Business | $100/mo | 1 hour (critical) | 24/7 phone/chat |
| Enterprise On-Ramp | $5,500/mo | 30 min (critical) | TAM pool |
| Enterprise | $15,000/mo | 15 min (critical) | Dedicated TAM |

### Q20: What is AWS Organizations?
AWS Organizations lets you manage multiple AWS accounts centrally. Features: consolidated billing (single bill for all accounts), Service Control Policies (SCPs) to restrict what accounts can do, organizational units (OUs) to group accounts. Use for: enterprise multi-account strategy, cost allocation, security guardrails.

---

## Quick Reference: Common Services

| Category | Service | One-line description |
|----------|---------|---------------------|
| Compute | EC2 | Virtual machines |
| Compute | Lambda | Serverless functions |
| Compute | ECS | Container orchestration |
| Storage | S3 | Object storage |
| Storage | EBS | Block storage for EC2 |
| Storage | EFS | Shared file system |
| Database | RDS | Managed relational DB |
| Database | DynamoDB | Managed NoSQL |
| Database | ElastiCache | In-memory cache |
| Network | VPC | Private network |
| Network | CloudFront | CDN |
| Network | Route 53 | DNS |
| Network | ALB/NLB | Load balancing |
| Security | IAM | Identity & access |
| Security | KMS | Encryption keys |
| Security | WAF | Web app firewall |
| Monitoring | CloudWatch | Metrics & logs |
| Monitoring | CloudTrail | API audit logs |
| DevOps | CodePipeline | CI/CD orchestration |
| DevOps | CloudFormation | Infrastructure as Code |
| Messaging | SQS | Message queue |
| Messaging | SNS | Pub/Sub |
| AI/ML | SageMaker | ML platform |
| Analytics | Athena | SQL on S3 |
| Analytics | Redshift | Data warehouse |
