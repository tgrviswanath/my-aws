# AWS Fundamentals — Cloud Concepts & Global Infrastructure

## Cloud Computing Models

| Model | You Manage | AWS Manages | Examples |
|-------|-----------|-------------|---------|
| IaaS | OS, runtime, apps, data | Physical infra, virtualization | EC2, EBS, VPC |
| PaaS | Apps, data | OS, runtime, middleware | Elastic Beanstalk, RDS |
| SaaS | Data, access | Everything | WorkMail, QuickSight |
| Serverless | Business logic | Everything else | Lambda, Fargate |

## AWS Global Infrastructure

### Regions
AWS has 33+ regions worldwide. Each region is a geographic area with multiple isolated datacenters.

**Region selection criteria:**
1. **Latency** — proximity to users
2. **Compliance** — data residency requirements (GDPR → EU regions)
3. **Service availability** — not all services in all regions
4. **Cost** — prices vary (us-east-1 often cheapest)
5. **Disaster recovery** — pair with another region

### Availability Zones (AZs)
- Each region has 2–6 AZs (typically 3)
- AZs are physically separated datacenters connected via high-bandwidth, low-latency links
- Named: us-east-1a, us-east-1b, us-east-1c
- **Best practice**: Deploy across 2+ AZs for high availability

### Edge Locations
- 400+ edge locations worldwide
- Used by CloudFront (CDN), Route 53, WAF
- Cache content closer to users to reduce latency

## Shared Responsibility Model

```
AWS Responsibility (Security OF the Cloud):
├── Physical security of datacenters
├── Hardware, networking, virtualization
└── Managed service software (RDS OS patching)

Customer Responsibility (Security IN the Cloud):
├── Data encryption (at rest and in transit)
├── IAM (users, roles, permissions)
├── OS patching (for EC2)
├── Network configuration (Security Groups, NACLs)
└── Application security
```

## AWS Pricing Models

| Model | Savings | Best For |
|-------|---------|----------|
| On-Demand | 0% | Unpredictable workloads, dev/test |
| Reserved 1yr | ~40% | Steady-state production |
| Reserved 3yr | ~60-72% | Long-term stable workloads |
| Spot | up to 90% | Batch, fault-tolerant, flexible timing |
| Savings Plans | up to 66% | Variable workloads needing flexibility |
| Dedicated Hosts | varies | Compliance, licensing requirements |

### Free Tier
- **Always Free**: Lambda (1M req/mo), DynamoDB (25GB), CloudWatch (10 metrics)
- **12 Months Free**: EC2 t2.micro (750hr/mo), S3 (5GB), RDS (750hr/mo)

## AWS CLI Basics

```bash
# Configure
aws configure
aws configure --profile dev

# Identity
aws sts get-caller-identity

# Query with JMESPath
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}" \
  --output table

# Use named profile
export AWS_PROFILE=production
```

## Interview Questions

### Q1: What is the difference between a Region and an Availability Zone?
**Region**: Geographic area containing multiple AZs. Completely independent from other regions.
**AZ**: One or more datacenters within a region. Physically separate but connected via low-latency links.
Deploy across AZs for HA within a region; deploy across regions for global DR.

### Q2: What is the AWS Shared Responsibility Model?
AWS is responsible for security **OF** the cloud (physical infrastructure, hardware, managed service software).
Customers are responsible for security **IN** the cloud (data, IAM, OS patching on EC2, network config, application security).
The boundary shifts based on service type — EC2 (more customer responsibility) vs Lambda (less).

### Q3: What are the differences between On-Demand, Reserved, and Spot instances?
- **On-Demand**: Pay per second, no commitment. Most expensive. Use for unpredictable workloads.
- **Reserved**: 1 or 3-year commitment. Up to 72% savings. Use for steady-state production.
- **Spot**: Bid on unused capacity. Up to 90% savings. Can be interrupted with 2-min notice.
- **Savings Plans**: Commit to $/hour spend. More flexible than Reserved.

### Q4: How do you choose an AWS region?
1. Latency: Closest to your users
2. Compliance: Data residency laws
3. Service availability: Not all services in all regions
4. Cost: Prices vary (us-east-1 often cheapest)
5. DR: Pair with another region for disaster recovery
