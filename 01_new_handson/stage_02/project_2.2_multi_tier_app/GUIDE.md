# Project 2.2 — 3-Tier AWS Application Architecture

> Stage 02 | Multi-Tier Architecture | AWS CLI + Console | No Terraform

---

## 1. Project Overview

**Title:** 3-Tier AWS Application Architecture

**Problem:** A single EC2 instance is a single point of failure with no tier separation — all application logic, web serving, and database operations share the same server, the same network segment, and the same blast radius.

**Objectives:**
- Deploy three isolated tiers: Web (public), App (private), Database (private DB subnet)
- Chain security groups so traffic flows only in one direction: ALB → Web → App → DB
- Use an Application Load Balancer for horizontal scalability and health checks
- Deploy RDS MySQL in a DB subnet group for managed database operations
- Practice the principle of least privilege across all security boundaries

**Key Concepts:** Security group chaining, ALB target groups, health checks, RDS subnet groups, tier isolation, stateful vs stateless firewalling

**Depends on:** Project 2.1 (custom VPC with public and private subnets)

---

## 2. Architecture

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Route 53 (optional DNS)                                                 │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────────┐
│  VPC: handson-vpc (10.0.0.0/16)                                          │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  PUBLIC SUBNETS (10.0.1.0/24 us-east-1a, 10.0.3.0/24 us-east-1b) │  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────┐                     │  │
│  │  │  Application Load Balancer (alb-sg)      │                     │  │
│  │  │  Listener: HTTP :80                      │                     │  │
│  │  │  Target Group: web-tg (port 80)          │                     │  │
│  │  └──────────────────┬───────────────────────┘                     │  │
│  │                     │ port 80                                      │  │
│  │  ┌──────────────────▼───────────────────────┐                     │  │
│  │  │  Web EC2 (web-sg)                        │                     │  │
│  │  │  Allows: HTTP :80 from alb-sg only       │                     │  │
│  │  └──────────────────┬───────────────────────┘                     │  │
│  └─────────────────────┼──────────────────────────────────────────────┘  │
│                        │ port 8080                                        │
│  ┌─────────────────────┼──────────────────────────────────────────────┐  │
│  │  PRIVATE APP SUBNETS│(10.0.2.0/24 us-east-1a)                     │  │
│  │                     │                                              │  │
│  │  ┌──────────────────▼───────────────────────┐                     │  │
│  │  │  App EC2 (app-sg)                        │                     │  │
│  │  │  Allows: TCP :8080 from web-sg only      │                     │  │
│  │  └──────────────────┬───────────────────────┘                     │  │
│  └─────────────────────┼──────────────────────────────────────────────┘  │
│                        │ port 3306                                        │
│  ┌─────────────────────┼──────────────────────────────────────────────┐  │
│  │  PRIVATE DB SUBNETS │(10.0.4.0/24, 10.0.5.0/24 multi-AZ)         │  │
│  │                     │                                              │  │
│  │  ┌──────────────────▼───────────────────────┐                     │  │
│  │  │  RDS MySQL (db-sg)                       │                     │  │
│  │  │  Allows: MySQL :3306 from app-sg only    │                     │  │
│  │  └──────────────────────────────────────────┘                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

Security Group Chain:
  Internet → alb-sg (80) → web-sg (80 from alb-sg) → app-sg (8080 from web-sg) → db-sg (3306 from app-sg)
```

---

## 3. Prerequisites

- **Complete Project 2.1 first** — this project uses the custom VPC (`handson-vpc`, `10.0.0.0/16`)
- IAM permissions needed:
  - `ec2:*` (instances, security groups, subnets)
  - `elasticloadbalancing:*` (ALB, target groups, listeners)
  - `rds:*` (DB instances, subnet groups, parameter groups)
- AWS CLI v2 configured with `us-east-1` as default region
- Key pair available in us-east-1
- VPC ID from Project 2.1 (run: `aws ec2 describe-vpcs --filters "Name=tag:Name,Values=handson-vpc" --query 'Vpcs[0].VpcId' --output text`)
- Understanding of HTTP/TCP ports and three-tier application design

**Prerequisites Check:**
```bash
# Confirm VPC exists from Project 2.1
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=handson-vpc" \
  --query 'Vpcs[0].VpcId' --output text)
echo "VPC: $VPC_ID"

# Confirm subnets exist
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].{Name:Tags[?Key==`Name`].Value|[0],CIDR:CidrBlock,AZ:AvailabilityZone}' \
  --output table

# Check ELB permissions
aws elbv2 describe-load-balancers --query 'LoadBalancers[0]' 2>&1 | head -3
```

---

## 4. Folder Structure

```
project_2.2_multi_tier_app/
├── GUIDE.md                  # This file — full implementation guide
├── steps_awsconsoleui.md     # Console UI step-by-step with screenshots
├── cost_estimate.md          # Cost breakdown and free tier analysis
└── README.md                 # Quick reference
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method

#### Prerequisites Check
Before starting in the console:
- [ ] VPC `handson-vpc` is visible in VPC Dashboard
- [ ] Public subnet `public-subnet-1a` exists
- [ ] Private subnet `private-subnet-1b` exists
- [ ] You're in region `us-east-1`

---

#### Decision Point 1 — ALB vs NLB

| Feature | ALB (Application LB) | NLB (Network LB) |
|---------|----------------------|-------------------|
| Protocol | HTTP, HTTPS, WebSocket | TCP, UDP, TLS |
| Routing | Path-based, host-based, header-based | IP + port only |
| Health checks | HTTP response code aware | TCP connection based |
| Use case | ✅ Web applications, APIs | Raw TCP, gaming, IoT |
| Cost | $0.008/LCU-hr + fixed | Similar |

**Use ALB** for this 3-tier web application — it understands HTTP and provides rich routing rules.

---

#### Step-by-Step: Security Groups

**Create ALB Security Group (`alb-sg`):**
1. EC2 → Security Groups → Create security group
2. Name: `alb-sg`, Description: `ALB — allow HTTP from internet`
3. VPC: `handson-vpc`
4. Inbound rules: HTTP (80) from `0.0.0.0/0`
5. Outbound: All traffic (default)
6. Create

**Create Web Security Group (`web-sg`):**
1. Create security group, Name: `web-sg`, VPC: `handson-vpc`
2. Inbound: HTTP (80) from **Security Group** → select `alb-sg`
3. Inbound: SSH (22) from your IP (for admin access)
4. Create

**Create App Security Group (`app-sg`):**
1. Create security group, Name: `app-sg`, VPC: `handson-vpc`
2. Inbound: Custom TCP (8080) from **Security Group** → select `web-sg`
3. Create

**Create DB Security Group (`db-sg`):**
1. Create security group, Name: `db-sg`, VPC: `handson-vpc`
2. Inbound: MySQL/Aurora (3306) from **Security Group** → select `app-sg`
3. Create

---

#### Step-by-Step: DB Subnets and RDS Subnet Group

RDS requires at least 2 subnets in different AZs for a subnet group.

**Create 2nd public subnet for ALB** (ALB needs 2 AZs):
1. VPC → Subnets → Create subnet
2. VPC: `handson-vpc`, Name: `public-subnet-1b`, AZ: `us-east-1b`, CIDR: `10.0.3.0/24`

**Create DB subnet 1:**
1. VPC → Subnets → Create subnet
2. VPC: `handson-vpc`, Name: `db-subnet-1a`, AZ: `us-east-1a`, CIDR: `10.0.4.0/24`

**Create DB subnet 2:**
1. VPC → Subnets → Create subnet
2. VPC: `handson-vpc`, Name: `db-subnet-1b`, AZ: `us-east-1b`, CIDR: `10.0.5.0/24`

**Create RDS DB Subnet Group:**
1. RDS → Subnet groups → Create DB subnet group
2. Name: `handson-db-subnet-group`
3. VPC: `handson-vpc`
4. Add subnets: `db-subnet-1a` and `db-subnet-1b`
5. Create

---

#### Step-by-Step: Launch EC2 Instances

**Web EC2:**
1. EC2 → Launch Instance
2. Name: `web-server`, AMI: Amazon Linux 2023, Type: `t2.micro`
3. Key pair: your key
4. Network: `handson-vpc`, Subnet: `public-subnet-1a`
5. Auto-assign public IP: Enable
6. Security group: `web-sg`
7. User data (optional):
   ```bash
   #!/bin/bash
   yum update -y
   yum install -y httpd
   systemctl start httpd
   echo "<h1>Web Tier — $(hostname)</h1>" > /var/www/html/index.html
   ```
8. Launch

**App EC2:**
1. EC2 → Launch Instance
2. Name: `app-server`, AMI: Amazon Linux 2023, Type: `t2.micro`
3. Key pair: your key
4. Network: `handson-vpc`, Subnet: `private-subnet-1b`
5. Auto-assign public IP: Disable
6. Security group: `app-sg`
7. Launch

---

#### Step-by-Step: Create ALB and Target Group

**Create Target Group:**
1. EC2 → Target Groups → Create target group
2. Type: Instances
3. Name: `web-tg`, Protocol: HTTP, Port: 80
4. VPC: `handson-vpc`
5. Health check: HTTP, path `/`, threshold 2 healthy / 3 unhealthy
6. Register targets: add `web-server` instance
7. Create

**Create ALB:**
1. EC2 → Load Balancers → Create Load Balancer
2. Choose **Application Load Balancer**
3. Name: `handson-alb`, Scheme: Internet-facing
4. VPC: `handson-vpc`
5. Subnets: select `public-subnet-1a` AND `public-subnet-1b` (must have 2 AZs)
6. Security group: `alb-sg`
7. Listener: HTTP :80 → Forward to `web-tg`
8. Create

Wait ~2 minutes for ALB to become **Active**.

#### Expected Outcome
- ALB DNS name (e.g., `handson-alb-xxxx.us-east-1.elb.amazonaws.com`) returns web server page
- Security groups block direct access to app and DB tiers

#### Troubleshooting
- ALB health check failing: ensure web-server's httpd is running, port 80 open in `web-sg` from `alb-sg`
- 503 from ALB: no healthy targets in target group; check health check path
- App EC2 unreachable: confirm `app-sg` allows port 8080 from `web-sg`, not from 0.0.0.0/0

---

### 5B. AWS CLI Method

```bash
# ── Prerequisites: get VPC and subnet IDs from Project 2.1 ──────────────────
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=handson-vpc" \
  --query 'Vpcs[0].VpcId' --output text)

PUBLIC_SUBNET_1A=$(aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values=public-subnet-1a" \
  --query 'Subnets[0].SubnetId' --output text)

PRIVATE_SUBNET=$(aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values=private-subnet-1b" \
  --query 'Subnets[0].SubnetId' --output text)

echo "VPC=$VPC_ID | Pub=$PUBLIC_SUBNET_1A | Priv=$PRIVATE_SUBNET"

# ── Create 2nd public subnet for ALB (needs 2 AZs) ──────────────────────────
PUBLIC_SUBNET_1B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-1b}]' \
  --query 'Subnet.SubnetId' --output text)

# ── Create DB Subnets ────────────────────────────────────────────────────────
DB_SUBNET_1A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=db-subnet-1a}]' \
  --query 'Subnet.SubnetId' --output text)

DB_SUBNET_1B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.5.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=db-subnet-1b}]' \
  --query 'Subnet.SubnetId' --output text)

# ── STEP 1: Create Security Groups ──────────────────────────────────────────
ALB_SG=$(aws ec2 create-security-group \
  --group-name alb-sg \
  --description "ALB - allow HTTP from internet" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

WEB_SG=$(aws ec2 create-security-group \
  --group-name web-sg \
  --description "Web tier - allow HTTP from ALB only" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

APP_SG=$(aws ec2 create-security-group \
  --group-name app-sg \
  --description "App tier - allow 8080 from web tier only" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

DB_SG=$(aws ec2 create-security-group \
  --group-name db-sg \
  --description "DB tier - allow MySQL from app tier only" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

echo "SGs: ALB=$ALB_SG | WEB=$WEB_SG | APP=$APP_SG | DB=$DB_SG"

# ── STEP 2: Add Inbound Rules (security group chaining) ──────────────────────
# ALB: allow HTTP from internet
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

# Web: allow HTTP only from ALB security group
aws ec2 authorize-security-group-ingress \
  --group-id $WEB_SG \
  --protocol tcp --port 80 \
  --source-group $ALB_SG

# App: allow port 8080 only from web security group
aws ec2 authorize-security-group-ingress \
  --group-id $APP_SG \
  --protocol tcp --port 8080 \
  --source-group $WEB_SG

# DB: allow MySQL (3306) only from app security group
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG \
  --protocol tcp --port 3306 \
  --source-group $APP_SG

# ── STEP 3: Create RDS DB Subnet Group ───────────────────────────────────────
aws rds create-db-subnet-group \
  --db-subnet-group-name handson-db-subnet-group \
  --db-subnet-group-description "DB subnet group for multi-tier app" \
  --subnet-ids $DB_SUBNET_1A $DB_SUBNET_1B

# ── STEP 4: Launch Web EC2 ───────────────────────────────────────────────────
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" "Name=state,Values=available" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text)

WEB_INSTANCE=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t2.micro \
  --subnet-id $PUBLIC_SUBNET_1A \
  --security-group-ids $WEB_SG \
  --associate-public-ip-address \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server}]' \
  --user-data '#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
echo "<h1>Web Tier - $(hostname)</h1>" > /var/www/html/index.html' \
  --query 'Instances[0].InstanceId' --output text)

# ── STEP 5: Launch App EC2 ───────────────────────────────────────────────────
APP_INSTANCE=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t2.micro \
  --subnet-id $PRIVATE_SUBNET \
  --security-group-ids $APP_SG \
  --no-associate-public-ip-address \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=app-server}]' \
  --query 'Instances[0].InstanceId' --output text)

echo "EC2: WEB=$WEB_INSTANCE | APP=$APP_INSTANCE"

# ── STEP 6: Create ALB, Target Group, and Listener ──────────────────────────
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name handson-alb \
  --subnets $PUBLIC_SUBNET_1A $PUBLIC_SUBNET_1B \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

TG_ARN=$(aws elbv2 create-target-group \
  --name web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path "/" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Wait for instance to be running before registering
aws ec2 wait instance-running --instance-ids $WEB_INSTANCE

aws elbv2 register-targets \
  --target-group-arn $TG_ARN \
  --targets Id=$WEB_INSTANCE

aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

echo "ALB ARN: $ALB_ARN"
echo "Target Group ARN: $TG_ARN"

# ── STEP 7: Create RDS MySQL Instance ────────────────────────────────────────
aws rds create-db-instance \
  --db-instance-identifier handson-mysql \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --engine-version "8.0" \
  --master-username admin \
  --master-user-password "YourSecurePassword123!" \
  --db-name appdb \
  --db-subnet-group-name handson-db-subnet-group \
  --vpc-security-group-ids $DB_SG \
  --no-publicly-accessible \
  --allocated-storage 20 \
  --storage-type gp2

echo "RDS instance creation started (takes ~5-10 minutes)"

# Get ALB DNS name to test
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)
echo "ALB DNS: $ALB_DNS"
echo "Test with: curl http://$ALB_DNS"
```

---

## 6. Code Deep Dive

### Security Group Chaining Logic

Security group chaining is the key concept in this architecture. Instead of specifying an IP CIDR as the traffic source, you reference another security group ID:

```
Source: sg-0abc123 (alb-sg)   ← means "any resource that belongs to alb-sg"
```

This is powerful because:
- If you add more ALB nodes, they automatically inherit access rights
- It's dynamic — no IP management needed
- It enforces strict tier boundaries regardless of IP changes

**Why this matters:** If `web-sg` allowed `0.0.0.0/0` on port 80, users could bypass the ALB and hit web servers directly. With SG chaining, only resources with `alb-sg` attached can reach web servers.

### ALB Target Group Health Check Config

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `health-check-path` | `/` | ALB sends GET / to check if instance is alive |
| `health-check-interval` | 30s | How often ALB probes each target |
| `healthy-threshold` | 2 | Must pass 2 consecutive checks to be healthy |
| `unhealthy-threshold` | 3 | Must fail 3 consecutive checks to be marked unhealthy |

An instance is removed from rotation only after 3 failed checks (3 × 30s = 90s). This prevents flapping.

### RDS `--no-publicly-accessible`
This flag ensures RDS gets no public IP. Combined with `db-sg` allowing only `app-sg`, the database is completely unreachable from outside the VPC — even if someone knew the endpoint.

---

## 7. Verification

```bash
# Check ALB state (should be "active")
aws elbv2 describe-load-balancers \
  --names handson-alb \
  --query 'LoadBalancers[*].{Name:LoadBalancerName,State:State.Code,DNS:DNSName}' \
  --output table

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{ID:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table

# Test ALB with curl
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names handson-alb \
  --query 'LoadBalancers[0].DNSName' --output text)
curl -I http://$ALB_DNS

# Verify security group chaining
aws ec2 describe-security-groups \
  --group-ids $WEB_SG \
  --query 'SecurityGroups[*].IpPermissions' \
  --output json

# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier handson-mysql \
  --query 'DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Accessible:PubliclyAccessible}' \
  --output table

# Verify RDS is NOT publicly accessible (should return false)
aws rds describe-db-instances \
  --db-instance-identifier handson-mysql \
  --query 'DBInstances[0].PubliclyAccessible'
```

---

## 8. Observations

### ALB Round-Robin Distribution
- ALB distributes requests across healthy targets using round-robin by default
- You can enable **Least Outstanding Requests** algorithm for better distribution under variable load
- ALB maintains persistent connections to targets (keep-alive) for efficiency

### Security Groups are Stateful
- If port 80 inbound is allowed, the response traffic on the ephemeral port is automatically allowed outbound — you don't need a separate outbound rule
- This is different from NACLs, which require explicit inbound AND outbound rules

### RDS Not Publicly Accessible
- The `--no-publicly-accessible` flag means RDS has no public DNS endpoint
- Connection is only possible from within the VPC
- Even with correct credentials, the database is unreachable from outside

### ALB Cost Structure
- Fixed cost: ~$0.008/hour = ~$5.76/month baseline
- Variable cost: $0.008 per LCU-hour (Load Capacity Unit — based on connections, bandwidth, rules, rule evaluations)
- A lightly loaded ALB typically uses 1-2 LCUs = ~$16-18/month total

---

## 9. Screenshots Guide

1. **Security Groups list** — all 4 security groups in handson-vpc
2. **web-sg inbound rules** — showing source is `alb-sg` group ID, not 0.0.0.0/0
3. **app-sg inbound rules** — showing source is `web-sg` group ID
4. **db-sg inbound rules** — showing MySQL 3306 from `app-sg` group ID
5. **ALB active state** — Load Balancer showing state "active" with DNS name
6. **Target Group health** — web-server target showing "healthy" state
7. **ALB listener rules** — showing HTTP:80 → forward to web-tg
8. **EC2 instances** — both web-server and app-server running
9. **RDS instance** — showing Available state, Publicly Accessible: No
10. **curl test** — terminal showing HTTP 200 response from ALB DNS name

---

## 10. Cleanup

**Delete in reverse dependency order:**

```bash
# ── Step 1: Delete ALB Listener (must delete before ALB) ─────────────────────
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query 'Listeners[0].ListenerArn' --output text)
aws elbv2 delete-listener --listener-arn $LISTENER_ARN

# ── Step 2: Delete ALB ────────────────────────────────────────────────────────
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# ── Step 3: Delete Target Group ───────────────────────────────────────────────
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# ── Step 4: Delete RDS (takes ~5 minutes) ────────────────────────────────────
aws rds delete-db-instance \
  --db-instance-identifier handson-mysql \
  --skip-final-snapshot

echo "Waiting for RDS deletion..."
aws rds wait db-instance-deleted --db-instance-identifier handson-mysql

# ── Step 5: Delete RDS Subnet Group ──────────────────────────────────────────
aws rds delete-db-subnet-group \
  --db-subnet-group-name handson-db-subnet-group

# ── Step 6: Terminate EC2 instances ──────────────────────────────────────────
aws ec2 terminate-instances --instance-ids $WEB_INSTANCE $APP_INSTANCE
aws ec2 wait instance-terminated --instance-ids $WEB_INSTANCE $APP_INSTANCE

# ── Step 7: Delete Security Groups (in reverse chain order) ──────────────────
aws ec2 delete-security-group --group-id $DB_SG
aws ec2 delete-security-group --group-id $APP_SG
aws ec2 delete-security-group --group-id $WEB_SG
aws ec2 delete-security-group --group-id $ALB_SG

# ── Step 8: Delete extra subnets created in this project ─────────────────────
aws ec2 delete-subnet --subnet-id $PUBLIC_SUBNET_1B
aws ec2 delete-subnet --subnet-id $DB_SUBNET_1A
aws ec2 delete-subnet --subnet-id $DB_SUBNET_1B

echo "Cleanup complete."
echo "VPC and core subnets from Project 2.1 are preserved."
```

**Verify cleanup:**
```bash
aws elbv2 describe-load-balancers --names handson-alb 2>&1 | grep -i "not found\|LoadBalancerNotFound"
aws rds describe-db-instances --db-instance-identifier handson-mysql 2>&1 | grep -i "not found\|DBInstanceNotFound"
aws ec2 describe-instances --instance-ids $WEB_INSTANCE --query 'Reservations[*].Instances[*].State.Name'
```

---

*Guide generated for Stage 02 — AWS Multi-Tier Architecture Hands-on. Uses AWS CLI v2 and AWS Console. No Terraform.*
