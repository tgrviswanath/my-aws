# Verification & Validation — Project 2.3 ALB vs NLB Comparison Lab

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ALB | EC2 → Load Balancers | `compare-alb`, Type = **application**, State = active |
| NLB | EC2 → Load Balancers | `compare-nlb`, Type = **network**, State = active |
| ALB Listener Rules | Listeners → View/edit rules | `/api/*` → `tg-api`, default → `tg-web` |
| NLB Elastic IP | Load Balancer → Description | Static IP assigned per AZ |
| Target Groups | EC2 → Target Groups | `tg-web` and `tg-api`, both healthy |

📸 Screenshot: Both ALB and NLB listed with their types  
📸 Screenshot: ALB listener rules showing path-based routing  
📸 Screenshot: NLB with Elastic IP assigned  
📸 Screenshot: load_test.py comparison output showing latency difference

---

## 2. AWS CLI Verification

```bash
# 2.1 Both LBs exist with correct types
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?contains(LoadBalancerName,'compare')].{Name:LoadBalancerName,Type:Type,State:State.Code,DNS:DNSName}"
# Expected: compare-alb (application, active), compare-nlb (network, active)

ALB_DNS=$(aws elbv2 describe-load-balancers --names compare-alb \
  --query "LoadBalancers[0].DNSName" --output text)
NLB_DNS=$(aws elbv2 describe-load-balancers --names compare-nlb \
  --query "LoadBalancers[0].DNSName" --output text)

# 2.2 ALB path routing — / hits web TG
curl -s http://$ALB_DNS/
# Expected: HTML response from web target group

# 2.3 ALB path routing — /api/* hits api TG
curl -s http://$ALB_DNS/api/users
# Expected: JSON response from api target group

# 2.4 ALB listener rules show path conditions
ALB_ARN=$(aws elbv2 describe-load-balancers --names compare-alb \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN \
  --query "Listeners[0].ListenerArn" --output text)
aws elbv2 describe-rules --listener-arn $LISTENER_ARN \
  --query "Rules[*].{Priority:Priority,Conditions:Conditions[*].Values,Actions:Actions[*].Type}"
# Expected: rule with /api/* condition

# 2.5 NLB basic connectivity
curl -s http://$NLB_DNS/
# Expected: HTML response

# 2.6 Source IP difference — ALB replaces client IP, NLB preserves it
# Check EC2 access logs:
# ALB: source IP = ALB's IP range (10.0.x.x)
# NLB: source IP = your real public IP
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_lb.alb
# aws_lb.nlb
# aws_lb_listener.alb_http
# aws_lb_listener.nlb_tcp
# aws_lb_listener_rule.api_path
# aws_lb_target_group.web
# aws_lb_target_group.api

terraform state show aws_lb.alb
# Shows: load_balancer_type=application, internal=false

terraform state show aws_lb.nlb
# Shows: load_balancer_type=network, internal=false

terraform output
# Expected: alb_dns, nlb_dns

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Performance Comparison Test

```bash
# Install Apache Bench
sudo yum install -y httpd-tools   # Amazon Linux
# or: sudo apt install -y apache2-utils  # Ubuntu

# Benchmark ALB (100 requests, 10 concurrent)
ab -n 100 -c 10 http://$ALB_DNS/ 2>&1 | grep -E "Requests per second|Time per request|Failed"

# Benchmark NLB
ab -n 100 -c 10 http://$NLB_DNS/ 2>&1 | grep -E "Requests per second|Time per request|Failed"

# Or use the Python load tester
pip install requests
python code/load_test.py \
  --url http://$ALB_DNS \
  --compare-url http://$NLB_DNS \
  --requests 200
```

---

## 5. Expected Successful Outputs

**LB types:**
```json
[
  { "Name": "compare-alb", "Type": "application", "State": "active" },
  { "Name": "compare-nlb", "Type": "network",     "State": "active" }
]
```

**ALB path routing:**
```
curl /        → <h1>Web Server</h1>     (tg-web)
curl /api/*   → {"status":"ok"}         (tg-api)
```

**load_test.py comparison:**
```
=== Load Test Results ===
ALB:  P50=12ms  P95=28ms  P99=45ms  RPS=820
NLB:  P50=8ms   P95=18ms  P99=30ms  RPS=1240
NLB is ~35% faster at P95 latency
```

---

## 6. Verification Checklist

- [ ] ALB type = application, state = active
- [ ] NLB type = network, state = active
- [ ] ALB listener rule: `/api/*` → `tg-api`
- [ ] ALB default rule: `*` → `tg-web`
- [ ] `curl /` returns web response (tg-web)
- [ ] `curl /api/*` returns api response (tg-api)
- [ ] NLB has static Elastic IP per AZ
- [ ] NLB basic connectivity works
- [ ] Source IP difference confirmed in EC2 access logs
- [ ] Performance comparison recorded (ALB vs NLB latency)
- [ ] `terraform plan` shows no changes
