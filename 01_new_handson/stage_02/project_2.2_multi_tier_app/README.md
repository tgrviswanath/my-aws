# Project 2.2 — Multi-Tier Application Architecture

**Stage:** 02 | **Level:** Intermediate | **Est. Time:** 3–4 hours | **Cost:** ~$40–55/month

Deploy a classic 3-tier web application inside the VPC built in Project 2.1. An Application Load Balancer in the public subnets accepts HTTP traffic and distributes it to EC2 web-tier instances. The web tier proxies API calls to an EC2 app tier sitting in the private subnets, which in turn queries an RDS MySQL database in a DB subnet group. Security groups are chained so that each tier only accepts traffic from the tier directly above it, preventing lateral movement between tiers.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| ALB | Layer-7 load balancer in public subnets | ~$16/month + $0.008/LCU |
| EC2 web tier (×2) | Apache/Nginx reverse proxy, t3.micro | ~$8/month each |
| EC2 app tier (×2) | Application logic, private subnet, t3.micro | ~$8/month each |
| RDS MySQL | Managed database in DB subnet group | ~$15/month (db.t3.micro) |
| Security Groups (×4) | alb-sg, web-sg, app-sg, rds-sg | Free |
| Target Groups (×2) | Web-tier TG and app-tier TG with health checks | Free |

## Input / Output

### Input

| Parameter | Value |
|---|---|
| VPC | From Project 2.1 (`10.0.0.0/16`) |
| AMI ID | `ami-0c02fb55956c7d316` (Amazon Linux 2, us-east-1) |
| EC2 instance type | `t3.micro` |
| DB engine | MySQL 8.0 |
| DB instance class | `db.t3.micro` |
| DB name | `appdb` |
| ALB listener port | HTTP 80 |
| Health check path | `/health` |

### Output

| Resource | Result |
|---|---|
| ALB DNS | `project22-alb-xxxxxxxxx.us-east-1.elb.amazonaws.com` |
| Web tier | 2× EC2 in public subnets, registered to web-tg |
| App tier | 2× EC2 in private subnets, registered to app-tg |
| RDS endpoint | `appdb.xxxxxxxxx.us-east-1.rds.amazonaws.com:3306` |
| End-to-end test | `curl http://<ALB_DNS>/health` returns HTTP 200 |

## Architecture

```
  Internet
      │
  [ALB]  alb-sg: allows 0.0.0.0/0:80
      │
  ┌───┴──────────────────────────────────────────┐
  │  Public Subnets (10.0.1.0/24, 10.0.2.0/24)  │
  │  [EC2 web-1]          [EC2 web-2]            │
  │  web-sg: allows alb-sg:80 only               │
  └───┬──────────────────────────────────────────┘
      │ proxy to :8080
  ┌───┴──────────────────────────────────────────┐
  │  Private Subnets (10.0.3.0/24, 10.0.4.0/24) │
  │  [EC2 app-1]          [EC2 app-2]            │
  │  app-sg: allows web-sg:8080 only             │
  └───┬──────────────────────────────────────────┘
      │ MySQL :3306
  ┌───┴──────────────────────────────────────────┐
  │  DB Subnet Group (10.0.3.0/24, 10.0.4.0/24) │
  │  [RDS MySQL primary]                         │
  │  rds-sg: allows app-sg:3306 only             │
  └──────────────────────────────────────────────┘
```

## Quick Start

```cmd
REM Step 1: Create alb-sg — allows HTTP from internet
aws ec2 create-security-group --group-name alb-sg ^
  --description "ALB inbound HTTP" --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress --group-id <ALB_SG_ID> ^
  --protocol tcp --port 80 --cidr 0.0.0.0/0

REM Step 2: Create web-sg — allows only alb-sg as source
aws ec2 create-security-group --group-name web-sg ^
  --description "Web tier - from ALB only" --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress --group-id <WEB_SG_ID> ^
  --protocol tcp --port 80 --source-group <ALB_SG_ID>

REM Step 3: Create app-sg — allows only web-sg as source
aws ec2 create-security-group --group-name app-sg ^
  --description "App tier - from web tier only" --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress --group-id <APP_SG_ID> ^
  --protocol tcp --port 8080 --source-group <WEB_SG_ID>

REM Step 4: Create rds-sg — allows only app-sg as source
aws ec2 create-security-group --group-name rds-sg ^
  --description "RDS - from app tier only" --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress --group-id <RDS_SG_ID> ^
  --protocol tcp --port 3306 --source-group <APP_SG_ID>

REM Step 5: Launch web-tier EC2 in public subnet
aws ec2 run-instances ^
  --image-id ami-0c02fb55956c7d316 --instance-type t3.micro ^
  --subnet-id <PUBLIC_SUBNET_1A_ID> --security-group-ids <WEB_SG_ID> ^
  --associate-public-ip-address ^
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=web-tier-1a}]"

REM Step 6: Create RDS DB subnet group (2 AZs required even for single-AZ)
aws rds create-db-subnet-group ^
  --db-subnet-group-name project22-db-subnet-group ^
  --db-subnet-group-description "DB subnets across 2 AZs" ^
  --subnet-ids <PRIVATE_SUBNET_1A_ID> <PRIVATE_SUBNET_1B_ID>

REM Step 7: Create RDS MySQL instance
aws rds create-db-instance ^
  --db-instance-identifier project22-mysql ^
  --db-instance-class db.t3.micro --engine mysql --engine-version 8.0 ^
  --master-username admin --master-user-password <DB_PASSWORD> ^
  --db-name appdb --db-subnet-group-name project22-db-subnet-group ^
  --vpc-security-group-ids <RDS_SG_ID> --no-multi-az --allocated-storage 20

REM Step 8: Create ALB, target group, register instances, create listener
aws elbv2 create-load-balancer --name project22-alb ^
  --subnets <PUBLIC_SUBNET_1A_ID> <PUBLIC_SUBNET_1B_ID> ^
  --security-groups <ALB_SG_ID>

aws elbv2 create-target-group --name web-tg ^
  --protocol HTTP --port 80 --vpc-id <VPC_ID> --health-check-path /health

aws elbv2 register-targets --target-group-arn <WEB_TG_ARN> ^
  --targets Id=<WEB_EC2_1A_ID> Id=<WEB_EC2_1B_ID>

aws elbv2 create-listener --load-balancer-arn <ALB_ARN> ^
  --protocol HTTP --port 80 ^
  --default-actions Type=forward,TargetGroupArn=<WEB_TG_ARN>
```

## Data Flow

1. User sends `GET http://<ALB_DNS>/` — ALB listener on port 80 receives the request.
2. ALB evaluates the default forwarding rule and selects a healthy target from `web-tg` using round-robin.
3. ALB opens a new connection to the chosen web-tier EC2 on port 80; `web-sg` allows this because the source is `alb-sg`.
4. Web-tier EC2 processes the request and proxies the API call to the app-tier EC2 on port 8080; `app-sg` allows this because the source is `web-sg`.
5. App-tier EC2 runs the business logic and issues a MySQL query to the RDS endpoint on port 3306; `rds-sg` allows this because the source is `app-sg`.
6. RDS returns the query result; the response travels back up through app tier → web tier → ALB → client.
7. ALB health check hits `/health` on each web-tier target every 30 seconds; any target returning non-200 is marked unhealthy and removed from rotation.

## Project Files

| File | Description |
|---|---|
| `README.md` | This document |
| `sg-chain.sh` | Creates all 4 security groups with chained ingress rules |
| `launch-ec2.sh` | Launches web and app tier instances with user-data |
| `web-userdata.sh` | User-data script: installs Nginx, configures proxy pass |
| `app-userdata.sh` | User-data script: installs Python app, listens on 8080 |
| `alb-setup.sh` | Creates ALB, target groups, listeners, registers targets |
| `rds-setup.sh` | Creates DB subnet group and RDS MySQL instance |

## Lessons Learned

- **Security group chaining blocks lateral movement:** Setting `source-group` instead of a CIDR means only traffic originating from the referenced group's instances is allowed. An attacker who compromises the web tier cannot directly reach RDS — they must also compromise the app tier.
- **ALB health check path must return HTTP 200:** If `/health` returns 301 (redirect to HTTPS) or 404, the target is marked unhealthy and gets no traffic. Test the health check URL directly on the instance before registering it.
- **Target group deregistration delay defaults to 300 seconds:** During a deployment, old instances stay in "draining" state for 5 minutes so in-flight requests complete. Reduce this to 30–60s in dev to speed up deployments, but keep it high in production.
- **RDS DB subnet group requires 2 AZs even for single-AZ deployments:** AWS enforces multi-AZ subnet group creation for RDS even if `--no-multi-az` is set. The DB only runs in one AZ, but the subnet group must span two.
- **ALB replaces the client IP with its own:** App-tier instances see the ALB's internal IP in the TCP connection, not the original client IP. Use the `X-Forwarded-For` header (populated by ALB) to get the real client IP in application logs.
- **Security group rules reference group IDs, not names:** In CLI and IaC, always use the group ID (`sg-xxxxxxxxx`), not the name. Names are not unique across VPCs and can cause silent misrouting.
- **RDS `--no-multi-az` means zero failover:** A reboot or AZ failure causes a full outage. Enable Multi-AZ for any workload where downtime matters — it doubles the cost but provides automatic standby promotion in ~60–120 seconds.
