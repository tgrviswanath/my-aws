# Steps — Project 2.3 ALB vs NLB Comparison Lab

## Phase 1 — Deploy ALB with Path-Based Routing

### 1.1 Create Two Target Groups
- `tg-web`: for `/` path → EC2 instances serving HTML
- `tg-api`: for `/api/*` path → EC2 instances serving JSON

### 1.2 Create ALB with Path Rules
1. **EC2** → **Load Balancers** → **Create** → Application Load Balancer
2. Name: `compare-alb`
3. Subnets: public subnets
4. Listener HTTP:80 → default action: forward to `tg-web`
5. After creation: **Listeners** → **View/edit rules**
6. Add rule: IF path is `/api/*` THEN forward to `tg-api`

### 1.3 Test ALB Path Routing
```bash
ALB_DNS="compare-alb-xxxx.us-east-1.elb.amazonaws.com"

# Should hit web target group
curl http://$ALB_DNS/

# Should hit API target group
curl http://$ALB_DNS/api/users

# Should return 404 (no rule matches)
curl http://$ALB_DNS/unknown
```

---

## Phase 2 — Deploy NLB

### 2.1 Create NLB
1. **EC2** → **Load Balancers** → **Create** → Network Load Balancer
2. Name: `compare-nlb`
3. Scheme: Internet-facing
4. Subnets: public subnets (assign Elastic IPs)
5. Listener TCP:80 → forward to target group

### 2.2 Test NLB
```bash
NLB_DNS="compare-nlb-xxxx.us-east-1.elb.amazonaws.com"

# Basic connectivity
curl http://$NLB_DNS/

# Check source IP preservation (NLB passes real client IP)
# On the EC2 instance, check access logs:
# ALB: source IP = ALB's IP
# NLB: source IP = your real IP
```

---

## Phase 3 — AWS CLI Comparison

```bash
# List all load balancers with type
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[*].{Name:LoadBalancerName,Type:Type,DNS:DNSName,State:State.Code}"

# View ALB listener rules (path routing)
aws elbv2 describe-rules \
  --listener-arn $ALB_LISTENER_ARN \
  --query "Rules[*].{Priority:Priority,Conditions:Conditions,Actions:Actions}"

# View NLB attributes
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn $NLB_ARN
```

---

## Phase 4 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
terraform output
```

---

## Phase 5 — Performance Comparison Test

```bash
# Install Apache Bench
sudo yum install -y httpd-tools

# Benchmark ALB
ab -n 1000 -c 50 http://$ALB_DNS/

# Benchmark NLB
ab -n 1000 -c 50 http://$NLB_DNS/

# Compare:
# - Requests per second
# - Time per request
# - Connection times
```

---

## Screenshots to Take
- [ ] ALB with path-based routing rules visible
- [ ] NLB with Elastic IP assigned
- [ ] `curl /api/*` hitting different target group than `curl /`
- [ ] Apache Bench results for both (compare latency)
- [ ] Source IP difference in EC2 access logs (ALB vs NLB)
- [ ] `terraform apply` success output
