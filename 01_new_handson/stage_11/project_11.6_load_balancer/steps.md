# Steps — Project 11.6 Load Balancer Integration

## Phase 1 — Console

### 1.1 Prerequisites
Use the VPC from Project 11.5 (or create a new one with 2 public + 2 private subnets).

### 1.2 Launch 2 Web Server EC2 Instances
- AMI: Amazon Linux 2023
- Type: t3.micro
- Subnets: one in AZ-a, one in AZ-b (private subnets)
- User data (installs a simple web server):
```bash
#!/bin/bash
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from $(hostname -f)</h1>" > /var/www/html/index.html
mkdir -p /var/www/html
echo "OK" > /var/www/html/health
```

### 1.3 Create Target Group
1. **EC2** → **Target Groups** → **Create target group**
2. Type: Instances
3. Name: `tg-web-11-6`
4. Protocol: HTTP, Port: 80
5. VPC: your VPC
6. Health check path: `/health`
7. Healthy threshold: 2, Unhealthy threshold: 2, Interval: 30s
8. Register both EC2 instances

### 1.4 Create Application Load Balancer
1. **EC2** → **Load Balancers** → **Create** → Application Load Balancer
2. Name: `alb-11-6`
3. Scheme: Internet-facing
4. IP type: IPv4
5. VPC: your VPC
6. Subnets: select both PUBLIC subnets (AZ-a and AZ-b)
7. Security group: `alb-sg` (HTTP 80 from 0.0.0.0/0)
8. Listener: HTTP 80 → Forward to `tg-web-11-6`
9. Create

### 1.5 Test
- Wait for ALB to be Active (~2 minutes)
- Copy ALB DNS name
- `curl http://<ALB_DNS_NAME>` — should return one of the web servers
- Refresh multiple times — should alternate between instances

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<vpc-id>
PUB_SUBNET_A=<public-subnet-a-id>
PUB_SUBNET_B=<public-subnet-b-id>
WEB_INSTANCE_A=<instance-a-id>
WEB_INSTANCE_B=<instance-b-id>
ALB_SG=<alb-sg-id>

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name tg-web-11-6 \
  --protocol HTTP --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 2 \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# Register instances
aws elbv2 register-targets --target-group-arn $TG_ARN \
  --targets Id=$WEB_INSTANCE_A Id=$WEB_INSTANCE_B

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name alb-11-6 \
  --subnets $PUB_SUBNET_A $PUB_SUBNET_B \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" --output text)
echo "ALB DNS: $ALB_DNS"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
terraform output alb_dns_name
```

---

## Phase 4 — Verify

```bash
ALB_DNS=<your-alb-dns>

# 1. Check ALB state
aws elbv2 describe-load-balancers --names alb-11-6 \
  --query "LoadBalancers[0].{State:State.Code,DNS:DNSName}"

# 2. Check target health
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"

# 3. Test load balancing — run 10 requests and see distribution
for i in $(seq 1 10); do curl -s http://$ALB_DNS | grep -o "hostname.*"; done

# 4. Simulate failure — stop one instance
aws ec2 stop-instances --instance-ids $WEB_INSTANCE_A
# Wait ~60s for health check to mark it unhealthy
aws elbv2 describe-target-health --target-group-arn $TG_ARN
# All traffic should now go to instance B only

# 5. Restart instance — verify it rejoins
aws ec2 start-instances --instance-ids $WEB_INSTANCE_A
# Wait for health check to pass — traffic resumes to both

# 6. Run checker
python code/alb_checker.py --alb-name alb-11-6
```

### Verification Checklist
- [ ] ALB created in 2 public subnets, state = active
- [ ] Target group with 2 instances, both healthy
- [ ] `curl http://<ALB_DNS>` returns response
- [ ] Multiple requests show different hostnames (load balancing works)
- [ ] Stopping one instance → health check fails → traffic shifts to other
- [ ] Restarting instance → health check passes → traffic resumes to both
- [ ] Web instances have no public IPs (only ALB is public-facing)

---

## Teardown
```bash
terraform destroy
# ALB costs ~$0.008/hr + LCU charges
```
