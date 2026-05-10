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
├── 21_scenarios_production.md    Scenarios 21–24: Netflix-style, EKS, multi-env, data platform
└── 22_best_practices_guide.md    How to practice, project order, checklist, interview prep
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

Complete Hands-on Scenarios Roadmap

For Amazon Web Services + Linux + Docker + Terraform + Python + SQL

The goal is:

not just learning services
but learning how real systems are built
LEVEL 1 — Beginner Hands-on Scenarios

Goal:
Understand basic cloud workflow.

Scenario 1 — Host a Static Website in S3
Skills
S3
IAM
Static website hosting
Tasks
Create S3 bucket
Enable static hosting
Upload HTML/CSS files
Configure public access
Access website URL
Learn
object storage
bucket policies
permissions
public vs private access
Scenario 2 — Launch Linux Server in EC2
Skills
EC2
SSH
Linux basics
Tasks
Launch EC2
Create key pair
SSH into server
Install Nginx
Host webpage
Linux Commands
ssh
sudo
apt
yum
systemctl
Learn
cloud servers
Linux administration
security groups
Scenario 3 — Create IAM Users & Roles
Skills
IAM
Security
Tasks
Create IAM user
Create group
Attach policies
Create EC2 role
Learn
least privilege
access management
AWS authentication
Scenario 4 — Create RDS MySQL Database
Skills
RDS
SQL
Networking basics
Tasks
Launch MySQL RDS
Connect from EC2
Create tables
Insert records
SQL Practice

SELECT∗FROMusersWHEREage>25

Learn
managed databases
DB security
connectivity
Scenario 5 — Python Script Uploading Files to S3
Skills
Python
boto3
S3
Tasks
Install boto3
Upload files
Download files
List bucket objects
Learn
AWS SDK
automation
scripting
LEVEL 2 — Intermediate Hands-on Scenarios

Goal:
Build real application infrastructure.

Scenario 6 — Build Custom VPC Architecture
Skills
Networking
VPC
Routing
Architecture
VPC
├── Public Subnet
│   └── EC2
└── Private Subnet
    └── RDS
Tasks
Create VPC
Create subnets
Configure route tables
Configure Internet Gateway
Configure NAT
Learn
cloud networking
subnet isolation
secure architectures
Scenario 7 — Deploy Full Stack App on EC2
Stack
React frontend
Node backend
MySQL database
Skills
Linux
EC2
Nginx
PM2
Tasks
Deploy frontend
Deploy backend
Configure reverse proxy
Run app as service
Learn
application deployment
production setup
Scenario 8 — Dockerize Full Application
Skills
Docker
Containers
Tasks
Create Dockerfile
Build image
Run container
Create docker-compose
Architecture
Frontend Container
Backend Container
Database Container
Learn
containerization
environment consistency
Scenario 9 — Push Docker Images to ECR
Skills
Docker
ECR
Tasks
Create ECR repository
Authenticate Docker
Push image
Pull image
Learn
container registry
deployment workflows
Scenario 10 — Deploy Containers to ECS
Skills
ECS
Fargate
Tasks
Create ECS cluster
Create task definition
Deploy service
Configure load balancer
Learn
container orchestration
scalable deployments
Scenario 11 — Terraform AWS Infrastructure
Skills
Terraform
IaC
Tasks

Create:

VPC
Subnets
EC2
Security groups

using Terraform only.

Learn
infrastructure automation
reproducible deployments
Scenario 12 — CI/CD Pipeline
Skills
GitHub Actions
AWS deployment
Tasks
Push code to GitHub
Auto build Docker image
Deploy automatically to AWS
Learn
DevOps workflow
automation
LEVEL 3 — Advanced Hands-on Scenarios

Goal:
Think like production engineer.

Scenario 13 — Auto Scaling Web Application
Skills
Load Balancer
Auto Scaling
Tasks
Create launch template
Configure ASG
Configure ALB
Learn
high availability
scalability
Scenario 14 — Serverless REST API
Stack
API Gateway
Lambda
DynamoDB
Tasks
Create REST API
Create Lambda function
Store data in DynamoDB
Learn
serverless architecture
event-driven systems
Scenario 15 — Monitoring & Logging System
Skills
CloudWatch
Logging
Tasks
Configure logs
Create alarms
Monitor EC2 metrics
Learn
observability
monitoring
Scenario 16 — Event-driven File Processing
Flow
S3 Upload
→ Lambda Trigger
→ Process File
→ Store Metadata
Skills
S3 events
Lambda
Python
Learn
automation
event architecture
LEVEL 4 — Data Engineering Hands-on

Very important for your path.

Scenario 17 — Data Lake Project
Architecture
CSV Files
→ S3
→ Glue Catalog
→ Athena Queries
Skills
S3
Glue
Athena
Learn
data lakes
metadata cataloging
Scenario 18 — ETL Pipeline
Flow
Raw Data
→ Glue ETL
→ Clean Data
→ S3
→ Athena
Learn
ETL
transformations
Scenario 19 — Real-time Streaming Pipeline
Flow
Producer
→ Kinesis
→ Lambda
→ S3/Redshift
Learn
streaming systems
real-time analytics
Scenario 20 — Spark Processing on EMR
Skills
Spark
EMR
Tasks
Create EMR cluster
Run PySpark jobs
Process large datasets
Learn
distributed processing
big data systems
LEVEL 5 — Production-grade Projects
Scenario 21 — Netflix-style Architecture
Components
CloudFront
S3
ECS
RDS
Redis
Learn
scalable architecture
caching
CDN
Scenario 22 — Multi-environment Terraform Setup
Environments
dev
qa
prod
Learn
enterprise IaC
reusable modules
Scenario 23 — Kubernetes on EKS
Skills
Kubernetes
EKS
Tasks
Deploy pods
Services
Ingress
Autoscaling
Learn
advanced orchestration
Scenario 24 — Complete Data Platform
Architecture
Kafka/Kinesis
→ Spark
→ S3
→ Redshift
→ BI Dashboard
Learn
end-to-end data engineering
BEST WAY TO PRACTICE

For EVERY project:

Step 1

Create manually in AWS Console

Step 2

Repeat using AWS CLI

Step 3

Automate using Terraform

Step 4

Monitor using CloudWatch

Step 5

Document in GitHub

Your GitHub Should Contain

For every project:

README.md
Architecture Diagram
Terraform Files
Deployment Steps
Screenshots

This becomes your portfolio.

BEST PROJECT ORDER FOR YOU
Start Here
S3 static hosting
EC2 Linux server
RDS setup
Python boto3 automation
Then
VPC architecture
Dockerized app
ECS deployment
Terraform infrastructure
Then
Data lake
ETL pipeline
Kinesis streaming
Spark on EMR

That progression is excellent for your direction.