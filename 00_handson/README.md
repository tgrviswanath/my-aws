# 🛠️ AWS Hands-On Use Cases — Learn by Doing

> Real-world scenarios for every major AWS service. Each use case includes the business problem, architecture, step-by-step CLI commands, and what you learn.

---

## 📁 Structure

```
00_handson/
├── 01_ec2_usecases.md          Web server, bastion host, spot batch jobs
├── 02_s3_usecases.md           Static website, data lake, cross-account sharing
├── 03_lambda_usecases.md       Image resize, scheduled jobs, API backend
├── 04_rds_usecases.md          Multi-AZ setup, read replicas, RDS Proxy
├── 05_dynamodb_usecases.md     Session store, leaderboard, e-commerce cart
├── 06_vpc_usecases.md          3-tier network, VPC peering, private endpoints
├── 07_iam_usecases.md          Cross-account roles, least privilege, ABAC
├── 08_cloudwatch_usecases.md   Custom metrics, log insights, anomaly detection
├── 09_sqs_sns_usecases.md      Order processing, fan-out, dead letter queues
├── 10_ecs_usecases.md          Fargate web app, blue/green deploy, auto-scaling
├── 11_cloudfront_usecases.md   CDN for SPA, signed URLs, WAF integration
├── 12_elasticache_usecases.md  Session store, query cache, rate limiter
├── 13_kinesis_usecases.md      Real-time analytics, log streaming, CDC
├── 14_step_functions_usecases.md Order workflow, ETL orchestration, retry logic
└── 15_cost_optimization_usecases.md  Right-sizing, Spot, lifecycle policies
```

---

## 🎯 How to Use This Folder

Each file follows this pattern:
1. **Business Problem** — why you'd use this service
2. **Architecture** — how it fits together
3. **Step-by-step CLI** — exact commands to run
4. **What you learn** — key concepts reinforced
5. **Common mistakes** — pitfalls to avoid

**Prerequisites**: AWS CLI configured, an AWS account (free tier works for most)

---

## 🗺️ Learning Path

| Level | Use Cases | Time |
|-------|-----------|------|
| Beginner | EC2, S3, IAM, CloudWatch | 2–3 days |
| Intermediate | Lambda, RDS, VPC, SQS/SNS, ECS | 3–4 days |
| Advanced | DynamoDB, ElastiCache, Kinesis, Step Functions | 3–4 days |
| Expert | CloudFront, Cost Optimization, multi-service architectures | 2–3 days |


Done — 00_handson Folder Complete
16 new files added covering every major AWS service with real-world use cases.

What's in each file
File	Use Cases	Key Concepts
01_ec2_usecases.md	Web server, Spot batch jobs, bastion host, auto scaling	IMDSv2, SSM over SSH, Spot interruption handling, scheduled scaling
02_s3_usecases.md	React SPA hosting, data lake, cross-account access, pre-signed uploads, event-driven processing	OAC, lifecycle policies, CORS, S3 event notifications
03_lambda_usecases.md	Image thumbnail generator, scheduled reports, REST API backend, SQS consumer	PIL processing, EventBridge cron, SAM templates, partial batch failures
04_rds_usecases.md	Multi-AZ setup, read replicas, RDS Proxy, Aurora Serverless v2, PITR recovery	Failover testing, connection pooling, point-in-time restore
05_dynamodb_usecases.md	Shopping cart, leaderboard, session store, DynamoDB Streams notifications	TTL, composite keys, GSI design, conditional writes
06_vpc_usecases.md	3-tier network, VPC peering, VPC endpoints, flow log investigation	NAT HA, security group chaining, Gateway vs Interface endpoints
07_iam_usecases.md	Least-privilege microservice role, cross-account access, ABAC, break-glass	Policy simulation, ExternalId, tag-based access control
08_sqs_sns_usecases.md	Order processing pipeline, fan-out, FIFO transactions, DLQ investigation	Visibility timeout, filter policies, message redrive
09_cloudwatch_usecases.md	Business metrics dashboard, composite alarms, log investigation, CloudWatch Agent	Custom metrics, anomaly detection, Logs Insights queries
10_ecs_usecases.md	Fargate web API, auto scaling, blue/green with CodeDeploy	Task definitions, deployment circuit breaker, canary traffic shifting
11_cloudfront_usecases.md	React SPA CDN, signed URLs for video streaming, WAF integration	OAC, CloudFront Functions, cache behaviors, WAF managed rules
12_elasticache_usecases.md	API response caching, distributed sessions, rate limiter, pub/sub notifications	Cache-aside pattern, sliding window rate limiter, Redis sorted sets
13_kinesis_usecases.md	Clickstream analytics, Firehose → S3 data lake, CDC, real-time aggregations	Partition keys, Firehose buffering, Lambda transformer, Kinesis Analytics SQL
14_step_functions_usecases.md	Order workflow, ETL orchestration, bulk image processing	Choice states, Parallel branches, waitForTaskToken, Map state
15_cost_optimization_usecases.md	Waste elimination, right-sizing, Spot for batch, S3 lifecycle, RI vs Savings Plans	Compute Optimizer, Spot fleet, lifecycle policies, budget alerts
README.md	Index of all use cases with learning path	—
Pattern used in every file
Each use case follows: Business Problem → Architecture diagram → Step-by-step CLI/code → What you learn → Common mistakes table