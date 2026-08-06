# Project 8.2 — AWS WAF v2
## Web Application Firewall with OWASP Rules, Rate Limiting, and ALB Integration

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] ALB exists and serving traffic (or create one first)
- [ ] IAM permissions: `wafv2:*`, `elasticloadbalancing:*`, `cloudwatch:*`, `logs:*`
- [ ] Region: `us-east-1` (WAF for ALB must be in same region as ALB)
- [ ] ALB ARN available: `aws elbv2 describe-load-balancers --query 'LoadBalancers[0].LoadBalancerArn'`
- [ ] jq installed: `jq --version`

```bash
# Verify prerequisites
aws sts get-caller-identity
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names my-application-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)
echo "ALB ARN: $ALB_ARN"
```

---

## Decision Point 1

**WAF Classic vs WAF v2 vs AWS Shield — which to use?**

| Option | Recommendation | Use Case | Cost |
|--------|---------------|----------|------|
| **WAF v2** ✅ | **Use this** | Modern apps, API Gateway, ALB, CloudFront | $5/ACL + $1/rule |
| WAF Classic | Legacy only | Pre-2019 configs being migrated | Similar pricing |
| Shield Standard | Always on | Basic DDoS protection | Free |
| Shield Advanced | Enterprise | Volumetric DDoS, 24/7 DRT support | $3,000/month |

**WAF v2 advantages over Classic:**
- Managed rule groups (OWASP, Bot Control, known bad IPs)
- Labels for complex logic across rules
- JSON rule body inspection
- Rate limiting per IP with 5-minute windows
- Supports ALB, API Gateway, CloudFront, AppSync, Cognito

**Verdict:** WAF v2 ✅ — modern, managed, full OWASP coverage.

---

## 1. Architecture Overview

```
Internet → CloudFront (optional)
                │
                ▼
    Application Load Balancer
                │
         AWS WAF v2 Web ACL
         ├── Rule 1: AWSManagedRulesCommonRuleSet (OWASP)
         ├── Rule 2: AWSManagedRulesKnownBadInputsRuleSet
         ├── Rule 3: Rate limit — 2000 req/5min per IP
         ├── Rule 4: Custom IP block list
         └── Default action: ALLOW
                │
         EC2 / ECS / Lambda targets
```

**Key concepts:**
- **Web ACL**: Container for WAF rules, attached to one or more resources
- **Rule Group**: Reusable set of rules (managed = AWS-maintained, custom = yours)
- **Rate-based rule**: Counts requests per IP per 5-minute window
- **Scope**: REGIONAL (ALB/API GW) or CLOUDFRONT (must be us-east-1)

---

## 2. Create Web ACL

```bash
# Create WAF v2 Web ACL with managed rules
cat > /tmp/waf-rules.json << 'EOF'
[
  {
    "Name": "AWSManagedRulesCommonRuleSet",
    "Priority": 1,
    "OverrideAction": {"None": {}},
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesCommonRuleSet"
      }
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "AWSCommonRules"
    }
  },
  {
    "Name": "AWSManagedRulesKnownBadInputs",
    "Priority": 2,
    "OverrideAction": {"None": {}},
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesKnownBadInputsRuleSet"
      }
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "KnownBadInputs"
    }
  },
  {
    "Name": "RateLimitPerIP",
    "Priority": 3,
    "Action": {"Block": {}},
    "Statement": {
      "RateBasedStatement": {
        "Limit": 2000,
        "AggregateKeyType": "IP"
      }
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "RateLimit"
    }
  }
]
EOF

WEB_ACL_ARN=$(aws wafv2 create-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --default-action '{"Allow": {}}' \
  --rules file:///tmp/waf-rules.json \
  --visibility-config '{
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "myapp-web-acl"
  }' \
  --description "WAF v2 for myapp ALB — OWASP + rate limiting" \
  --tags '[{"Key":"Project","Value":"myapp"},{"Key":"Environment","Value":"production"}]' \
  --query 'Summary.ARN' \
  --output text)

echo "Web ACL ARN: $WEB_ACL_ARN"
```

---

## 3. Add Custom IP Block Rule

```bash
# Create IP set for blocked addresses
IP_SET_ARN=$(aws wafv2 create-ip-set \
  --name "blocked-ips" \
  --scope REGIONAL \
  --ip-address-version IPV4 \
  --addresses '["192.0.2.0/24", "198.51.100.0/24"]' \
  --description "Manually blocked IP ranges" \
  --query 'Summary.ARN' \
  --output text)

echo "IP Set ARN: $IP_SET_ARN"

# Get Web ACL lock token (required for updates)
LOCK_TOKEN=$(aws wafv2 get-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --id $(aws wafv2 list-web-acls --scope REGIONAL --query 'WebACLs[?Name==`myapp-web-acl`].Id' --output text) \
  --query 'LockToken' \
  --output text)

# Update Web ACL to add IP block rule
# (In practice, use update-web-acl with all existing rules + new rule)
echo "IP Set created. Add to Web ACL via console or update-web-acl CLI."
```

---

## 4. Associate Web ACL with ALB

```bash
# Associate Web ACL with your ALB
aws wafv2 associate-web-acl \
  --web-acl-arn "$WEB_ACL_ARN" \
  --resource-arn "$ALB_ARN"

# Verify association
aws wafv2 get-web-acl-for-resource \
  --resource-arn "$ALB_ARN" \
  --query 'WebACL.{Name:Name,ARN:ARN}'
```

---

## 5A. Console: Create Web ACL

**Step-by-step via AWS Management Console:**

1. Navigate to **AWS WAF & Shield** → **Web ACLs**
2. Click **Create web ACL**
3. **Resource type**: Regional resources (ALB, API GW)
4. **Region**: US East (N. Virginia)
5. **Name**: `myapp-web-acl`
6. **Add associated AWS resources**: Select your ALB
7. Click **Next** → **Add rules**:
   - **Add managed rule groups** → AWS managed:
     - ✅ `AWSManagedRulesCommonRuleSet` (OWASP Top 10)
     - ✅ `AWSManagedRulesKnownBadInputsRuleSet`
   - **Add rules** → **Add my own rules** → **Rate-based rule**:
     - Name: `RateLimitPerIP`
     - Rate limit: `2000`
     - Aggregation: `Source IP address`
     - Action: Block
8. **Default web ACL action**: Allow
9. **Set metric name**: `myapp-web-acl`
10. Click **Create web ACL**

---

## 5B. CLI: Full Setup Commands

```bash
# List all Web ACLs
aws wafv2 list-web-acls --scope REGIONAL

# Get Web ACL details
WEB_ACL_ID=$(aws wafv2 list-web-acls \
  --scope REGIONAL \
  --query 'WebACLs[?Name==`myapp-web-acl`].Id' \
  --output text)

aws wafv2 get-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID"

# Check association
aws wafv2 list-resources-for-web-acl \
  --web-acl-arn "$WEB_ACL_ARN"

# Update IP block list
aws wafv2 update-ip-set \
  --name "blocked-ips" \
  --scope REGIONAL \
  --id $(aws wafv2 list-ip-sets --scope REGIONAL --query 'IPSets[?Name==`blocked-ips`].Id' --output text) \
  --lock-token $(aws wafv2 get-ip-set --name blocked-ips --scope REGIONAL --id $IP_SET_ID --query LockToken --output text) \
  --addresses '["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"]'
```

---

## 6. Enable WAF Logging to CloudWatch

```bash
# Create CloudWatch log group for WAF logs
aws logs create-log-group \
  --log-group-name "aws-waf-logs-myapp" \
  --retention-in-days 90

# Get log group ARN
LOG_GROUP_ARN=$(aws logs describe-log-groups \
  --log-group-name-prefix "aws-waf-logs-myapp" \
  --query 'logGroups[0].arn' \
  --output text)

# Enable WAF logging
aws wafv2 put-logging-configuration \
  --logging-configuration "{
    \"ResourceArn\": \"$WEB_ACL_ARN\",
    \"LogDestinationConfigs\": [\"$LOG_GROUP_ARN\"]
  }"

# Verify logging
aws wafv2 get-logging-configuration \
  --resource-arn "$WEB_ACL_ARN"
```

---

## 7. Create CloudWatch Alarms

```bash
# Alarm: WAF is blocking requests (potential attack)
aws cloudwatch put-metric-alarm \
  --alarm-name "WAF-BlockedRequests-High" \
  --alarm-description "WAF blocking elevated traffic — possible attack" \
  --metric-name "BlockedRequests" \
  --namespace "AWS/WAFV2" \
  --dimensions Name=WebACL,Value=myapp-web-acl Name=Region,Value=us-east-1 \
  --statistic Sum \
  --period 300 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:ACCOUNT:security-alerts"

# Alarm: Rate limit exceeded
aws cloudwatch put-metric-alarm \
  --alarm-name "WAF-RateLimit-Triggered" \
  --alarm-description "Rate limit rule blocking IPs" \
  --metric-name "RateLimit" \
  --namespace "AWS/WAFV2" \
  --dimensions Name=WebACL,Value=myapp-web-acl Name=Region,Value=us-east-1 Name=Rule,Value=RateLimitPerIP \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:ACCOUNT:security-alerts"
```

---

## 8. Test WAF Rules

```bash
# Test OWASP SQL injection block (should return 403)
curl -v "https://your-alb-dns.us-east-1.elb.amazonaws.com/?id=1'OR'1'='1"

# Test XSS block
curl -v "https://your-alb-dns.us-east-1.elb.amazonaws.com/?input=<script>alert(1)</script>"

# Test rate limit (2001 requests in 5 min should trigger block)
for i in $(seq 1 2100); do
  curl -s -o /dev/null "https://your-alb-dns.us-east-1.elb.amazonaws.com/"
done

# Check sampled requests
aws wafv2 get-sampled-requests \
  --web-acl-arn "$WEB_ACL_ARN" \
  --rule-metric-name "AWSCommonRules" \
  --scope REGIONAL \
  --time-window "StartTime=$(date -d '1 hour ago' --utc +%Y-%m-%dT%H:%M:%SZ),EndTime=$(date --utc +%Y-%m-%dT%H:%M:%SZ)" \
  --max-items 10
```

---

## 9. Add Bot Control (Optional)

```bash
# Add Bot Control managed rule group
cat > /tmp/bot-rule.json << 'EOF'
{
  "Name": "AWSManagedRulesBotControlRuleSet",
  "Priority": 0,
  "OverrideAction": {"None": {}},
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesBotControlRuleSet",
      "ManagedRuleGroupConfigs": [
        {
          "AWSManagedRulesBotControlRuleSet": {
            "InspectionLevel": "COMMON"
          }
        }
      ]
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BotControl"
  }
}
EOF
# Note: Priority 0 = evaluated first; add to update-web-acl call
```

---

## 10. Verify Complete Setup

```bash
echo "=== WAF v2 Verification ==="

# 1. Web ACL exists
aws wafv2 list-web-acls --scope REGIONAL \
  --query 'WebACLs[?Name==`myapp-web-acl`]' | jq .

# 2. Attached to ALB
aws wafv2 get-web-acl-for-resource \
  --resource-arn "$ALB_ARN" \
  --query 'WebACL.Name'

# 3. Rules configured
aws wafv2 get-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --query 'WebACL.Rules[].Name'

# 4. Metrics flowing
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name AllowedRequests \
  --dimensions Name=WebACL,Value=myapp-web-acl Name=Region,Value=us-east-1 \
  --start-time $(date -d '1 hour ago' --utc +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date --utc +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum

echo "=== Verification Complete ==="
```

---

## Troubleshooting

**WAF not blocking known attacks:**
```bash
# Check if Web ACL is associated
aws wafv2 get-web-acl-for-resource --resource-arn "$ALB_ARN"
# If empty — run associate-web-acl again
```

**Legitimate traffic being blocked:**
```bash
# View sampled blocked requests to identify cause
aws wafv2 get-sampled-requests \
  --web-acl-arn "$WEB_ACL_ARN" \
  --rule-metric-name "AWSCommonRules" \
  --scope REGIONAL \
  --time-window "StartTime=2024-01-01T00:00:00Z,EndTime=2024-01-01T01:00:00Z" \
  --max-items 5
# Switch rule to COUNT mode while debugging, then back to BLOCK
```

**Rate limit too aggressive:**
```bash
# Increase rate limit threshold in update-web-acl call
# Or add IP-based exclusion for trusted CIDR ranges
```

---

## Expected Outcome

After completing this guide:
- ✅ Web ACL `myapp-web-acl` created with OWASP managed rules
- ✅ Rate limiting at 2000 req/5min per IP (auto-blocks attackers)
- ✅ Custom IP block list maintained
- ✅ Web ACL attached to ALB — all traffic inspected
- ✅ CloudWatch metrics and alarms configured
- ✅ WAF logs stored in CloudWatch Logs for 90 days

---

## Cleanup

```bash
# Disassociate from ALB first
aws wafv2 disassociate-web-acl \
  --resource-arn "$ALB_ARN"

# Get Web ACL lock token
LOCK_TOKEN=$(aws wafv2 get-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --query 'LockToken' \
  --output text)

# Delete Web ACL
aws wafv2 delete-web-acl \
  --name "myapp-web-acl" \
  --scope REGIONAL \
  --id "$WEB_ACL_ID" \
  --lock-token "$LOCK_TOKEN"

# Delete IP set
IP_SET_ID=$(aws wafv2 list-ip-sets --scope REGIONAL \
  --query 'IPSets[?Name==`blocked-ips`].Id' --output text)
IP_SET_LOCK=$(aws wafv2 get-ip-set --name blocked-ips --scope REGIONAL \
  --id "$IP_SET_ID" --query 'LockToken' --output text)
aws wafv2 delete-ip-set \
  --name "blocked-ips" --scope REGIONAL \
  --id "$IP_SET_ID" --lock-token "$IP_SET_LOCK"

# Delete log group
aws logs delete-log-group --log-group-name "aws-waf-logs-myapp"

echo "WAF cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
