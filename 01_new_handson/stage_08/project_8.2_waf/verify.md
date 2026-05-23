# Verification & Validation — Project 8.2 WAF Application Protection

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| WAF Web ACL | WAF & Shield → Web ACLs | `handson-waf-acl` listed, associated with ALB |
| Rule groups | Web ACL → Rules tab | Core Rule Set, SQL Database, Known Bad Inputs, Rate limit rules listed |
| ALB association | Web ACL → Associated AWS resources | ALB ARN listed |
| WAF Logging | Web ACL → Logging and metrics | Logging enabled → S3 or CloudWatch |
| CloudWatch metrics | CloudWatch → Metrics → WAF | `AllowedRequests`, `BlockedRequests` metrics visible |

📸 Screenshot: WAF Web ACL with all rules listed and priorities  
📸 Screenshot: WAF metrics showing BlockedRequests after running waf_tester.py  
📸 Screenshot: waf_tester.py output showing PASS/FAIL table

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm Web ACL exists
aws wafv2 list-web-acls \
  --scope REGIONAL \
  --query "WebACLs[*].{Name:Name,ARN:ARN,Id:Id}"
# Expected: handson-waf-acl listed

# 2.2 Get Web ACL details and rules
WAF_ARN=$(aws wafv2 list-web-acls --scope REGIONAL \
  --query "WebACLs[?Name=='handson-waf-acl'].ARN" --output text)
WAF_ID=$(aws wafv2 list-web-acls --scope REGIONAL \
  --query "WebACLs[?Name=='handson-waf-acl'].Id" --output text)

aws wafv2 get-web-acl \
  --name handson-waf-acl \
  --scope REGIONAL \
  --id $WAF_ID \
  --query "WebACL.Rules[*].{Name:Name,Priority:Priority,Action:Action}"
# Expected: all rules listed with priorities

# 2.3 Confirm WAF is associated with ALB
aws wafv2 list-resources-for-web-acl \
  --web-acl-arn $WAF_ARN \
  --query "ResourceArns"
# Expected: ALB ARN listed

# 2.4 Test legitimate request — should return 200
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[0].DNSName" --output text)
curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/health
# Expected: 200

# 2.5 Test SQL injection — should return 403
curl -s -o /dev/null -w "%{http_code}" \
  "http://$ALB_DNS/?id=1'+OR+'1'='1"
# Expected: 403

# 2.6 Test XSS — should return 403
curl -s -o /dev/null -w "%{http_code}" \
  "http://$ALB_DNS/?q=<script>alert(1)</script>"
# Expected: 403

# 2.7 Run full WAF test suite
python code/waf_tester.py --url http://$ALB_DNS
# Expected: all attack tests return PASS (blocked), legitimate request returns PASS (allowed)

# 2.8 Check WAF metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value=handson-waf-acl Name=Region,Value=us-east-1 Name=Rule,Value=ALL \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --query "Datapoints[*].Sum"
# Expected: Sum > 0 after running attack tests
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_wafv2_web_acl.main
# aws_wafv2_web_acl_association.alb
# aws_wafv2_web_acl_logging_configuration.main
# aws_cloudwatch_log_group.waf (if logging to CloudWatch)

# 3.2 Inspect Web ACL
terraform state show aws_wafv2_web_acl.main
# Shows: name, default_action=allow, rules with managed rule groups

# 3.3 Confirm outputs
terraform output waf_arn
# Expected: arn:aws:wafv2:us-east-1:123456789012:regional/webacl/handson-waf-acl/xxx

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Attack Simulation

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[0].DNSName" --output text)

echo "=== WAF Verification Tests ==="

# Test 1: Legitimate traffic (should pass)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/health)
[ "$STATUS" = "200" ] && echo "✅ Legitimate request: $STATUS" || echo "❌ Legitimate request: $STATUS"

# Test 2: SQL injection (should be blocked)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/?id=1'+OR+'1'='1")
[ "$STATUS" = "403" ] && echo "✅ SQL injection blocked: $STATUS" || echo "❌ SQL injection NOT blocked: $STATUS"

# Test 3: XSS (should be blocked)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/?q=%3Cscript%3Ealert%281%29%3C%2Fscript%3E")
[ "$STATUS" = "403" ] && echo "✅ XSS blocked: $STATUS" || echo "❌ XSS NOT blocked: $STATUS"

# Test 4: Bad bot user-agent (should be blocked)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -A "sqlmap/1.0" http://$ALB_DNS/)
[ "$STATUS" = "403" ] && echo "✅ Bad bot blocked: $STATUS" || echo "❌ Bad bot NOT blocked: $STATUS"
```

---

## 5. Expected Successful Outputs

**waf_tester.py output:**
```
=== WAF Test Results ===
✅ PASS  Legitimate request     GET /          → 200 OK (allowed as expected)
✅ PASS  SQL injection          ?id=1' OR...   → 403 Blocked
✅ PASS  XSS attack             ?q=<script>    → 403 Blocked
✅ PASS  Bad bot user-agent     sqlmap/1.0     → 403 Blocked
✅ PASS  Path traversal         /../etc/passwd → 403 Blocked

5/5 tests passed — WAF is protecting your application
```

**CloudWatch BlockedRequests metric:**
```json
[5.0]
```

---

## 6. Verification Checklist

- [ ] WAF Web ACL `handson-waf-acl` exists and is REGIONAL scope
- [ ] Web ACL associated with ALB
- [ ] Core Rule Set (OWASP Top 10) rule group active
- [ ] SQL Database rule group active
- [ ] Known Bad Inputs rule group active
- [ ] Rate limiting rule configured
- [ ] WAF logging enabled (S3 or CloudWatch)
- [ ] Legitimate request returns 200 (not over-blocked)
- [ ] SQL injection returns 403
- [ ] XSS returns 403
- [ ] Bad bot user-agent returns 403
- [ ] CloudWatch `BlockedRequests` metric shows count > 0
- [ ] `terraform plan` shows no changes
