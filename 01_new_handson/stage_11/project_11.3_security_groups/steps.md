# Steps — Project 11.3 Security Groups Deep Dive

## Phase 1 — Console

### 1.1 Create VPC and Subnets
- VPC: `vpc-11-3`, CIDR: `10.0.0.0/16`
- Public subnet: `10.0.1.0/24`
- Private subnet: `10.0.2.0/24`
- Attach IGW, create route tables (same as 11.1)

### 1.2 Create Security Groups (in order — each references the previous)

**SG 1 — ALB** (`alb-sg-11-3`):
- Inbound: HTTP 80 from `0.0.0.0/0`, HTTPS 443 from `0.0.0.0/0`
- Outbound: All traffic

**SG 2 — Web** (`web-sg-11-3`):
- Inbound: HTTP 80 from `alb-sg-11-3` (select SG, not CIDR)
- Inbound: SSH 22 from My IP
- Outbound: All traffic

**SG 3 — App** (`app-sg-11-3`):
- Inbound: TCP 8080 from `web-sg-11-3`
- Inbound: SSH 22 from `web-sg-11-3` (bastion hop)
- Outbound: All traffic

**SG 4 — DB** (`db-sg-11-3`):
- Inbound: MySQL 3306 from `app-sg-11-3`
- Inbound: SSH 22 from `app-sg-11-3`
- Outbound: All traffic

### 1.3 Launch EC2 Instances
- Web EC2: public subnet, `web-sg-11-3`
- App EC2: private subnet, `app-sg-11-3`
- DB EC2: private subnet, `db-sg-11-3`

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<your-vpc-id>

# ALB SG
ALB_SG=$(aws ec2 create-security-group \
  --group-name alb-sg-11-3 --description "ALB SG" \
  --vpc-id $VPC_ID --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --group-id $ALB_SG \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $ALB_SG \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# Web SG
WEB_SG=$(aws ec2 create-security-group \
  --group-name web-sg-11-3 --description "Web SG" \
  --vpc-id $VPC_ID --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --group-id $WEB_SG \
  --protocol tcp --port 80 --source-group $ALB_SG
aws ec2 authorize-security-group-ingress --group-id $WEB_SG \
  --protocol tcp --port 22 --cidr <MY_IP>/32

# App SG
APP_SG=$(aws ec2 create-security-group \
  --group-name app-sg-11-3 --description "App SG" \
  --vpc-id $VPC_ID --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --group-id $APP_SG \
  --protocol tcp --port 8080 --source-group $WEB_SG
aws ec2 authorize-security-group-ingress --group-id $APP_SG \
  --protocol tcp --port 22 --source-group $WEB_SG

# DB SG
DB_SG=$(aws ec2 create-security-group \
  --group-name db-sg-11-3 --description "DB SG" \
  --vpc-id $VPC_ID --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --group-id $DB_SG \
  --protocol tcp --port 3306 --source-group $APP_SG
aws ec2 authorize-security-group-ingress --group-id $DB_SG \
  --protocol tcp --port 22 --source-group $APP_SG

echo "SGs: ALB=$ALB_SG WEB=$WEB_SG APP=$APP_SG DB=$DB_SG"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. List all SGs in VPC
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}"

# 2. Inspect DB SG rules — should only allow from App SG
aws ec2 describe-security-groups --group-ids $DB_SG \
  --query "SecurityGroups[0].IpPermissions"

# 3. Test connectivity from Web EC2
ssh -i key.pem ec2-user@<WEB_PUBLIC_IP>
# From web EC2:
curl http://<APP_PRIVATE_IP>:8080    # should succeed
curl http://<DB_PRIVATE_IP>:3306     # should FAIL (web can't reach DB directly)

# 4. Test from App EC2
ssh -i key.pem ec2-user@<APP_PRIVATE_IP>   # hop from web EC2
nc -zv <DB_PRIVATE_IP> 3306               # should succeed (app → db allowed)
nc -zv <WEB_PRIVATE_IP> 80               # should FAIL (app can't reach web on 80)

# 5. Run SG checker
python code/sg_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] 4 security groups created (alb, web, app, db)
- [ ] Web SG allows HTTP only from ALB SG (not 0.0.0.0/0)
- [ ] App SG allows 8080 only from Web SG
- [ ] DB SG allows 3306 only from App SG
- [ ] Web EC2 can reach App EC2 on 8080
- [ ] Web EC2 CANNOT reach DB EC2 on 3306
- [ ] App EC2 can reach DB EC2 on 3306
- [ ] Direct internet access to App/DB EC2 is blocked

---

## Teardown
```bash
terraform destroy
```
