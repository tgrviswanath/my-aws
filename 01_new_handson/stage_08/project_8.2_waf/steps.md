# Steps — Project 8.2 WAF Application Protection

## Phase 1 — Deploy

```bash
cd terraform
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names handson-flask-api-alb \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

terraform init
terraform apply -var="alb_arn=$ALB_ARN" -auto-approve
terraform output waf_arn
```

---

## Phase 2 — Test SQL Injection Blocking

```bash
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"

# Normal request — should work
curl -s "$ALB_URL/items" | python3 -m json.tool

# SQL injection attempt — should be BLOCKED (403)
curl -v "$ALB_URL/items?id=1' OR '1'='1"
# Expected: HTTP 403 Forbidden

# XSS attempt — should be BLOCKED
curl -v "$ALB_URL/items?name=<script>alert('xss')</script>"
# Expected: HTTP 403 Forbidden
```

---

## Phase 3 — Test Rate Limiting

```bash
# Send 110 requests quickly — should start getting 429 after 100
for i in {1..110}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ALB_URL/health)
  echo "Request $i: $STATUS"
done
# First 100: 200 OK
# After 100: 429 Too Many Requests (or 403 depending on WAF config)
```

---

## Phase 4 — Block an IP

```bash
# Get your current IP
MY_IP=$(curl -s https://checkip.amazonaws.com)

# Add to blocked IP set
IP_SET_ARN=$(terraform output -raw blocked_ip_set)
IP_SET_ID=$(echo $IP_SET_ARN | cut -d'/' -f3)
IP_SET_NAME="${var.project}-blocked-ips"

# Get current lock token
LOCK_TOKEN=$(aws wafv2 get-ip-set \
  --name $IP_SET_NAME \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --query LockToken --output text)

# Add your IP to blocked list
aws wafv2 update-ip-set \
  --name $IP_SET_NAME \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --addresses "$MY_IP/32" \
  --lock-token $LOCK_TOKEN

# Test — should now be blocked
curl -v $ALB_URL/health
# Expected: 403 Forbidden

# Remove your IP (unblock yourself)
aws wafv2 update-ip-set \
  --name $IP_SET_NAME \
  --scope REGIONAL \
  --id $IP_SET_ID \
  --addresses [] \
  --lock-token $(aws wafv2 get-ip-set --name $IP_SET_NAME --scope REGIONAL --id $IP_SET_ID --query LockToken --output text)
```

---

## Phase 5 — View WAF Logs

```bash
# Query WAF logs in CloudWatch
aws logs filter-log-events \
  --log-group-name "aws-waf-logs-handson" \
  --filter-pattern '{ $.action = "BLOCK" }' \
  --start-time $(date -d '1 hour ago' +%s000) \
  | python3 -m json.tool
```

---

## Screenshots to Take
- [ ] WAF Web ACL with all rules listed
- [ ] SQL injection attempt returning 403
- [ ] Rate limit test showing 429 after threshold
- [ ] WAF metrics in CloudWatch (blocked requests)
- [ ] WAF logs showing blocked request details
- [ ] IP set with blocked IP added
