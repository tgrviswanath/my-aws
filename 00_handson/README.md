# 🛠️ AWS Hands-On Use Cases — Learn by Doing

> Real-world scenarios for every major AWS service. Each use case includes the business problem, architecture, step-by-step CLI commands, and what you learn.

---

## 📁 Structure

```
00_handson/
├── 00_learning_roadmap.md        Master roadmap: phases, companion skills, daily routine
├── 01_ec2_usecases.md            Web server, bastion host, spot batch jobs
├── 02_s3_usecases.md             Static website, data lake, cross-account sharing
├── 03_lambda_usecases.md         Image resize, scheduled jobs, API backend
├── 04_rds_usecases.md            Multi-AZ setup, read replicas, RDS Proxy
├── 05_dynamodb_usecases.md       Session store, leaderboard, e-commerce cart
├── 06_vpc_usecases.md            3-tier network, VPC peering, private endpoints
├── 07_iam_usecases.md            Cross-account roles, least privilege, ABAC
├── 08_cloudwatch_usecases.md     Custom metrics, log insights, anomaly detection
├── 09_sqs_sns_usecases.md        Order processing, fan-out, dead letter queues
├── 10_ecs_usecases.md            Fargate web app, blue/green deploy, auto-scaling
├── 11_cloudfront_usecases.md     CDN for SPA, signed URLs, WAF integration
├── 12_elasticache_usecases.md    Session store, query cache, rate limiter
├── 13_kinesis_usecases.md        Real-time analytics, log streaming, CDC
├── 14_step_functions_usecases.md Order workflow, ETL orchestration, retry logic
├── 15_cost_optimization_usecases.md  Right-sizing, Spot, lifecycle policies
├── 16_frontend_deployment_eks.md     End-to-end: Docker → ECR → EKS (with troubleshooting)
├── 17_scenarios_beginner.md      Scenarios 1–5:  S3, EC2, IAM, RDS, Python boto3
├── 18_scenarios_intermediate.md  Scenarios 6–12: VPC, Docker, ECS, Terraform, CI/CD
├── 19_scenarios_advanced.md      Scenarios 13–16: Auto Scaling, Serverless, Monitoring, Events
├── 20_scenarios_data_engineering.md  Scenarios 17–20: Data lake, ETL, Kinesis, EMR
└── 21_scenarios_production.md    Scenarios 21–24: Netflix-style, EKS, multi-env, data platform
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
| Real Project | Docker → ECR → EKS end-to-end deployment | 1 day |

## 🎯 24 Hands-On Scenarios (Structured Path)

| Level | Scenarios | File |
|-------|---------|------|
| 🟢 Beginner | 1–5: S3, EC2, IAM, RDS, Python | `17_scenarios_beginner.md` |
| 🟡 Intermediate | 6–12: VPC, Docker, ECS, Terraform, CI/CD | `18_scenarios_intermediate.md` |
| 🔴 Advanced | 13–16: Auto Scaling, Serverless, Monitoring | `19_scenarios_advanced.md` |
| ⚫ Data Engineering | 17–20: Data lake, ETL, Kinesis, EMR | `20_scenarios_data_engineering.md` |
| 🏆 Production | 21–24: Netflix-style, EKS, multi-env, data platform | `21_scenarios_production.md` |

**Start here**: `00_learning_roadmap.md` → then work through scenarios 1–24 in order.


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

The document from the .docx was converted into 16_frontend_deployment_eks.md with major enhancements:
What was in the original document → What was added/improved:

Original	Enhanced Version
Basic steps listed	Full CLI commands with expected outputs
"Why multi-stage build?" mentioned	Detailed comparison: 1.2GB → 25MB, security benefits
Simple Dockerfile	Added nginx.conf for React Router, layer caching explanation
"Screenshot here" placeholders	Exact expected output for every command
Issue 1 mentioned briefly	Root cause analysis + fix + lesson learned
Basic YAML files	Added resources, livenessProbe, readinessProbe with explanations
"Next enhancements" listed	Full working code for HTTPS/Ingress, GitHub Actions CI/CD, HPA, monitoring
No resume section	7 ready-to-use resume bullet points
No interview prep	30-second interview explanation script
Simple architecture diagram	Full ASCII architecture diagram showing complete pipeline
No debug commands	Complete kubectl debug/maintenance reference
Cleanup mentioned	Step-by-step cleanup with cost warning
All 15 use case files cover:
File	Services	Use Cases
01	EC2	Web server, Spot batch, bastion, auto scaling
02	S3	SPA hosting, data lake, cross-account, pre-signed uploads, event-driven
03	Lambda	Image thumbnails, cron reports, REST API, SQS consumer
04	RDS/Aurora	Multi-AZ, read replicas, RDS Proxy, Serverless v2, PITR
05	DynamoDB	Shopping cart, leaderboard, sessions, Streams notifications
06	VPC	3-tier network, peering, endpoints, flow log investigation
07	IAM	Least privilege, cross-account, ABAC, break-glass
08	SQS/SNS	Order pipeline, fan-out, FIFO transactions, DLQ investigation
09	CloudWatch	Business metrics, composite alarms, log investigation, Agent
10	ECS	Fargate API, auto scaling, blue/green CodeDeploy
11	CloudFront	SPA CDN, signed URLs, WAF integration
12	ElastiCache	API caching, sessions, rate limiter, pub/sub
13	Kinesis	Clickstream, Firehose → S3, CDC, Analytics SQL
14	Step Functions	Order workflow, ETL, Map state bulk processing
15	Cost	Waste audit, right-sizing, Spot, S3 lifecycle, RI vs Savings Plans
16	Docker+ECR+EKS	Full deployment guide from the docx — enhanced with troubleshooting, resume bullets, interview prep