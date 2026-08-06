# Verification & Validation — Project 2.2 Multi-Tier Web Application

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ALB | EC2 → Load Balancers | `app-alb`, State = **active**, Scheme = internet-facing |
| ALB Subnets | Description tab | Both **public** subnets across 2 AZs |
| Target Group | EC2 → Target Groups | `app-tg`, all targets = **healthy** |
| ASG | EC2 → Auto Scaling Groups | `app-asg`, Desired=2, Min=1, Max=4 |
| ASG Instances | Activity tab | 2 instances in service |
| EC2 Instances | EC2 → Instances | Running in **private-app** subnets, no public IP |
| RDS | RDS → Databases | Available, in **private-db** subnets, Public access = No |
| SG Chain | EC2 → Security Groups | alb-sg → app-sg → rds-sg (each references previous) |

📸 Screenshot: ALB state = active with DNS name  
📸 Screenshot: Target group showing 2 healthy instances  
📸 Screenshot: ASG showing desired/min/max and 2 instances in service  
📸 Screenshot: Browser showing different hostnames on refresh (load balancing)

---

## 2. AWS CLI Verification

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --names app-alb \
  --query "LoadBalancers[0].DNSName" --output text)

# 2.1 ALB active
aws elbv2 describe-load-balancers --names app-alb \
  --query "LoadBalancers[0].{State:State.Code,Scheme:Scheme,DNS:DNSName}"
# Expected: State=active, Scheme=internet-facing

# 2.2 All targets healthy
TG_ARN=$(aws elbv2 describe-target-groups --names app-tg \
  --query "TargetGroups[0].TargetGroupArn" --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: all healthy

# 2.3 ASG desired = running
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-asg \
  --query "AutoScalingGroups[0].{Desired:DesiredCapacity,Min:MinSize,Max:MaxSize,Running:Instances[?LifecycleState=='InService']|length(@)}"
# Expected: Desired=2, Min=1, Max=4, Running=2

# 2.4 Load balancing — different hostnames
for i in {1..5}; do curl -s http://$ALB_DNS | grep "App Server"; done
# Expected: mix of 2 different hostnames

# 2.5 Health endpoint
curl -s http://$ALB_DNS/health
# Expected: OK

# 2.6 EC2 instances in private subnets (no public IP)
aws ec2 describe-instances \
  --filters "Name=tag:aws:autoscaling:groupName,Values=app-asg" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,PublicIP:PublicIpAddress,Subnet:SubnetId}"
# Expected: PublicIP = null for all instances

# 2.7 Run health checker
python code/health_check.py
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_lb.app
# aws_lb_listener.http
# aws_lb_target_group.app
# aws_autoscaling_group.app
# aws_launch_template.app
# aws_security_group.alb
# aws_security_group.app
# aws_security_group.rds
# aws_db_instance.mysql

terraform state show aws_autoscaling_group.app
# Shows: desired_capacity=2, min_size=1, max_size=4,
#        vpc_zone_identifier (private-app subnets)

terraform output alb_dns_name
# Expected: app-alb-xxx.us-east-1.elb.amazonaws.com

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Auto Scaling Recovery

```bash
# Get one instance ID from ASG
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-asg \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)

# Terminate it — ASG should replace it automatically
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# Watch replacement (takes ~2-3 minutes)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: one unhealthy → then replaced with new healthy instance

# ALB continues serving during replacement
curl -s http://$ALB_DNS/health
# Expected: OK throughout (other instance handles traffic)
```

---

## 5. Expected Successful Outputs

**Target health:**
```json
[
  { "Target": "i-0abc123", "Health": "healthy" },
  { "Target": "i-0def456", "Health": "healthy" }
]
```

**Load balancing (5 requests):**
```
<h1>App Server: ip-10-0-3-xxx</h1>
<h1>App Server: ip-10-0-4-xxx</h1>
<h1>App Server: ip-10-0-3-xxx</h1>
<h1>App Server: ip-10-0-4-xxx</h1>
<h1>App Server: ip-10-0-3-xxx</h1>
```

**health_check.py output:**
```
Tier 1 — ALB: ✅ active
Tier 1 — Target Group: ✅ 2/2 healthy
Tier 2 — EC2: ✅ 2 instances running
Tier 3 — RDS: ✅ available
Overall: ALL SYSTEMS HEALTHY
```

---

## 6. Verification Checklist

- [ ] ALB state = active, scheme = internet-facing, in public subnets
- [ ] Target group `app-tg`: all 2 instances healthy
- [ ] ASG: desired=2, min=1, max=4
- [ ] EC2 instances in private-app subnets, no public IPs
- [ ] `curl http://<ALB_DNS>` returns HTML response
- [ ] `curl http://<ALB_DNS>/health` returns OK
- [ ] Multiple requests show different hostnames (load balancing works)
- [ ] RDS in private-db subnets, public access = No
- [ ] SG chain: alb-sg → app-sg → rds-sg (no direct internet to app/db)
- [ ] ASG replaces terminated instance automatically
- [ ] `terraform plan` shows no changes
- [ ] `health_check.py` shows ALL SYSTEMS HEALTHY

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
