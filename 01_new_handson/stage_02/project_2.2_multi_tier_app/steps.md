# Steps — Project 2.2 Multi-Tier Web Application

## Prerequisites
- VPC from Project 2.1 must exist (or use Terraform outputs)
- Key pair created (from Project 1.2)

---

## Phase 1 — Console

### 1.1 Create Security Groups (in order)

**ALB Security Group** (`alb-sg`):
- Inbound: HTTP 80 from `0.0.0.0/0`
- Inbound: HTTPS 443 from `0.0.0.0/0`
- Outbound: All

**EC2 Security Group** (`app-sg`):
- Inbound: HTTP 80 from `alb-sg` only
- Inbound: SSH 22 from your IP only
- Outbound: All

**RDS Security Group** (`rds-sg`):
- Inbound: MySQL 3306 from `app-sg` only
- Outbound: All

### 1.2 Create Target Group
1. **EC2** → **Target Groups** → **Create**
2. Type: Instances
3. Name: `app-tg`
4. Protocol: HTTP, Port: 80
5. VPC: `handson-vpc`
6. Health check path: `/health`
7. Healthy threshold: 2, Unhealthy: 3

### 1.3 Create ALB
1. **EC2** → **Load Balancers** → **Create** → Application Load Balancer
2. Name: `app-alb`
3. Scheme: Internet-facing
4. Subnets: both **public** subnets
5. Security group: `alb-sg`
6. Listener: HTTP:80 → forward to `app-tg`

### 1.4 Create Launch Template
1. **EC2** → **Launch Templates** → **Create**
2. Name: `app-lt`
3. AMI: Amazon Linux 2023
4. Instance type: `t3.micro`
5. Key pair: your key
6. Security group: `app-sg`
7. User data:
```bash
#!/bin/bash
yum update -y
yum install -y nginx
systemctl start nginx
systemctl enable nginx
cat > /usr/share/nginx/html/index.html << 'EOF'
<h1>App Server: $(hostname)</h1>
<p>AZ: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
EOF
# Health check endpoint
echo "OK" > /usr/share/nginx/html/health
```

### 1.5 Create Auto Scaling Group
1. **EC2** → **Auto Scaling Groups** → **Create**
2. Name: `app-asg`
3. Launch template: `app-lt`
4. VPC: `handson-vpc`
5. Subnets: both **private-app** subnets
6. Attach to load balancer: `app-tg`
7. Desired: 2, Min: 1, Max: 4
8. Health check: ELB, grace period: 60s

### 1.6 Create RDS in Private Subnet
- Follow Project 1.4 steps but use `handson-vpc` and `private-db` subnets
- Security group: `rds-sg`

---

## Phase 2 — AWS CLI

```bash
# Get VPC and subnet IDs from Project 2.1 outputs
VPC_ID="vpc-xxxxxxxxxx"
PUB_SUBNET_A="subnet-xxxxxxxxxx"
PUB_SUBNET_B="subnet-xxxxxxxxxx"
PRIV_APP_A="subnet-xxxxxxxxxx"
PRIV_APP_B="subnet-xxxxxxxxxx"

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name app-alb \
  --subnets $PUB_SUBNET_A $PUB_SUBNET_B \
  --security-groups $ALB_SG_ID \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# Create Target Group
TG_ARN=$(aws elbv2 create-target-group \
  --name app-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path /health \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# Create Listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# Get ALB DNS name
aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" --output text
```

---

## Phase 3 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Get ALB DNS
terraform output alb_dns_name
```

---

## Phase 4 — Verify

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test load balancing — run multiple times, should see different hostnames
for i in {1..5}; do
  curl -s http://$ALB_DNS | grep "App Server"
done

# Test health check
curl http://$ALB_DNS/health

# Verify Auto Scaling instances are healthy
aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN
```

---

## Phase 5 — Test Auto Scaling

```bash
# Manually scale up
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name app-asg \
  --desired-capacity 3

# Watch instances register with ALB
watch -n 5 "aws elbv2 describe-target-health --target-group-arn $TG_ARN"

# Scale back down
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name app-asg \
  --desired-capacity 2
```

---

## Screenshots to Take
- [ ] ALB in Active state with DNS name
- [ ] Target group showing 2 healthy instances
- [ ] Browser hitting ALB DNS — showing different hostnames on refresh
- [ ] Auto Scaling Group with desired/min/max settings
- [ ] Security group chain (ALB → EC2 → RDS)
- [ ] RDS in private subnet, not publicly accessible
- [ ] `terraform apply` success output
