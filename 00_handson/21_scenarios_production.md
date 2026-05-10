# Level 5 — Production-Grade Scenarios

> **Goal**: Think and build like a senior cloud engineer.  
> **Prerequisites**: Completed Levels 1–4.

---

## Scenario 21 — Netflix-Style Scalable Architecture

**Skills**: CloudFront, S3, ECS, RDS, ElastiCache  
**Time**: 90 minutes

### Architecture
```
Users (Global)
      ↓
CloudFront (CDN — 400+ edge locations)
  ├── /static/* → S3 (React app, images, videos)
  └── /api/*    → ALB → ECS (Node.js API)
                              ↓
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ElastiCache          RDS Aurora
              (Redis cache)        (PostgreSQL)
              Session store        Persistent data
```

### Step-by-Step

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ── Step 1: S3 for static assets ──────────────────────────────────────────────
STATIC_BUCKET="${ACCOUNT_ID}-static-assets"
aws s3api create-bucket --bucket $STATIC_BUCKET --region $REGION
aws s3api put-public-access-block \
  --bucket $STATIC_BUCKET \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# ── Step 2: CloudFront with OAC ───────────────────────────────────────────────
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "s3-oac",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }' \
  --query 'OriginAccessControl.Id' --output text)

DIST_ID=$(aws cloudfront create-distribution \
  --distribution-config "{
    \"CallerReference\": \"netflix-style-$(date +%s)\",
    \"Comment\": \"Netflix-style CDN\",
    \"DefaultRootObject\": \"index.html\",
    \"Origins\": {
      \"Quantity\": 2,
      \"Items\": [
        {
          \"Id\": \"s3-static\",
          \"DomainName\": \"${STATIC_BUCKET}.s3.${REGION}.amazonaws.com\",
          \"S3OriginConfig\": {\"OriginAccessIdentity\": \"\"},
          \"OriginAccessControlId\": \"${OAC_ID}\"
        },
        {
          \"Id\": \"alb-api\",
          \"DomainName\": \"my-alb.${REGION}.elb.amazonaws.com\",
          \"CustomOriginConfig\": {
            \"HTTPPort\": 80,
            \"HTTPSPort\": 443,
            \"OriginProtocolPolicy\": \"http-only\"
          }
        }
      ]
    },
    \"DefaultCacheBehavior\": {
      \"TargetOriginId\": \"s3-static\",
      \"ViewerProtocolPolicy\": \"redirect-to-https\",
      \"CachePolicyId\": \"658327ea-f89d-4fab-a63d-7e88639e58f6\",
      \"Compress\": true,
      \"AllowedMethods\": {\"Quantity\": 2, \"Items\": [\"GET\", \"HEAD\"]}
    },
    \"CacheBehaviors\": {
      \"Quantity\": 1,
      \"Items\": [{
        \"PathPattern\": \"/api/*\",
        \"TargetOriginId\": \"alb-api\",
        \"ViewerProtocolPolicy\": \"https-only\",
        \"CachePolicyId\": \"4135ea2d-6df8-44a3-9df3-4b5a84be39ad\",
        \"AllowedMethods\": {\"Quantity\": 7, \"Items\": [\"GET\",\"HEAD\",\"OPTIONS\",\"PUT\",\"POST\",\"PATCH\",\"DELETE\"]}
      }]
    },
    \"CustomErrorResponses\": {
      \"Quantity\": 1,
      \"Items\": [{\"ErrorCode\": 403, \"ResponsePagePath\": \"/index.html\", \"ResponseCode\": \"200\", \"ErrorCachingMinTTL\": 0}]
    },
    \"Enabled\": true,
    \"HttpVersion\": \"http2and3\",
    \"PriceClass\": \"PriceClass_All\"
  }" \
  --query 'Distribution.Id' --output text)

CF_DOMAIN=$(aws cloudfront get-distribution \
  --id $DIST_ID \
  --query 'Distribution.DomainName' --output text)

echo "CloudFront: https://$CF_DOMAIN"

# ── Step 3: ElastiCache Redis ─────────────────────────────────────────────────
aws elasticache create-replication-group \
  --replication-group-id "app-cache" \
  --description "Application cache" \
  --engine redis \
  --engine-version "7.1" \
  --cache-node-type cache.t3.micro \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled

# ── Step 4: Aurora PostgreSQL ─────────────────────────────────────────────────
aws rds create-db-cluster \
  --db-cluster-identifier "app-aurora" \
  --engine aurora-postgresql \
  --engine-version "15.4" \
  --master-username dbadmin \
  --manage-master-user-password \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=8 \
  --storage-encrypted

aws rds create-db-instance \
  --db-instance-identifier "app-aurora-writer" \
  --db-cluster-identifier "app-aurora" \
  --db-instance-class db.serverless \
  --engine aurora-postgresql

echo "✅ Netflix-style architecture deployed!"
echo "CDN: https://$CF_DOMAIN"
```

### Application Code with Caching

```python
# app.py — Node.js-style Python API with Redis caching
import redis
import json
import os
import psycopg2
from functools import wraps

# Connections (initialized once, reused)
cache = redis.Redis(
    host=os.environ['REDIS_HOST'],
    port=6379, ssl=True, decode_responses=True
)

def get_db():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def cached(ttl=300):
    """Cache decorator — check Redis first, then DB."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            # Try cache
            result = cache.get(key)
            if result:
                print(f"Cache HIT: {key}")
                return json.loads(result)
            # Cache miss — query DB
            print(f"Cache MISS: {key}")
            result = func(*args, **kwargs)
            cache.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

@cached(ttl=300)
def get_products(category=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            if category:
                cur.execute("SELECT * FROM products WHERE category = %s", (category,))
            else:
                cur.execute("SELECT * FROM products LIMIT 100")
            return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

@cached(ttl=60)
def get_user_profile(user_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(zip([d[0] for d in cur.description], row)) if row else None
```

### What You Learned
- ✅ CloudFront for global CDN
- ✅ Multi-origin CloudFront (S3 + ALB)
- ✅ ElastiCache for application caching
- ✅ Aurora Serverless v2 for variable workloads
- ✅ Cache-aside pattern

---

## Scenario 22 — Multi-Environment Terraform Setup

**Skills**: Terraform modules, workspaces, environments  
**Time**: 60 minutes

```
terraform/
├── modules/
│   ├── vpc/
│   ├── ec2/
│   └── rds/
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
└── main.tf
```

```hcl
# modules/vpc/main.tf
variable "environment" {}
variable "vpc_cidr"    { default = "10.0.0.0/16" }

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = { Name = "${var.environment}-vpc", Environment = var.environment }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${var.environment}-public-${count.index + 1}" }
}

data "aws_availability_zones" "available" { state = "available" }

output "vpc_id"         { value = aws_vpc.main.id }
output "public_subnets" { value = aws_subnet.public[*].id }
```

```hcl
# main.tf — uses modules
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

variable "environment"    {}
variable "instance_type"  { default = "t3.micro" }
variable "db_instance"    { default = "db.t3.micro" }

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { Environment = var.environment, ManagedBy = "Terraform" }
  }
}

module "vpc" {
  source      = "./modules/vpc"
  environment = var.environment
}

module "ec2" {
  source        = "./modules/ec2"
  environment   = var.environment
  instance_type = var.instance_type
  subnet_ids    = module.vpc.public_subnets
  vpc_id        = module.vpc.vpc_id
}

module "rds" {
  source        = "./modules/rds"
  environment   = var.environment
  instance_class = var.db_instance
  subnet_ids    = module.vpc.public_subnets
  vpc_id        = module.vpc.vpc_id
}
```

```hcl
# environments/dev.tfvars
environment   = "dev"
instance_type = "t3.micro"
db_instance   = "db.t3.micro"

# environments/prod.tfvars
environment   = "prod"
instance_type = "t3.medium"
db_instance   = "db.r6g.large"
```

```bash
# Deploy to different environments
# Dev
terraform workspace new dev
terraform apply -var-file="environments/dev.tfvars"

# Staging
terraform workspace new staging
terraform apply -var-file="environments/staging.tfvars"

# Production
terraform workspace new prod
terraform apply -var-file="environments/prod.tfvars"

# List workspaces
terraform workspace list

# Switch environment
terraform workspace select dev
```

### What You Learned
- ✅ Terraform modules for reusability
- ✅ Workspaces for environment isolation
- ✅ Variable files per environment
- ✅ Remote state in S3

---

## Scenario 23 — Kubernetes on EKS

**Skills**: EKS, kubectl, Helm, HPA  
**Time**: 60 minutes

```bash
# Step 1: Create EKS cluster
eksctl create cluster \
  --name production-cluster \
  --region us-east-1 \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --with-oidc \
  --zones us-east-1a,us-east-1b,us-east-1c

# Step 2: Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=production-cluster

# Step 3: Deploy application
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: webapp
    spec:
      containers:
        - name: webapp
          image: nginx:alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "200m"
              memory: "128Mi"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: webapp-service
spec:
  selector:
    app: webapp
  ports:
    - port: 80
      targetPort: 80
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
EOF

# Step 4: Monitor
kubectl get pods -w
kubectl get svc webapp-service
kubectl get hpa webapp-hpa

# Step 5: Rolling update (zero downtime)
kubectl set image deployment/webapp webapp=nginx:1.25
kubectl rollout status deployment/webapp

# Rollback if needed
kubectl rollout undo deployment/webapp
```

### What You Learned
- ✅ EKS cluster creation with eksctl
- ✅ Kubernetes Deployments, Services, HPA
- ✅ Rolling updates with zero downtime
- ✅ Horizontal Pod Autoscaler

---

## Scenario 24 — Complete Data Platform

**Skills**: All data engineering services  
**Time**: 2–3 hours

### Architecture
```
Data Sources
  ├── Application DB (RDS) → Kinesis (CDC)
  ├── API Events → Kinesis Data Streams
  └── Batch Files → S3 (raw)
          ↓
  Kinesis Firehose → S3 (bronze layer)
          ↓
  Glue ETL → S3 (silver layer, Parquet)
          ↓
  Redshift (gold layer, analytics)
          ↓
  QuickSight / Athena (dashboards + ad-hoc)

Orchestration: Step Functions (daily ETL)
Monitoring:    CloudWatch + SNS alerts
```

```bash
# Step 1: Create Redshift cluster
aws redshift create-cluster \
  --cluster-identifier "analytics-cluster" \
  --node-type ra3.xlplus \
  --number-of-nodes 2 \
  --master-username admin \
  --master-user-password "SecurePass123!" \
  --db-name analytics \
  --cluster-subnet-group-name my-subnet-group \
  --vpc-security-group-ids $SG_DB \
  --encrypted

# Step 2: Create Kinesis Firehose → S3
aws firehose create-delivery-stream \
  --delivery-stream-name "events-to-s3" \
  --extended-s3-destination-configuration "{
    \"RoleARN\": \"arn:aws:iam::${ACCOUNT_ID}:role/firehose-role\",
    \"BucketARN\": \"arn:aws:s3:::${BUCKET}\",
    \"Prefix\": \"bronze/events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/\",
    \"BufferingHints\": {\"SizeInMBs\": 128, \"IntervalInSeconds\": 300},
    \"CompressionFormat\": \"GZIP\"
  }"

# Step 3: Step Functions for daily ETL orchestration
aws stepfunctions create-state-machine \
  --name "daily-etl" \
  --definition '{
    "StartAt": "ExtractFromSources",
    "States": {
      "ExtractFromSources": {
        "Type": "Parallel",
        "Branches": [
          {"StartAt": "ExtractDB", "States": {"ExtractDB": {"Type": "Task", "Resource": "arn:aws:lambda:::function:extract-db", "End": true}}},
          {"StartAt": "ExtractAPI", "States": {"ExtractAPI": {"Type": "Task", "Resource": "arn:aws:lambda:::function:extract-api", "End": true}}}
        ],
        "Next": "RunGlueETL"
      },
      "RunGlueETL": {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": {"JobName": "transactions-etl"},
        "Next": "LoadToRedshift"
      },
      "LoadToRedshift": {
        "Type": "Task",
        "Resource": "arn:aws:states:::redshift-data:executeStatement.sync",
        "Parameters": {
          "ClusterIdentifier": "analytics-cluster",
          "Database": "analytics",
          "Sql": "COPY transactions FROM '\''s3://bucket/silver/transactions/'\'' IAM_ROLE '\''arn:aws:iam::123456789:role/RedshiftRole'\'' FORMAT AS PARQUET"
        },
        "Next": "NotifySuccess"
      },
      "NotifySuccess": {
        "Type": "Task",
        "Resource": "arn:aws:states:::sns:publish",
        "Parameters": {
          "TopicArn": "arn:aws:sns:us-east-1:123456789:data-team",
          "Message": "Daily ETL complete!"
        },
        "End": true
      }
    }
  }' \
  --role-arn arn:aws:iam::${ACCOUNT_ID}:role/StepFunctionsRole

# Schedule daily at 2 AM
aws events put-rule \
  --name "daily-etl-trigger" \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

echo "✅ Complete data platform deployed!"
```

### What You Learned
- ✅ End-to-end data platform architecture
- ✅ Kinesis Firehose for streaming ingestion
- ✅ Redshift for analytics warehouse
- ✅ Step Functions for ETL orchestration
- ✅ Production-grade data engineering

---

## Summary — All 24 Scenarios Complete! 🎉

| Level | Scenarios | Key Skills |
|-------|---------|-----------|
| Beginner (1–5) | S3, EC2, IAM, RDS, Python | Cloud basics, Linux, SQL |
| Intermediate (6–12) | VPC, Docker, ECS, Terraform, CI/CD | Networking, containers, IaC |
| Advanced (13–16) | ALB+ASG, Lambda, CloudWatch, Events | Scalability, serverless, monitoring |
| Data Engineering (17–20) | Glue, Athena, Kinesis, EMR | Data pipelines, streaming, Spark |
| Production (21–24) | CloudFront, EKS, multi-env, data platform | Enterprise architecture |

---

## Your GitHub Portfolio Should Have

```
aws-projects/
├── 01-static-website/          README + S3 config
├── 02-ec2-web-server/          README + user data script
├── 03-custom-vpc/              README + Terraform
├── 04-fullstack-app/           README + Docker + deploy script
├── 05-serverless-api/          README + Lambda + SAM template
├── 06-auto-scaling/            README + Terraform
├── 07-data-lake/               README + Glue + Athena queries
├── 08-streaming-pipeline/      README + Kinesis + Lambda
└── 09-complete-platform/       README + architecture diagram
```

**Each project README should have**:
- Architecture diagram
- What it does
- Services used
- How to deploy
- Cost estimate
- Lessons learned

*This is your engineering portfolio — not just knowledge.*
