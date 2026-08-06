# AWS Console UI — Step-by-Step Guide
# Project 2.2: 3-Tier AWS Application Architecture

> Method: AWS Management Console only (no CLI)
> Region: us-east-1 (N. Virginia)
> Estimated time: 45–60 minutes
> Dependency: Project 2.1 VPC must exist

---

## Prerequisites Check

Before starting, verify in the console:

- [ ] VPC `handson-vpc` is visible under **VPC → Your VPCs**
- [ ] `public-subnet-1a` and `private-subnet-1b` exist under **VPC → Subnets**
- [ ] IAM permissions include: `EC2:*`, `ElasticLoadBalancing:*`, `RDS:*`
- [ ] You're in region **us-east-1** (top-right corner of console)
- [ ] A key pair exists under **EC2 → Key Pairs**

**Quick permission check:**
1. Go to **EC2 → Security Groups** — can you see the list? ✅
2. Go to **EC2 → Load Balancers** — is the menu accessible? ✅
3. Go to **RDS → Databases** — does the page load? ✅

---

## Step 1 — Create Security Groups

Security groups are the core of this architecture. We create 4 groups and chain them together so traffic flows only through the proper path.

### Decision Point 1: Security Group Chaining vs NACLs

| Approach | Level | Statefulness | Recommended |
|----------|-------|--------------|-------------|
| ✅ Security Group Chaining | Instance level | Stateful | Yes — fine-grained, dynamic |
| NACLs | Subnet level | Stateless | Supplementary only |
| Combined | Both | Mixed | Production best practice |

**Use security group chaining** — referencing another SG as the source is more flexible and maintainable than IP-based rules.

---

### Create alb-sg (Load Balancer)

1. Go to **EC2 → Security Groups** (left sidebar under Network & Security)
2. Click **Create security group**
3. Fill in:
   - **Security group name:** `alb-sg`
   - **Description:** `ALB - allow HTTP from internet`
   - **VPC:** `handson-vpc`
4. Under **Inbound rules** → click **Add rule**:
   - Type: `HTTP`, Protocol: TCP, Port: 80, Source: `0.0.0.0/0`
5. Leave outbound rules as default (All traffic)
6. Click **Create security group**

### Create web-sg (Web Tier)

1. Click **Create security group**
2. Fill in:
   - **Name:** `web-sg`
   - **Description:** `Web tier - HTTP from ALB only`
   - **VPC:** `handson-vpc`
3. Inbound rules — **Add rule**:
   - Type: HTTP, Port: 80, Source: **Custom** → type/select `alb-sg` (pick the SG ID)
4. Add another rule:
   - Type: SSH, Port: 22, Source: My IP
5. Create security group

### Create app-sg (App Tier)

1. Click **Create security group**
2. Fill in:
   - **Name:** `app-sg`
   - **Description:** `App tier - 8080 from web tier only`
   - **VPC:** `handson-vpc`
3. Inbound rules → **Add rule**:
   - Type: Custom TCP, Port: 8080, Source: **Custom** → select `web-sg`
4. Create security group

### Create db-sg (Database Tier)

1. Click **Create security group**
2. Fill in:
   - **Name:** `db-sg`
   - **Description:** `DB tier - MySQL from app tier only`
   - **VPC:** `handson-vpc`
3. Inbound rules → **Add rule**:
   - Type: MySQL/Aurora (3306), Source: **Custom** → select `app-sg`
4. Create security group

### 📸 Screenshot
> Capture 1: Security Groups list filtered by `handson-vpc` — all 4 groups visible (alb-sg, web-sg, app-sg, db-sg)
> Capture 2: `web-sg` inbound rules tab — showing source is the sg-xxxx ID of alb-sg, NOT 0.0.0.0/0
> Capture 3: `db-sg` inbound rules — MySQL 3306 with source = app-sg group ID

### Expected Outcome
- 4 security groups exist in `handson-vpc`
- Each group only allows traffic from the immediately preceding tier
- No group (except alb-sg) has 0.0.0.0/0 as the inbound source for application ports

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| Can't select SG as source | Same VPC required | Confirm all SGs are in `handson-vpc` |
| SG rule not saving | Overlapping rules | Remove duplicate rule before adding |
| Can't find SG in dropdown | Wrong VPC filter | Type the SG name or ID in the source box |
| MySQL type not in dropdown | Scroll down in Type | It's listed as "MySQL/Aurora" |

---

## Step 2 — Launch EC2 Instances (Web and App Tiers)

### Decision Point 2: User Data Scripts

| Option | What It Does | Recommendation |
|--------|-------------|----------------|
| ✅ With user data | Installs web server on boot automatically | Use for testing |
| Without user data | Clean instance; manual setup | Use for custom apps |

**Use user data** for this exercise — it auto-installs Apache so the ALB health check passes immediately.

---

### Launch Web Server (Public Subnet)

1. Go to **EC2 → Instances → Launch instances**
2. **Name and tags:** `web-server`
3. **AMI:** Amazon Linux 2023 AMI (64-bit x86)
4. **Instance type:** `t2.micro` (free tier eligible)
5. **Key pair:** select your existing key pair
6. **Network settings** → click **Edit**:
   - VPC: `handson-vpc`
   - Subnet: `public-subnet-1a`
   - Auto-assign public IP: **Enable**
   - Security group: select **existing** → choose `web-sg`
7. **Advanced details** → **User data** → paste:
   ```bash
   #!/bin/bash
   yum update -y
   yum install -y httpd
   systemctl start httpd
   systemctl enable httpd
   echo "<h1>Web Tier — $(hostname -f)</h1><p>Instance: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>" > /var/www/html/index.html
   ```
8. Click **Launch instance**

### Launch App Server (Private Subnet)

1. Click **Launch instances** again
2. **Name:** `app-server`
3. **AMI:** Amazon Linux 2023 AMI
4. **Instance type:** `t2.micro`
5. **Key pair:** same key pair
6. **Network settings** → click **Edit**:
   - VPC: `handson-vpc`
   - Subnet: `private-subnet-1b`
   - Auto-assign public IP: **Disable**
   - Security group: `app-sg`
7. No user data needed for basic setup
8. Click **Launch instance**

### 📸 Screenshot
> Capture 1: EC2 Instances list showing both `web-server` (running, public IP) and `app-server` (running, no public IP)
> Capture 2: `web-server` details — Instance summary showing subnet = public-subnet-1a, public IPv4 DNS visible
> Capture 3: `app-server` details — no public IPv4, subnet = private-subnet-1b

### Expected Outcome
- `web-server`: Running, in public-subnet-1a, has public IP
- `app-server`: Running, in private-subnet-1b, no public IP
- Direct HTTP access to web-server public IP works (port 80 in web-sg allows it from alb-sg, not directly from internet)
- Actually: direct access to web-server IP will be blocked since web-sg only allows from alb-sg, not 0.0.0.0/0 — this is intentional!

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| Instance not starting | vCPU limit | Check service quotas for EC2 |
| Wrong subnet in dropdown | Forgot to select VPC first | In network settings, select VPC before subnet |
| SSH not working to app-server | No public IP | SSH to web-server first, then SSH from there |
| Httpd not running | User data failed | SSH in and run `systemctl status httpd` |

---

## Step 3 — Create ALB and Target Group

### Decision Point 3: ALB vs NLB

| Feature | Application Load Balancer | Network Load Balancer |
|---------|--------------------------|----------------------|
| Protocol | HTTP, HTTPS, WebSocket | TCP, UDP, TLS |
| Routing intelligence | Path, host, header, query | IP + port only |
| Health checks | HTTP status code | TCP connection |
| ✅ Use case | Web apps, REST APIs | Gaming, real-time, raw TCP |
| SSL termination | ✅ Yes | ✅ Yes |

**Choose ALB** — this is a web application and ALB gives us HTTP-aware health checks and path routing.

---

### Create DB Subnets (Required for RDS Subnet Group)

RDS subnet group requires 2 subnets in different AZs.

1. **VPC → Subnets → Create subnet**
   - VPC: `handson-vpc`, Name: `db-subnet-1a`, AZ: `us-east-1a`, CIDR: `10.0.4.0/24`
2. **Create subnet** again
   - VPC: `handson-vpc`, Name: `db-subnet-1b`, AZ: `us-east-1b`, CIDR: `10.0.5.0/24`
3. Also create a 2nd public subnet for ALB (needs 2 AZs):
   - Name: `public-subnet-1b`, AZ: `us-east-1b`, CIDR: `10.0.3.0/24`
   - Associate with the public route table

### Create Target Group

1. Go to **EC2 → Target Groups** (under Load Balancing in left sidebar)
2. Click **Create target group**
3. Configure:
   - **Target type:** Instances
   - **Target group name:** `web-tg`
   - **Protocol:** HTTP, **Port:** 80
   - **VPC:** `handson-vpc`
4. **Health checks:**
   - Protocol: HTTP, Path: `/`
   - Healthy threshold: 2, Unhealthy threshold: 3
   - Interval: 30 seconds
5. Click **Next**
6. **Register targets:** check `web-server` → click **Include as pending below**
7. Click **Create target group**

### Create Application Load Balancer

1. Go to **EC2 → Load Balancers → Create Load Balancer**
2. Choose **Application Load Balancer** → click **Create**
3. Configure:
   - **Name:** `handson-alb`
   - **Scheme:** Internet-facing
   - **IP address type:** IPv4
4. **Network mapping:**
   - VPC: `handson-vpc`
   - Availability Zones: check `us-east-1a` → `public-subnet-1a`
   - Also check `us-east-1b` → `public-subnet-1b` (the new one you created)
5. **Security groups:** remove default SG → add `alb-sg`
6. **Listeners and routing:**
   - HTTP : 80 → Forward to `web-tg`
7. Click **Create load balancer**
8. Wait ~2 minutes until status shows **Active**

### 📸 Screenshot
> Capture 1: Load Balancers list — `handson-alb` showing State = Active, DNS name visible
> Capture 2: Target Groups → `web-tg` → Targets tab — `web-server` showing Health Status = **healthy**
> Capture 3: ALB Listeners tab — HTTP:80 → forward to web-tg rule visible

### Expected Outcome
- ALB state: Active
- Target `web-server` health: healthy (green)
- `curl http://<ALB-DNS-name>` returns the web page with hostname

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| ALB stuck "provisioning" | Normal — wait 2 minutes | Refresh; takes time |
| Target shows "unhealthy" | httpd not running | SSH to web-server, run `systemctl start httpd` |
| Target shows "unused" | Instance not registered | Target Groups → Register targets |
| 503 from ALB DNS | No healthy targets | Check health check path matches `/` |
| ALB requires 2 subnets error | Only 1 AZ selected | Add subnet in second AZ |

---

## Step 4 — Create RDS MySQL Instance

### Console Actions

**Create DB Subnet Group:**
1. Go to **RDS → Subnet groups** (left sidebar)
2. Click **Create DB subnet group**
3. Configure:
   - **Name:** `handson-db-subnet-group`
   - **Description:** DB subnets for multi-tier app
   - **VPC:** `handson-vpc`
4. **Add subnets:** select `us-east-1a` → `db-subnet-1a`, then `us-east-1b` → `db-subnet-1b`
5. Click **Create**

**Create RDS MySQL:**
1. Go to **RDS → Databases → Create database**
2. **Creation method:** Standard create
3. **Engine:** MySQL, Version: 8.0.x (latest)
4. **Templates:** Free tier (uses db.t3.micro, Single-AZ)
5. **Settings:**
   - DB instance identifier: `handson-mysql`
   - Master username: `admin`
   - Master password: choose a secure password (write it down!)
6. **Instance configuration:** `db.t3.micro`
7. **Storage:** 20 GiB, gp2
8. **Connectivity:**
   - VPC: `handson-vpc`
   - DB subnet group: `handson-db-subnet-group`
   - Public access: **No**
   - VPC security group: remove default → add `db-sg`
9. **Additional configuration:**
   - Initial database name: `appdb`
   - Disable automated backups for cost savings in learning (optional)
10. Click **Create database**
11. Wait 5–10 minutes for status to show **Available**

### 📸 Screenshot
> Capture 1: RDS database creation form — showing VPC, no public access, db-sg selected
> Capture 2: RDS Databases list — `handson-mysql` showing Status = **Available**
> Capture 3: RDS instance details — Connectivity tab showing **Publicly accessible: No** and security group = db-sg

### Expected Outcome
- RDS status: Available
- Publicly accessible: No
- VPC security group: db-sg
- Endpoint visible but only accessible from within VPC

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| RDS creation takes too long | Normal for RDS | It takes 5-15 minutes; wait |
| "No subnet group" error | Subnet group not created | Complete the subnet group creation first |
| Can't connect to RDS from app | Wrong SG or subnet | Confirm app-sg → db-sg chain, RDS in db subnets |
| Subnet group validation fails | Subnets in same AZ | DB subnet group needs 2 different AZs |
| Free tier not available | db.t2.micro selected | Free tier uses db.t3.micro now; check template |

---

## Final Verification

After completing all 4 steps:

```
ALB DNS → web-server (port 80) → app-server (port 8080) → RDS MySQL (port 3306)
```

1. Copy the ALB DNS name from **EC2 → Load Balancers → handson-alb**
2. Open in browser or run: `curl http://<alb-dns-name>`
3. Expected: HTML page showing web tier hostname

**Security test:**
- Try accessing `web-server` public IP directly on port 80 → should be **blocked** (web-sg only allows from alb-sg)
- This confirms the SG chain is working correctly

---

## Cleanup Order

Delete in this exact order to avoid dependency errors:
1. ALB listener → ALB
2. Target group
3. RDS instance → DB subnet group
4. EC2 instances (web-server, app-server)
5. Security groups (db-sg → app-sg → web-sg → alb-sg)
6. Extra subnets (db-subnet-1a, db-subnet-1b, public-subnet-1b)

See GUIDE.md § 10 for full CLI cleanup commands.

---

*Console UI guide for Project 2.2 — Stage 02 AWS Multi-Tier Architecture Hands-on*
