# 🗺️ AWS Learning Roadmap — Hands-On Engineer's Guide

> **Philosophy**: Don't memorize services. Learn how to BUILD systems using AWS.  
> **Approach**: For every service → Understand → Console → CLI → IaC → Production Thinking

---

## 📋 Table of Contents

1. [Why This Roadmap](#why-this-roadmap)
2. [Companion Skills](#companion-skills-learn-alongside-aws)
3. [Phase-by-Phase Learning Path](#phase-by-phase-learning-path)
4. [Recommended Service Order](#recommended-service-order)
5. [AWS Domains Overview](#aws-domains-overview)
6. [80/20 Rule — What Actually Matters](#8020-rule)
7. [Hands-On Scenario Index](#hands-on-scenario-index)
8. [Daily Practice Routine](#daily-practice-routine)
9. [Certifications Guide](#certifications)
10. [Portfolio Building](#portfolio-building)

---

## Why This Roadmap

```
❌ Wrong approach:
   Watch videos → memorize services → take certification → apply for jobs

✅ Right approach:
   Break things → debug issues → read AWS docs → build mini-projects → understand architecture
```

**The 5-Step Method for Every AWS Service:**

```
Step 1 — UNDERSTAND
  What problem does it solve?
  Why did AWS create it?
  When should you use it?

Step 2 — CONSOLE
  Create it manually in AWS Console
  Explore every setting

Step 3 — CLI
  Do the same using AWS CLI
  Understand the API behind the UI

Step 4 — IaC
  Automate using Terraform or CloudFormation
  Make it reproducible

Step 5 — PRODUCTION THINKING
  Is it scalable?
  Is it secure?
  Is it highly available?
  Is it cost optimized?
```

---

## Companion Skills (Learn Alongside AWS)

> These skills matter MORE than memorizing AWS services.

### 1. Linux 🐧

Most AWS servers run Linux. Without Linux, EC2 is just a black box.

```bash
# Essential Linux commands for cloud engineers

# File system
ls -la          # List files with permissions
pwd             # Current directory
cd /var/log     # Change directory
mkdir -p a/b/c  # Create nested directories
rm -rf dir/     # Delete directory
cp -r src/ dst/ # Copy directory
mv old new      # Move/rename

# File content
cat file.txt    # View file
less file.txt   # Page through file
grep "error" /var/log/syslog  # Search in file
tail -f /var/log/nginx/access.log  # Live log stream
head -n 20 file.txt  # First 20 lines

# Permissions
chmod 755 script.sh   # rwxr-xr-x
chown ubuntu:ubuntu file  # Change owner
sudo command          # Run as root

# Process management
ps aux              # List all processes
top / htop          # Live process monitor
kill -9 PID         # Force kill process
systemctl start nginx   # Start service
systemctl enable nginx  # Auto-start on boot
systemctl status nginx  # Check service status

# Networking
curl -I https://example.com  # HTTP headers
wget https://example.com/file  # Download file
ping google.com              # Test connectivity
netstat -tlnp                # Open ports
ss -tlnp                     # Modern netstat
nslookup example.com         # DNS lookup
dig example.com              # Detailed DNS

# Disk & Memory
df -h           # Disk usage
du -sh /var/*   # Directory sizes
free -m         # Memory usage

# SSH
ssh -i key.pem ubuntu@1.2.3.4  # Connect to server
scp file.txt ubuntu@1.2.3.4:/home/ubuntu/  # Copy file to server

# Package management
sudo apt update && sudo apt install nginx -y  # Ubuntu/Debian
sudo yum install nginx -y                     # Amazon Linux/RHEL

# Logs
journalctl -u nginx -f  # Service logs
tail -f /var/log/syslog # System logs
```

**Hands-on**: Launch EC2 → SSH in → install Nginx → host a webpage → check logs.

---

### 2. Networking 🌐

Networking is the backbone of cloud. Most AWS beginners struggle here.

```
Core Concepts to Master:

IP Addressing:
  Public IP:   Reachable from internet (e.g., 54.123.45.67)
  Private IP:  Internal only (e.g., 10.0.1.50, 192.168.x.x)
  CIDR:        10.0.0.0/16 = 65,536 addresses
               10.0.1.0/24 = 256 addresses

Protocols:
  HTTP:  Port 80  (web traffic, unencrypted)
  HTTPS: Port 443 (web traffic, encrypted)
  SSH:   Port 22  (server access)
  MySQL: Port 3306
  PostgreSQL: Port 5432
  Redis: Port 6379

The Request Flow (CRITICAL for interviews):
  Browser → DNS (Route 53) → Load Balancer → EC2 → RDS
     ↑                           ↑
  Resolves domain            Distributes traffic
  to IP address              across instances

VPC Components:
  VPC:              Your private network in AWS
  Subnet:           Segment of VPC (public or private)
  Route Table:      Rules for where traffic goes
  Internet Gateway: Connects VPC to internet
  NAT Gateway:      Private subnet → internet (outbound only)
  Security Group:   Firewall at instance level (stateful)
  NACL:             Firewall at subnet level (stateless)
```

---

### 3. Docker 🐳

Modern cloud = containers. Docker is mandatory.

```dockerfile
# Dockerfile — the blueprint for your container
FROM node:20-alpine          # Base image
WORKDIR /app                 # Working directory
COPY package*.json ./        # Copy dependency files
RUN npm ci                   # Install dependencies
COPY . .                     # Copy source code
EXPOSE 3000                  # Document port
CMD ["node", "server.js"]    # Start command
```

```bash
# Essential Docker commands
docker build -t myapp:v1 .          # Build image
docker run -d -p 3000:3000 myapp:v1 # Run container
docker ps                           # List running containers
docker logs container-id            # View logs
docker exec -it container-id sh     # Shell into container
docker stop container-id            # Stop container
docker images                       # List images
docker-compose up -d                # Start multi-container app
docker-compose down                 # Stop everything
```

---

### 4. Git & GitHub 📁

Every cloud engineer uses Git daily.

```bash
# Daily Git workflow
git init                    # Initialize repo
git clone <url>             # Clone repo
git status                  # What changed?
git add .                   # Stage all changes
git commit -m "feat: add S3 upload"  # Commit
git push origin main        # Push to GitHub
git pull                    # Get latest changes

# Branching
git checkout -b feature/s3-upload  # Create branch
git merge feature/s3-upload        # Merge branch
git log --oneline                  # Commit history

# Good commit message format:
# feat: add new feature
# fix: bug fix
# docs: documentation
# refactor: code cleanup
# chore: maintenance
```

---

### 5. Terraform 🏗️

Infrastructure as Code — automate everything.

```hcl
# main.tf — create EC2 instance
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  tags = { Name = "web-server" }
}

output "public_ip" {
  value = aws_instance.web.public_ip
}
```

```bash
terraform init     # Download providers
terraform plan     # Preview changes
terraform apply    # Create resources
terraform destroy  # Delete everything
```

---

### 6. Python 🐍

Python is the glue language of cloud and data engineering.

```python
# boto3 — AWS SDK for Python
import boto3

# S3 operations
s3 = boto3.client('s3')
s3.upload_file('local.txt', 'my-bucket', 'remote.txt')
s3.download_file('my-bucket', 'remote.txt', 'local.txt')

# EC2 operations
ec2 = boto3.resource('ec2')
instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
)
for i in instances:
    print(i.id, i.instance_type, i.public_ip_address)

# Lambda function structure
def handler(event, context):
    print(f"Event: {event}")
    return {'statusCode': 200, 'body': 'OK'}
```

---

### 7. SQL 🗄️

Data engineering is impossible without SQL.

```sql
-- Core queries
SELECT name, age FROM users WHERE age > 25 ORDER BY age DESC;

-- Aggregations
SELECT country, COUNT(*) as users, AVG(age) as avg_age
FROM users GROUP BY country HAVING COUNT(*) > 100;

-- Joins
SELECT o.id, u.name, o.total
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'completed';

-- Window functions (asked in every DE interview)
SELECT
    user_id,
    amount,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY created_at) AS running_total,
    RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) AS rank
FROM transactions;

-- CTE
WITH monthly_revenue AS (
    SELECT DATE_TRUNC('month', created_at) AS month, SUM(amount) AS revenue
    FROM orders GROUP BY 1
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_month
FROM monthly_revenue;
```

---

## Phase-by-Phase Learning Path

### Phase 1 — AWS Foundations (Weeks 1–2)
**Goal**: Understand how AWS works internally.

| Service | Why Learn First |
|---------|----------------|
| IAM | Everything in AWS requires permissions |
| Regions & AZs | Understand the global infrastructure |
| EC2 | The foundation of cloud compute |
| S3 | The foundation of cloud storage |
| VPC basics | Your private network |
| CloudWatch | Monitor everything |
| Billing | Avoid surprise bills |

**Hands-on**:
- Create EC2 instance, SSH in, install Nginx
- Host static website in S3
- Create IAM users/roles with least privilege
- Monitor EC2 CPU with CloudWatch alarm

---

### Phase 2 — Networking + Security (Weeks 3–4)
**Goal**: Build secure, isolated architectures.

> ⚠️ Most beginners skip this. This phase makes you different.

| Topic | What to Learn |
|-------|--------------|
| VPC | Custom VPC from scratch |
| Subnets | Public vs private, CIDR planning |
| Route Tables | How traffic flows |
| Internet Gateway | Public internet access |
| NAT Gateway | Private subnet internet access |
| Security Groups | Instance-level firewall |
| NACL | Subnet-level firewall |
| IAM deep dive | Policies, roles, conditions |

**Hands-on Project**: 3-tier VPC
```
Internet → ALB (public subnet)
              ↓
         EC2 (private subnet)
              ↓
         RDS (isolated subnet)
```

---

### Phase 3 — Compute + Storage (Weeks 5–6)

| Category | Services |
|----------|---------|
| Compute | EC2, Auto Scaling, ALB, Lambda, ECS, ECR |
| Storage | S3, EBS, EFS, Glacier |

**Hands-on**:
- Deploy React app on EC2 behind ALB
- Configure Auto Scaling (scale on CPU)
- Build serverless API: Lambda + API Gateway
- Dockerize app → push to ECR → deploy on ECS

---

### Phase 4 — Databases (Weeks 7–8)

| Service | Use Case |
|---------|---------|
| RDS | Relational (MySQL, PostgreSQL) |
| DynamoDB | NoSQL, serverless |
| Aurora | High-performance relational |
| ElastiCache | Caching (Redis) |
| Redshift | Data warehouse |

**Hands-on**:
- Host MySQL in RDS, connect from EC2
- Build DynamoDB CRUD API with Lambda
- Load CSV into Redshift, query with SQL

---

### Phase 5 — DevOps + CI/CD (Weeks 9–10)

| Tool | Purpose |
|------|---------|
| CodePipeline | Orchestrate CI/CD |
| CodeBuild | Build and test |
| CodeDeploy | Deploy to EC2/ECS |
| CloudFormation | AWS-native IaC |
| Terraform | Multi-cloud IaC |
| GitHub Actions | CI/CD with GitHub |

**Hands-on**:
- CI/CD pipeline: GitHub push → build → test → deploy to ECS
- Terraform: provision VPC + EC2 + RDS from code

---

### Phase 6 — Data Engineering Path (Weeks 11–14)

| Service | Purpose |
|---------|---------|
| Glue | Serverless ETL |
| Athena | SQL on S3 |
| EMR | Managed Spark/Hadoop |
| Kinesis | Real-time streaming |
| Redshift | Data warehouse |
| Lake Formation | Data lake governance |
| Step Functions | Workflow orchestration |
| EventBridge | Event routing |

**Hands-on Projects**:
- CSV → S3 → Glue → Athena pipeline
- Real-time streaming: Kinesis → Lambda → S3
- Data lake architecture
- ETL pipeline with Glue
- Airflow on AWS (MWAA)

---

### Phase 7 — Real Projects (Ongoing)

| Level | Projects |
|-------|---------|
| Beginner | Static website, URL shortener, file upload API |
| Intermediate | Full-stack deployment, serverless REST API, CI/CD pipeline |
| Advanced | Netflix-style architecture, event-driven microservices, data lake |

---

## Recommended Service Order

```
1.  IAM              ← Security foundation
2.  EC2              ← Compute foundation
3.  S3               ← Storage foundation
4.  VPC              ← Network foundation
5.  RDS              ← Database
6.  Lambda           ← Serverless
7.  CloudWatch       ← Monitoring
8.  Load Balancer    ← Traffic distribution
9.  Auto Scaling     ← Scalability
10. Docker           ← Containerization
11. ECS/EKS          ← Container orchestration
12. Terraform        ← Infrastructure as Code
13. Glue/Kinesis/Redshift ← Data engineering
```

---

## AWS Domains Overview

| Domain | Key Services | Your Priority |
|--------|-------------|--------------|
| Compute | EC2, Lambda, ECS, EKS, Fargate | 🔴 High |
| Storage | S3, EBS, EFS, Glacier | 🔴 High |
| Databases | RDS, DynamoDB, Aurora, Redshift, ElastiCache | 🔴 High |
| Networking | VPC, Route53, CloudFront, API Gateway, ELB | 🔴 High |
| Security | IAM, Cognito, KMS, Secrets Manager, WAF, GuardDuty | 🔴 High |
| Monitoring | CloudWatch, CloudTrail, X-Ray, Config | 🟡 Medium |
| DevOps | CloudFormation, CodePipeline, CodeBuild, Systems Manager | 🟡 Medium |
| Containers | ECS, EKS, Fargate, ECR | 🟡 Medium |
| Analytics | Glue, Athena, EMR, Kinesis, Redshift, QuickSight | 🔴 High (for DE) |
| AI/ML | SageMaker, Bedrock, Rekognition | 🟢 Optional |

---

## 80/20 Rule

> You can build MOST production systems using only these 10 services:

```
EC2          → Compute
S3           → Storage
RDS          → Database
IAM          → Security
VPC          → Networking
Lambda       → Serverless
CloudWatch   → Monitoring
Load Balancer → Traffic
ECS          → Containers
Route53      → DNS
```

---

## Hands-On Scenario Index

| # | Scenario | Level | File |
|---|---------|-------|------|
| 1 | Host static website in S3 | Beginner | `17_scenarios_beginner.md` |
| 2 | Launch Linux server in EC2 | Beginner | `17_scenarios_beginner.md` |
| 3 | Create IAM users & roles | Beginner | `17_scenarios_beginner.md` |
| 4 | Create RDS MySQL database | Beginner | `17_scenarios_beginner.md` |
| 5 | Python script uploading to S3 | Beginner | `17_scenarios_beginner.md` |
| 6 | Build custom VPC architecture | Intermediate | `18_scenarios_intermediate.md` |
| 7 | Deploy full-stack app on EC2 | Intermediate | `18_scenarios_intermediate.md` |
| 8 | Dockerize full application | Intermediate | `18_scenarios_intermediate.md` |
| 9 | Push Docker images to ECR | Intermediate | `18_scenarios_intermediate.md` |
| 10 | Deploy containers to ECS | Intermediate | `18_scenarios_intermediate.md` |
| 11 | Terraform AWS infrastructure | Intermediate | `18_scenarios_intermediate.md` |
| 12 | CI/CD pipeline | Intermediate | `18_scenarios_intermediate.md` |
| 13 | Auto Scaling web application | Advanced | `19_scenarios_advanced.md` |
| 14 | Serverless REST API | Advanced | `19_scenarios_advanced.md` |
| 15 | Monitoring & logging system | Advanced | `19_scenarios_advanced.md` |
| 16 | Event-driven file processing | Advanced | `19_scenarios_advanced.md` |
| 17 | Data lake project | Data Eng | `20_scenarios_data_engineering.md` |
| 18 | ETL pipeline | Data Eng | `20_scenarios_data_engineering.md` |
| 19 | Real-time streaming pipeline | Data Eng | `20_scenarios_data_engineering.md` |
| 20 | Spark processing on EMR | Data Eng | `20_scenarios_data_engineering.md` |
| 21 | Netflix-style architecture | Production | `21_scenarios_production.md` |
| 22 | Multi-environment Terraform | Production | `21_scenarios_production.md` |
| 23 | Kubernetes on EKS | Production | `21_scenarios_production.md` |
| 24 | Complete data platform | Production | `21_scenarios_production.md` |

---

## Daily Practice Routine

```
Every Day:
  ⏰ 1 hour   — Learn (read docs, watch 1 video)
  ⏰ 2 hours  — Hands-on (build something)
  ⏰ 30 mins  — Document (write notes, push to GitHub)

Every Week:
  Complete 1 scenario from this guide
  Push code + README to GitHub
  Draw architecture diagram

Every Month:
  Complete 1 full project
  Write a blog post or LinkedIn article
  Review AWS billing and optimize
```

---

## Portfolio Building

> Every project should have these in GitHub:

```
project-name/
├── README.md              ← What it does, architecture, how to run
├── architecture.png       ← Diagram (draw.io, Lucidchart, or ASCII)
├── terraform/             ← Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── src/                   ← Application code
├── Dockerfile             ← If containerized
├── .github/workflows/     ← CI/CD pipeline
│   └── deploy.yml
└── docs/
    └── deployment.md      ← Step-by-step deployment guide
```

**Resume bullet point formula**:
```
[Action verb] + [Technology] + [What you built] + [Result/Scale]

Example:
"Deployed containerized React app to Amazon EKS using Docker and ECR,
 reducing deployment time from 30 minutes to 5 minutes via CI/CD pipeline"
```

---

## Certifications

> Don't do certifications first without projects.

| Certification | When to Take | Focus |
|--------------|-------------|-------|
| AWS Cloud Practitioner | After Phase 1-2 | Cloud concepts, basic services |
| AWS Solutions Architect Associate | After Phase 1-5 | Architecture, all core services |
| AWS Data Engineer Associate | After Phase 6 | Glue, Kinesis, Redshift, EMR |
| AWS Developer Associate | After Phase 3-5 | Lambda, DynamoDB, CI/CD |

---

## Your Best Long-Term Stack

```
Python          → Scripting, Lambda, data processing
Data Engineering → Spark, Airflow, Kafka/Kinesis
AWS             → Cloud infrastructure
Terraform       → Infrastructure as Code
Docker          → Containerization
SQL             → Data querying and modeling
Linux           → Server administration

This combination = strong market demand for:
  ✅ Cloud Engineer
  ✅ DevOps Engineer
  ✅ Data Engineer
  ✅ Platform Engineer
```

---

*Start with Scenario 1 → work through all 24 → you'll be production-ready.*
