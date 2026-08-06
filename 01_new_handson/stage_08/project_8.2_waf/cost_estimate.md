# Cost Estimate — Project 8.2: AWS WAF v2

## Pricing Model (us-east-1, as of 2024)

| Resource | Unit Price | Notes |
|----------|-----------|-------|
| Web ACL | $5.00 / month | Per Web ACL |
| Rule | $1.00 / rule / month | Each rule or rule group counts |
| Requests | $0.60 / million requests | Inspected by WAF |
| Bot Control | $10.00 / month | Optional add-on rule group |
| Fraud Control | $10.00 / month | Optional account takeover protection |

---

## Free Tier

AWS WAF has **no free tier**. Charges begin immediately upon Web ACL creation.

However, Shield Standard (basic DDoS protection) is always free.

---

## Scenario Estimates

### Minimal Setup (1 Web ACL, 3 rules, low traffic)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Web ACL | 1 | $5.00 |
| Managed rule groups (Core + KnownBad) | 2 | $2.00 |
| Rate-based rule | 1 | $1.00 |
| IP set rule | 1 | $1.00 |
| Requests (100K/day = 3M/month) | 3M | $1.80 |
| **Total** | | **~$10.80/month** |

### Medium Traffic (1 Web ACL, 5 rules, 50M requests/month)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Web ACL | 1 | $5.00 |
| Rules (managed groups + custom) | 5 | $5.00 |
| Requests (50M/month) | 50M | $30.00 |
| CloudWatch Logs (5 GB) | 5 GB | $2.50 |
| **Total** | | **~$42.50/month** |

### Production / High Traffic (1 Web ACL + Bot Control, 500M requests)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Web ACL | 1 | $5.00 |
| Rules (6 rules) | 6 | $6.00 |
| Bot Control rule group | 1 | $10.00 |
| Requests (500M/month) | 500M | $300.00 |
| WAF logs to S3 (50 GB) | 50 GB | $1.15 |
| **Total** | | **~$322/month** |

---

## Cost vs. Alternatives

| Solution | Monthly Cost | Protection Level |
|----------|-------------|-----------------|
| **WAF v2 minimal** ✅ | ~$11 | OWASP + rate limiting |
| WAF v2 + Bot Control | ~$21 | + bot protection |
| Third-party WAF (Cloudflare Pro) | $20 flat | Similar OWASP coverage |
| Shield Advanced | $3,000+ | Enterprise DDoS |

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Dev/test (1 ACL, minimal traffic) | ~$10.80 | ~$130 |
| Production (moderate traffic, 50M req) | ~$42.50 | ~$510 |
| High traffic (500M req) | ~$322 | ~$3,864 |

**For this learning project:** ~$10-15/month

---

## Cleanup

```bash
# 1. Disassociate Web ACL from ALB
aws wafv2 disassociate-web-acl \
  --resource-arn "$ALB_ARN"

# 2. Get lock token
WEB_ACL_ID=$(aws wafv2 list-web-acls --scope REGIONAL \
  --query 'WebACLs[?Name==`myapp-web-acl`].Id' --output text)
LOCK_TOKEN=$(aws wafv2 get-web-acl \
  --name myapp-web-acl --scope REGIONAL --id "$WEB_ACL_ID" \
  --query LockToken --output text)

# 3. Delete Web ACL
aws wafv2 delete-web-acl \
  --name myapp-web-acl \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --lock-token "$LOCK_TOKEN"

# 4. Delete IP set
IP_SET_ID=$(aws wafv2 list-ip-sets --scope REGIONAL \
  --query 'IPSets[?Name==`blocked-ips`].Id' --output text)
IP_LOCK=$(aws wafv2 get-ip-set --name blocked-ips --scope REGIONAL \
  --id "$IP_SET_ID" --query LockToken --output text)
aws wafv2 delete-ip-set \
  --name blocked-ips --scope REGIONAL \
  --id "$IP_SET_ID" --lock-token "$IP_LOCK"

# 5. Delete log group
aws logs delete-log-group --log-group-name "aws-waf-logs-myapp"

# 6. Delete CloudWatch alarms
aws cloudwatch delete-alarms \
  --alarm-names "WAF-BlockedRequests-High" "WAF-RateLimit-Triggered"

echo "Billing stops within 1 hour of deletion"
```
