# Verification & Validation — Project 11.6 Load Balancer Integration

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ALB | EC2 → Load Balancers | `alb-11-6`, State = **active**, Scheme = internet-facing |
| ALB Subnets | Description tab | 2 public subnets in different AZs |
| Target Group | EC2 → Target Groups | `tg-web-11-6`, Protocol=HTTP, Port=80 |
| Target Health | Targets tab | Both instances = **healthy** |
| Listener | Listeners tab | HTTP:80 → forward to `tg-web-11-6` |
| Web EC2s | EC2 → Instances | Running, **no** public IP (only ALB is public) |

📸 Screenshot: Target group Targets tab showing both instances as healthy  
📸 Screenshot: ALB DNS name in description tab  
📸 Screenshot: Browser/curl response showing hostname from one of the instances

---

## 2. AWS CLI Verification

```bash
# 2.1 ALB state
aws elbv2 describe-load-balancers --names alb-11-6 \
  --query "LoadBalancers[0].{State:State.Code,DNS:DNSName,Scheme:Scheme}"
# Expected: State=active

# 2.2 Target health — both must be healthy
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State,Reason:TargetHealth.Reason}"
# Expected: both healthy

# 2.3 Load balancing — run 10 requests, confirm both instances respond
for i in $(seq 1 10); do curl -s http://$ALB_DNS | grep -o "hostname.*"; done
# Expected: mix of both instance hostnames

# 2.4 Failover test — stop one instance
aws ec2 stop-instances --instance-ids $WEB_INSTANCE_A
sleep 60
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: instance-A = unhealthy, instance-B = healthy
# All curl requests now return only instance-B hostname

# 2.5 Recovery — restart instance
aws ec2 start-instances --instance-ids $WEB_INSTANCE_A
# Wait ~60s for health check to pass
aws elbv2 describe-target-health --target-group-arn $TG_ARN
# Expected: both healthy again
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_lb.main
# aws_lb_listener.http
# aws_lb_target_group.web
# aws_lb_target_group_attachment.web_a
# aws_lb_target_group_attachment.web_b

terraform state show aws_lb.main
# Shows: arn, dns_name, internal=false, load_balancer_type=application

terraform output alb_dns_name
# Expected: alb-11-6-xxx.us-east-1.elb.amazonaws.com

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --names alb-11-6 \
  --query "LoadBalancers[0].DNSName" --output text)

# Health endpoint directly
curl http://$ALB_DNS/health
# Expected: OK

# Confirm load distribution
for i in $(seq 1 20); do curl -s http://$ALB_DNS | grep -o "ip-[0-9-]*"; done | sort | uniq -c
# Expected: roughly equal counts for both instance IPs
```

---

## 5. Expected Successful Outputs

**CLI — target health:**
```json
[
  { "Target": "i-0abc123", "Health": "healthy", "Reason": null },
  { "Target": "i-0def456", "Health": "healthy", "Reason": null }
]
```

**Load distribution (20 requests):**
```
  10 ip-10-0-1-xxx
  10 ip-10-0-2-xxx
```

**After stopping one instance:**
```json
[
  { "Target": "i-0abc123", "Health": "unhealthy", "Reason": "Target.FailedHealthChecks" },
  { "Target": "i-0def456", "Health": "healthy",   "Reason": null }
]
```

---

## 6. Verification Checklist

- [ ] ALB state = active, scheme = internet-facing
- [ ] ALB spans 2 public subnets in different AZs
- [ ] Target group health check path = `/health`
- [ ] Both instances = healthy
- [ ] `curl http://<ALB_DNS>` returns response
- [ ] Multiple requests show different hostnames (load balancing works)
- [ ] Stopping one instance → health check fails → all traffic to other instance
- [ ] Restarting instance → health check passes → traffic resumes to both
- [ ] Web instances have no public IPs
- [ ] `terraform plan` shows no changes
