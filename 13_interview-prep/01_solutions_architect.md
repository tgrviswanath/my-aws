# AWS Solutions Architect Interview Preparation

## Certification-Style Questions

### Domain 1: Design Resilient Architectures

**Q1: A company needs a web application that can handle 10,000 concurrent users with 99.99% availability. Design the architecture.**

```
Architecture:
├── Route 53 (latency routing + health checks)
├── CloudFront (CDN, DDoS protection, SSL termination)
├── ALB (across 3 AZs)
├── EC2 Auto Scaling Group (3 AZs, target tracking 60% CPU)
│   └── Launch Template with IMDSv2, encrypted EBS
├── ElastiCache Redis (session store, query cache)
├── RDS Aurora PostgreSQL (Multi-AZ, 2 read replicas)
├── S3 (static assets, user uploads)
└── VPC (public/private/DB subnets, 3 AZs)

Key decisions:
- CloudFront reduces origin load by caching static content
- ElastiCache eliminates repeated DB queries
- Aurora read replicas handle read-heavy traffic
- ASG handles traffic spikes automatically
- Multi-AZ for all stateful components
```

---

**Q2: A company's RDS database is experiencing high CPU during peak hours. What are your options?**

```
Immediate:
1. Add read replicas → offload read traffic
2. Implement ElastiCache → cache frequent queries
3. Optimize slow queries (Performance Insights)

Short-term:
4. Scale up instance class (vertical scaling)
5. Enable Aurora → better performance, more replicas

Long-term:
6. Migrate to Aurora Serverless v2 (auto-scales)
7. Implement read/write splitting in application
8. Consider DynamoDB for high-read, simple access patterns
9. Database sharding for write-heavy workloads
```

---

**Q3: Design a disaster recovery solution with RPO < 1 hour and RTO < 4 hours.**

```
Strategy: Pilot Light

Primary (us-east-1):
├── Full production stack
└── Automated backups to S3 (cross-region replication)

DR (eu-west-1):
├── RDS read replica (promotes to primary on failover)
├── AMIs replicated from primary
├── ASG with 0 desired capacity (scales up on failover)
└── Route 53 failover routing (health check on primary)

Failover procedure (automated):
1. Route 53 detects primary health check failure
2. DNS switches to DR region (< 1 min)
3. Lambda triggers: promote RDS replica, scale ASG
4. Total RTO: ~30-60 minutes

RPO: RDS replication lag (typically < 1 min) + backup interval
```

---

### Domain 2: Design High-Performing Architectures

**Q4: A media company needs to process 1 million video uploads per day. Design the pipeline.**

```
Architecture:
1. S3 (upload destination) + pre-signed URLs for direct upload
2. S3 Event Notification → SQS queue
3. ECS Fargate (video processing workers, auto-scaled by SQS depth)
4. Elastic Transcoder or MediaConvert (video transcoding)
5. S3 (processed videos, multiple resolutions)
6. CloudFront (video delivery CDN)
7. DynamoDB (job status tracking)
8. SNS → user notification on completion

Scaling:
- SQS queue depth drives ECS task scaling
- Spot Instances for cost optimization (fault-tolerant batch)
- S3 Transfer Acceleration for global uploads
```

---

**Q5: How would you design a real-time leaderboard for a gaming application with 1 million active users?**

```
Architecture:
├── API Gateway + Lambda (score submission)
├── DynamoDB (player scores, game data)
├── ElastiCache Redis Sorted Sets (real-time leaderboard)
│   └── ZADD leaderboard score userId
│   └── ZREVRANGE leaderboard 0 99 (top 100)
├── DynamoDB Streams → Lambda (sync to Redis on score change)
└── WebSocket API Gateway (push leaderboard updates to clients)

Why Redis Sorted Sets?
- O(log N) insert/update
- O(log N + M) range query
- Atomic operations
- Sub-millisecond latency
```

---

### Domain 3: Design Secure Applications

**Q6: How do you secure an API that handles financial transactions?**

```
Security layers:
1. CloudFront + WAF (DDoS, OWASP Top 10, rate limiting)
2. API Gateway (throttling, API keys, usage plans)
3. Cognito (authentication, JWT tokens)
4. Lambda Authorizer (custom authorization logic)
5. VPC (Lambda in private subnet)
6. IAM roles (least privilege for each Lambda)
7. Secrets Manager (DB credentials, API keys)
8. KMS (encrypt sensitive data at rest)
9. TLS 1.2+ everywhere (enforce HTTPS)
10. CloudTrail (audit all API calls)
11. GuardDuty (threat detection)
12. VPC Endpoints (keep traffic off internet)

Data:
- Encrypt PII with KMS before storing
- Tokenize card numbers (never store raw)
- Field-level encryption for sensitive fields
```

---

### Domain 4: Design Cost-Optimized Architectures

**Q7: A startup has a web app with unpredictable traffic. How do you minimize costs while maintaining performance?**

```
Architecture:
├── CloudFront (cache static content, reduce origin hits)
├── API Gateway + Lambda (pay per request, no idle cost)
├── DynamoDB On-Demand (pay per request)
├── S3 (static hosting, cheap storage)
└── Aurora Serverless v2 (scales to 0 when idle)

Cost comparison vs always-on:
- Lambda vs EC2 t3.medium: $0 idle vs $30/month
- DynamoDB On-Demand vs RDS: scales with usage
- Aurora Serverless: $0 when idle vs $12/month minimum

When traffic grows:
- Lambda → ECS Fargate (more control, lower cost at scale)
- DynamoDB On-Demand → Provisioned + Auto Scaling
- Aurora Serverless → Aurora Provisioned
```

---

## Scenario-Based Questions

**Q8: Users report intermittent 504 errors on your API. How do you debug?**

```
Investigation steps:
1. CloudWatch Metrics: ALB HTTPCode_ELB_504_Count
2. ALB Access Logs: identify which targets are timing out
3. Target Group health: check unhealthy instances
4. EC2 metrics: CPU, memory, network on app servers
5. RDS metrics: DatabaseConnections, CPUUtilization, ReadLatency
6. X-Ray: trace slow requests, identify bottleneck
7. CloudWatch Logs Insights: query for slow requests

Common causes:
- Application timeout < ALB timeout (increase app timeout)
- Database connection pool exhausted (add RDS Proxy)
- Memory leak causing GC pauses (increase instance size)
- Downstream service slow (add circuit breaker)
- Cold start on Lambda (provisioned concurrency)

Fix:
- Short-term: increase ALB idle timeout, scale up
- Long-term: fix root cause (DB optimization, connection pooling)
```

---

**Q9: Your S3 bucket costs tripled this month. How do you investigate?**

```
Investigation:
1. Cost Explorer: filter by S3, group by operation type
2. S3 Storage Lens: storage growth, request metrics
3. S3 Access Logs: identify high-request patterns
4. CloudTrail: who is making requests

Common causes:
- Data transfer out (large files downloaded frequently)
  → Fix: CloudFront CDN, pre-signed URLs
- Versioning enabled, many versions accumulating
  → Fix: lifecycle policy to expire old versions
- Replication costs
  → Review if replication is still needed
- Glacier retrieval fees
  → Review retrieval tier (use Bulk instead of Expedited)
- Incomplete multipart uploads
  → Fix: lifecycle rule to abort after 7 days
```

---

**Q10: Design a multi-tenant SaaS application on AWS.**

```
Isolation models:
1. Silo (separate AWS account per tenant) — strongest isolation, highest cost
2. Pool (shared resources, tenant ID in data) — lowest cost, shared fate
3. Bridge (shared compute, separate DB) — balance

Recommended architecture:
├── Route 53 (tenant.app.com routing)
├── CloudFront (per-tenant cache behaviors)
├── ALB (host-based routing)
├── ECS Fargate (shared compute, tenant context in JWT)
├── RDS Aurora (shared cluster, row-level security by tenant_id)
│   OR separate schemas per tenant
├── DynamoDB (PK: tenantId#entityId)
├── S3 (separate prefix per tenant: s3://bucket/tenant-id/)
├── KMS (separate key per tenant for encryption)
└── Cognito (separate user pool per tenant OR shared with tenant claim)

Security:
- JWT contains tenantId claim
- All DB queries filter by tenantId
- S3 bucket policies enforce tenant prefix
- KMS key policies per tenant
```

---

## Quick Reference: Common Architecture Patterns

| Pattern | AWS Services |
|---------|-------------|
| Static website | S3 + CloudFront + Route 53 |
| Serverless API | API Gateway + Lambda + DynamoDB |
| 3-tier web app | ALB + EC2 ASG + RDS |
| Event processing | S3 → SQS → Lambda → DynamoDB |
| Real-time streaming | Kinesis → Lambda → DynamoDB/S3 |
| ML pipeline | S3 → SageMaker → S3 → API Gateway |
| Data lake | S3 + Glue + Athena + QuickSight |
| Microservices | ECS/EKS + ALB + RDS + ElastiCache |
| Batch processing | S3 → SQS → EC2 Spot → S3 |
| IoT | IoT Core → Kinesis → Lambda → DynamoDB |

---

## Certification Tips

### AWS Solutions Architect Associate
- Focus: Core services (EC2, S3, RDS, VPC, IAM, Lambda)
- Key topics: HA design, cost optimization, security
- Exam style: Scenario-based, choose best option

### AWS Solutions Architect Professional
- Focus: Complex architectures, migrations, advanced services
- Key topics: Multi-account, hybrid connectivity, cost at scale
- Exam style: Complex scenarios, multiple correct answers (choose best)

### Study Strategy
1. Read AWS Well-Architected Framework (5 pillars)
2. Practice with AWS Free Tier
3. Use AWS Skill Builder practice exams
4. Review AWS whitepapers (especially disaster recovery)
5. Understand trade-offs, not just features
