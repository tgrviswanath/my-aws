# Hands-on Log  Project 3.2: Terraform AWS Infrastructure

**Date:** 2026-05-14
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.2_terraform_aws_infra\terraform\

---

## Project Description

This project builds a **complete production-grade multi-tier AWS infrastructure** using Terraform only  no console clicks. It combines everything learned in Project 3.1 (variables, locals, data sources, outputs) to create a real application stack.

**Why this project matters:**
This is the first time you create infrastructure that a real application could run on. VPC networking, load balancing, auto-scaling, and a managed database  all defined as code, all reproducible with one command.

**Architecture:**
```
Internet
    | HTTP port 80
    v
Application Load Balancer (handson-dev-alb)
    | in 2 Public Subnets (ap-south-1a, ap-south-1b)
    v
Auto Scaling Group (1 EC2 t3.micro running Nginx)
    | in 2 Private App Subnets
    | user_data installs Nginx + creates /health endpoint
    v
RDS MySQL 8.0 (db.t3.micro)
    | in 2 Private DB Subnets
    | NOT publicly accessible
    v
NAT Gateway
    | allows EC2 to reach internet for yum updates
    | in Public Subnet with Elastic IP
```

**Resources created (28 total):**
| Category | Resources | Count |
|----------|-----------|-------|
| Network | VPC, 6 subnets, IGW, EIP, NAT GW, 2 route tables, 6 RT associations | 18 |
| Security | ALB SG, App SG, RDS SG | 3 |
| Compute | Launch Template, Auto Scaling Group | 2 |
| Load Balancer | ALB, Target Group, Listener | 3 |
| Database | DB Subnet Group, RDS MySQL | 2 |
| **Total** | | **28** |

**Estimated cost while running: ~$1.80/day**
- NAT Gateway: ~$1.08/day (biggest cost)
- RDS db.t3.micro: ~$0.41/day
- EC2 t3.micro: ~$0.12/day
- ALB: ~$0.19/day

---

## File Structure

```
terraform/
 versions.tf      <- Terraform version + provider requirements
 variables.tf     <- All input variables
 locals.tf        <- name_prefix, common_tags
 main.tf          <- Provider configuration only
 vpc.tf           <- VPC, subnets, IGW, NAT, route tables
 ec2.tf           <- Security groups, ALB, launch template, ASG
 rds.tf           <- RDS MySQL
 outputs.tf       <- All outputs
 terraform.tfvars <- Your actual values
```

---

## Prerequisites

### Pre-req 1  AWS CLI Authentication

**Command run:**
```
aws sts get-caller-identity
```

**Output received:**
```
{
    "UserId": "AIDAXGVATZAHVJ3RFFKKR",
    "Account": "495331821583",
    "Arn": "arn:aws:iam::495331821583:user/vswnth1"
}
```

**My observation:**
- Authenticated as IAM user vswnth1 in account 495331821583
- Using IAM user (not root)  correct security practice

**Verification:** OK - AWS CLI configured correctly

[Screenshot: 00_aws_cli_auth.png]
> Terminal showing aws sts get-caller-identity output

---

### Pre-req 2  Get Your Public IP (for SSH security group)

**Command run:**
```
(Invoke-WebRequest -Uri "https://checkip.amazonaws.com").Content.Trim()
```

**Output received:**
```
103.82.209.148
```

**My observation:**
- This IP is used in the App security group SSH rule: 103.82.209.148/32
- Only your machine can SSH to EC2 instances  no 0.0.0.0/0 on port 22
- This is a critical security practice  never open SSH to the world

**Verification:** OK - IP captured for terraform.tfvars

[Screenshot: 00_my_public_ip.png]
> Terminal showing your public IP address

---

### Pre-req 3  EC2 Key Pair Created

**Steps taken:**
```
AWS Console -> EC2 -> Key Pairs -> Create key pair
Name: handson-key
Type: RSA
Format: .pem
-> Downloaded: handson-key.pem
```

**My observation:**
- Key pair name in Terraform = "handson-key" (WITHOUT .pem extension)
- The .pem file is needed for SSH access to EC2 instances
- Store it safely  AWS shows the private key only once

**Verification:** OK - Key pair created in ap-south-1

[Screenshot: 00_ec2_keypair.png]
> AWS Console -> EC2 -> Key Pairs showing handson-key

---

### Pre-req 4  terraform.tfvars Configured

**File contents:**
```
region           = "ap-south-1"
project          = "handson"
environment      = "dev"
key_name         = "handson-key"
my_ip            = "103.82.209.148/32"
azs              = ["ap-south-1a", "ap-south-1b"]
desired_capacity = 1
min_size         = 1
max_size         = 2
db_name          = "appdb"
db_username      = "admin"
# db_password passed via -var flag (never committed to git)
```

**My observation:**
- desired_capacity = 1 (saves cost vs default 2)
- db_password NOT in file  passed via -var="db_password=..." at runtime
- my_ip includes /32 CIDR notation  restricts SSH to exactly one IP

**Verification:** OK - All values set correctly for ap-south-1

---

## Bugs Fixed During Setup

### Bug 1  Duplicate resources across files

**Error:**
```
Error: Duplicate resource "aws_security_group" configuration
  on main.tf line 123: resource "aws_security_group" "alb"
  A aws_security_group resource named "alb" was already declared at ec2.tf:3
```

**Root cause:**
main.tf contained ALL resources AND separate files (vpc.tf, ec2.tf, rds.tf) also contained the same resources. Terraform reads all .tf files together  duplicates are not allowed.

**Fix:**
Cleared main.tf to contain ONLY the provider block. All resources stay in their dedicated files.

```
# main.tf after fix  provider only
provider "aws" { region = var.region }
```

**My observation:**
- Terraform treats all .tf files in a directory as ONE configuration
- Splitting into files is for human readability only  Terraform merges them all
- Each resource must be declared exactly once across all files

**Verification:** OK - terraform init succeeded after fix

---

### Bug 2  Single-line block syntax error

**Error:**
```
Error: Invalid single-argument block definition
  on ec2.tf line 6:
  ingress { from_port = 80  to_port = 80  protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] description = "HTTP" }
  A single-line block definition must end with a closing brace immediately after its single argument definition.
```

**Root cause:**
HCL single-line blocks can only have ONE argument. Multiple arguments require multi-line format.

**Fix:**
```
# Before (broken)
ingress { from_port = 80  to_port = 80  protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }

# After (fixed)
ingress {
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}
```

**My observation:**
- HCL is strict about single-line vs multi-line block syntax
- When in doubt, always use multi-line format  it is always valid
- This error appeared in both the ALB security group and the data source filter

**Verification:** OK - terraform init succeeded after fix

---

### Bug 3  RDS free tier backup retention limit

**Error:**
```
Error: creating RDS DB Instance (handson-dev-mysql):
api error FreeTierRestrictionError: The specified backup retention period
exceeds the maximum available to free tier customers.
```

**Root cause:**
Free tier AWS accounts cannot set backup_retention_period > 0 on RDS.

**Fix:**
```
# rds.tf  changed from 7 to 0
backup_retention_period = 0
```

**My observation:**
- Free tier accounts have restrictions that paid accounts don't
- backup_retention_period = 0 disables automated backups
- For production: use a paid account and set retention to 7+ days

**Verification:** OK - RDS created successfully after fix

---

### Bug 4  RDS password contains invalid character

**Error:**
```
Error: creating RDS DB Instance (handson-dev-mysql):
api error InvalidParameterValue: The parameter MasterUserPassword is not a valid password.
Only printable ASCII characters besides '/', '@', '"', ' ' may be used.
```

**Root cause:**
Password "Handson@2026!" contains '@' which is not allowed in RDS passwords.

**Fix:**
Changed password from "Handson@2026!" to "Handson2026Pass!" (removed @)

**My observation:**
- RDS password restrictions: no '/', '@', '"', or spaces
- Always test passwords before using in production
- Use AWS Secrets Manager for production passwords

**Verification:** OK - RDS created successfully with new password

---

## Hands-on Steps

### Step 1  terraform init

**Command run:**
```
terraform init
```

**Output received:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**What happened:**
- Downloaded AWS provider v5.100.0 to local .terraform/ folder
- Created .terraform.lock.hcl lock file
- NOTHING created in AWS

**My observation:**
- Only one provider needed (no random  bucket names come from variables, not random)
- Same provider version as all previous phases  lock file ensures consistency
- terraform init is always local-only  safe to run anytime

**Verification:** OK - Initialized successfully

[Screenshot: 01_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

### Step 2  terraform plan

**Command run:**
```
terraform plan -var-file="terraform.tfvars" -var="db_password=Handson2026Pass!"
```

**Key output:**
```
data.aws_ami.amazon_linux: Read complete after 1s [id=ami-0999036d4c4235ceb]

Plan: 28 to add, 0 to change, 0 to destroy.

Changes to Outputs:
+ alb_dns_name           = (known after apply)
+ alb_url                = (known after apply)
+ app_sg_id              = (known after apply)
+ nat_gateway_ip         = (known after apply)
+ private_app_subnet_ids = [(known after apply), (known after apply)]
+ private_db_subnet_ids  = [(known after apply), (known after apply)]
+ public_subnet_ids      = [(known after apply), (known after apply)]
+ rds_endpoint           = (known after apply)
+ vpc_id                 = (known after apply)
```

**Key confirmations in plan:**
- AMI resolved: ami-0999036d4c4235ceb (latest Amazon Linux 2023 in ap-south-1)
- Your IP locked in: 103.82.209.148/32 (SSH rule)
- DB password hidden: password = (sensitive value)
- Subnets spread across ap-south-1a and ap-south-1b
- Security chain correct: ALB SG -> App SG -> RDS SG
- All names prefixed: handson-dev-*

**My observation:**
- 28 resources is a lot  this is real production-grade infrastructure
- Data source resolved the AMI automatically  no hardcoded AMI ID
- db_password shows as (sensitive value)  never revealed in plan
- All 9 outputs will be populated after apply

**Verification:** OK - Plan shows 28 resources, all values correct

[Screenshot: 02_terraform_plan.png]
> Terminal showing "Plan: 28 to add, 0 to change, 0 to destroy"

---

### Step 3  terraform apply (First attempt  RDS backup error)

**Command run:**
```
terraform apply -var-file="terraform.tfvars" -var="db_password=Handson@2026!"
```

**What happened:**
- 27 of 28 resources created successfully
- RDS failed with FreeTierRestrictionError (backup_retention_period = 7)
- Fixed: changed backup_retention_period to 0 in rds.tf

**Resources created before error:**
- VPC, all 6 subnets, IGW, EIP, NAT Gateway
- All route tables and associations
- All 3 security groups
- ALB, Target Group, Listener
- Launch Template, Auto Scaling Group

**My observation:**
- Terraform is idempotent  re-running apply only creates what is missing
- The 27 already-created resources were NOT recreated on the second attempt
- Terraform refreshed state and only created the missing RDS instance

---

### Step 4  terraform apply (Second attempt  password error)

**Command run:**
```
terraform apply -var-file="terraform.tfvars" -var="db_password=Handson@2026!"
```

**Error:**
```
api error InvalidParameterValue: The parameter MasterUserPassword is not a valid password.
Only printable ASCII characters besides '/', '@', '"', ' ' may be used.
```

**Fix:** Changed password to "Handson2026Pass!" (removed @)

---

### Step 5  terraform apply (Third attempt  SUCCESS)

**Command run:**
```
terraform apply -var-file="terraform.tfvars" -var="db_password=Handson2026Pass!"
```

**Output received:**
```
aws_db_instance.mysql: Creating...
aws_db_instance.mysql: Still creating... [10s elapsed]
...
aws_db_instance.mysql: Creation complete after 4m33s [id=db-CDCK5XACKW474CHKSIX3YTJU3I]

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:
alb_dns_name = "handson-dev-alb-66391407.ap-south-1.elb.amazonaws.com"
alb_url      = "http://handson-dev-alb-66391407.ap-south-1.elb.amazonaws.com"
app_sg_id    = "sg-0d4cdc3be1fb345e7"
nat_gateway_ip = "3.7.192.253"
private_app_subnet_ids = ["subnet-0ebb6ccf04efd9ae0", "subnet-0626f1b6d9b71c8b6"]
private_db_subnet_ids  = ["subnet-065f8001f575628ec", "subnet-0e6643693bf41216a"]
public_subnet_ids      = ["subnet-06b9c76cb41c6ceba", "subnet-0653b835e4b7de436"]
rds_endpoint = "handson-dev-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306"
vpc_id       = "vpc-005a59b1a48818658"
```

**All 28 resources created. Infrastructure is live.**

**My observation:**
- RDS took 4m33s  the slowest resource (always the case)
- NAT Gateway took ~2 minutes  second slowest
- All other resources created in seconds
- Terraform's idempotency saved us  only RDS was created on the 3rd attempt

**Verification:** OK - All 28 resources created successfully

[Screenshot: 03_terraform_apply_complete.png]
> Terminal showing "Apply complete! Resources: 1 added" with all 9 outputs

---

### Step 6  Test the Application

**ALB URL tested in browser:**
```
http://handson-dev-alb-66391407.ap-south-1.elb.amazonaws.com
```

**Response received:**
```
ip-10-0-4-121.ap-south-1.compute.internal
AZ: | Env: dev
```

**What this confirms:**
- EC2 instance is running and serving traffic
- Private IP 10.0.4.121 = in subnet 10.0.4.0/24 (private-app-b in ap-south-1b)
- Nginx installed and running via user_data script
- ALB health check passing (EC2 registered as healthy target)
- AZ field empty = IMDSv2 metadata needs token (minor, non-critical)

**Health endpoint tested:**
```
http://handson-dev-alb-66391407.ap-south-1.elb.amazonaws.com/health
```
Response: OK

**My observation:**
- EC2 is in a PRIVATE subnet (10.0.4.x)  not directly accessible from internet
- Traffic flows: Internet -> ALB (public) -> EC2 (private)  correct architecture
- The hostname shows the internal DNS name  confirms private networking
- user_data script ran successfully on first boot

**Verification:** OK - Application accessible via ALB, EC2 in private subnet

[Screenshot: 04_alb_browser_response.png]
> Browser showing the EC2 hostname and Env: dev response

[Screenshot: 05_health_endpoint.png]
> Browser showing /health endpoint returning "OK"

---

### Step 7  Verify in AWS Console

**7a. VPC**
```
AWS Console -> VPC -> Your VPCs
handson-dev-vpc: vpc-005a59b1a48818658 (10.0.0.0/16) - available
```

[Screenshot: 06_vpc_console.png]
> VPC console showing handson-dev-vpc with CIDR 10.0.0.0/16

---

**7b. Subnets (6 total)**
```
VPC -> Subnets -> filter by vpc-005a59b1a48818658

handson-dev-public-a      10.0.1.0/24  ap-south-1a  (map_public_ip=true)
handson-dev-public-b      10.0.2.0/24  ap-south-1b  (map_public_ip=true)
handson-dev-private-app-a 10.0.3.0/24  ap-south-1a  (map_public_ip=false)
handson-dev-private-app-b 10.0.4.0/24  ap-south-1b  (map_public_ip=false)
handson-dev-private-db-a  10.0.5.0/24  ap-south-1a  (map_public_ip=false)
handson-dev-private-db-b  10.0.6.0/24  ap-south-1b  (map_public_ip=false)
```

**My observation:**
- Public subnets have map_public_ip=true  EC2 here gets public IP
- Private subnets have map_public_ip=false  EC2 here has no public IP
- EC2 is in private-app-b (10.0.4.x)  confirmed by the 10.0.4.121 IP we saw

[Screenshot: 07_subnets_console.png]
> VPC -> Subnets showing all 6 subnets with their CIDRs and AZs

---

**7c. EC2 Instance**
```
EC2 -> Instances
handson-dev-app: running
Private IP: 10.0.4.121
Subnet: private-app-b (NOT public)
Security group: handson-dev-app-sg
```

**My observation:**
- EC2 is in private subnet  cannot be reached directly from internet
- Only the ALB can send HTTP traffic to it (security group rule)
- Only your IP (103.82.209.148/32) can SSH to it

[Screenshot: 08_ec2_instance_console.png]
> EC2 console showing handson-dev-app instance running in private subnet

---

**7d. ALB and Target Group**
```
EC2 -> Load Balancers -> handson-dev-alb
State: active
DNS: handson-dev-alb-66391407.ap-south-1.elb.amazonaws.com

EC2 -> Target Groups -> handson-dev-tg
Target: 10.0.4.121:80
Health status: healthy
```

**My observation:**
- ALB is active and serving traffic
- Target (EC2) is healthy  /health endpoint returns 200
- ALB spans both public subnets (ap-south-1a and ap-south-1b) for HA

[Screenshot: 09_alb_console.png]
> EC2 -> Load Balancers showing handson-dev-alb active

[Screenshot: 10_target_group_healthy.png]
> EC2 -> Target Groups showing target as healthy

---

**7e. RDS Database**
```
RDS -> Databases -> handson-dev-mysql
Status: available
Engine: MySQL 8.0.45
Instance class: db.t3.micro
Endpoint: handson-dev-mysql.chew84266ne7.ap-south-1.rds.amazonaws.com:3306
Publicly accessible: No
Multi-AZ: No
```

**My observation:**
- RDS is NOT publicly accessible  only EC2 can reach it via port 3306
- Single-AZ for dev (Multi-AZ would double the cost)
- Endpoint format: identifier.random.region.rds.amazonaws.com:port

[Screenshot: 11_rds_console.png]
> RDS console showing handson-dev-mysql available

---

**7f. Security Groups  Chain Verification**
```
handson-dev-alb-sg:
  Inbound: 80 from 0.0.0.0/0, 443 from 0.0.0.0/0
  Outbound: all

handson-dev-app-sg:
  Inbound: 80 from sg-0a28421ce4d708e41 (ALB SG only!)
           22 from 103.82.209.148/32 (your IP only!)
  Outbound: all

handson-dev-rds-sg:
  Inbound: 3306 from sg-0d4cdc3be1fb345e7 (App SG only!)
  Outbound: all
```

**My observation:**
- Security groups are CHAINED: ALB -> EC2 -> RDS
- EC2 only accepts HTTP from ALB  not from internet directly
- RDS only accepts MySQL from EC2  not from internet at all
- This is defense in depth  each layer only trusts the layer above it

[Screenshot: 12_security_groups_chain.png]
> EC2 -> Security Groups showing the chained rules

---

### Step 8  terraform destroy

**Command run:**
```
terraform destroy -var-file="terraform.tfvars" -var="db_password=Handson2026Pass!"
```

**Typed:** yes

**Destruction order (Terraform handles automatically):**
```
1. Route table associations (instant)
2. DB instance (1m52s  slowest)
3. ALB listener (instant)
4. ALB (26s)
5. NAT Gateway (1m1s)
6. Auto Scaling Group (5m42s  waits for EC2 termination)
7. EIP, IGW, subnets (instant)
8. Security groups, launch template (instant)
9. VPC (last  everything else must be gone first)
```

**Final output:**
```
Destroy complete! Resources: 28 destroyed.
```

**My observation:**
- ASG took 5m42s  it waits for EC2 instances to terminate gracefully
- Terraform destroys in correct dependency order automatically
- VPC is always last  it cannot be deleted while resources exist inside it
- All 28 resources destroyed cleanly  AWS account is clean

**Verification:** OK - All resources destroyed, billing stopped

[Screenshot: 13_terraform_destroy.png]
> Terminal showing "Destroy complete! Resources: 28 destroyed"

[Screenshot: 14_vpc_gone_console.png]
> VPC console showing handson-dev-vpc no longer exists

---

## Summary

### All Resources Created and Destroyed

| Resource | ID | Status |
|----------|-----|--------|
| VPC | vpc-005a59b1a48818658 | Destroyed |
| Public Subnet A | subnet-06b9c76cb41c6ceba | Destroyed |
| Public Subnet B | subnet-0653b835e4b7de436 | Destroyed |
| Private App Subnet A | subnet-0ebb6ccf04efd9ae0 | Destroyed |
| Private App Subnet B | subnet-0626f1b6d9b71c8b6 | Destroyed |
| Private DB Subnet A | subnet-065f8001f575628ec | Destroyed |
| Private DB Subnet B | subnet-0e6643693bf41216a | Destroyed |
| Internet Gateway | igw-0a9e1d039bf3738e1 | Destroyed |
| Elastic IP | eipalloc-01761785802743a09 | Destroyed |
| NAT Gateway | nat-09e4438f1662bef97 | Destroyed |
| Public Route Table | rtb-0b30443c8f4f9a32f | Destroyed |
| Private Route Table | rtb-0062069bf6a1dcef1 | Destroyed |
| ALB Security Group | sg-0a28421ce4d708e41 | Destroyed |
| App Security Group | sg-0d4cdc3be1fb345e7 | Destroyed |
| RDS Security Group | sg-0b92a9d8e8ad47512 | Destroyed |
| ALB | handson-dev-alb | Destroyed |
| Target Group | handson-dev-tg | Destroyed |
| ALB Listener | port 80 | Destroyed |
| Launch Template | lt-0561291321a221e46 | Destroyed |
| Auto Scaling Group | handson-dev-asg | Destroyed |
| DB Subnet Group | handson-dev-db-subnet-group | Destroyed |
| RDS MySQL | handson-dev-mysql | Destroyed |

### Command Summary

| Command | Touched AWS? | Result |
|---------|-------------|--------|
| terraform init | No | Downloaded AWS provider v5.100.0 |
| terraform plan | No (read-only) | Showed 28 resources to create |
| terraform apply (1st) | Yes | 27 created, RDS failed (backup error) |
| terraform apply (2nd) | Yes | RDS failed (password error) |
| terraform apply (3rd) | Yes | RDS created  all 28 done |
| terraform destroy | Yes | All 28 resources deleted |

### Key Observations from This Project

1. **Terraform is idempotent**  re-running apply only creates what is missing
2. **Free tier has restrictions**  backup_retention_period must be 0 for RDS
3. **RDS password restrictions**  no @, /, ", or spaces allowed
4. **Duplicate resources across files** cause init failure  each resource declared once
5. **ASG takes longest to destroy** (~5 min)  waits for EC2 graceful termination
6. **NAT Gateway takes longest to create** (~2 min)  needs EIP + public subnet
7. **Security groups are chained**  ALB -> EC2 -> RDS, each only trusts layer above
8. **EC2 in private subnet**  only ALB can reach it, not internet directly
9. **VPC destroyed last**  all resources inside must be gone first
10. **Data source resolved AMI**  ami-0999036d4c4235ceb (latest AL2023 in ap-south-1)

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| NAT Gateway | ~10 minutes | ~$0.01 |
| RDS db.t3.micro | ~10 minutes | ~$0.003 |
| EC2 t3.micro | ~10 minutes | ~$0.001 |
| ALB | ~10 minutes | ~$0.001 |
| **Total** | | **~$0.015** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | 00_aws_cli_auth.png | aws sts get-caller-identity output | Add screenshot |
| 2 | 00_my_public_ip.png | Your public IP 103.82.209.148 | Add screenshot |
| 3 | 00_ec2_keypair.png | EC2 Key Pairs showing handson-key | Add screenshot |
| 4 | 01_terraform_init.png | "Terraform has been successfully initialized!" | Add screenshot |
| 5 | 02_terraform_plan.png | "Plan: 28 to add, 0 to change, 0 to destroy" | Add screenshot |
| 6 | 03_terraform_apply_complete.png | All 9 outputs after apply | Add screenshot |
| 7 | 04_alb_browser_response.png | Browser showing EC2 hostname response | Add screenshot |
| 8 | 05_health_endpoint.png | Browser showing /health returning OK | Add screenshot |
| 9 | 06_vpc_console.png | VPC console showing handson-dev-vpc | Add screenshot |
| 10 | 07_subnets_console.png | All 6 subnets with CIDRs and AZs | Add screenshot |
| 11 | 08_ec2_instance_console.png | EC2 instance in private subnet | Add screenshot |
| 12 | 09_alb_console.png | ALB active with DNS name | Add screenshot |
| 13 | 10_target_group_healthy.png | Target group showing healthy target | Add screenshot |
| 14 | 11_rds_console.png | RDS handson-dev-mysql available | Add screenshot |
| 15 | 12_security_groups_chain.png | Security groups showing chained rules | Add screenshot |
| 16 | 13_terraform_destroy.png | "Destroy complete! Resources: 28 destroyed" | Add screenshot |
| 17 | 14_vpc_gone_console.png | VPC console showing no handson-dev-vpc | Add screenshot |

Save all screenshots to:
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.2_terraform_aws_infra\screenshot\

---

Author: Viswanath TGR
LinkedIn: linkedin.com/in/viswanath-tgr-328b11264
Series: AWS Terraform Hands-on - 62 Projects