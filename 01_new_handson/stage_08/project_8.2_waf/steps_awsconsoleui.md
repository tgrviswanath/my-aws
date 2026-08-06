# Project 8.2 — AWS WAF v2: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] AWS Console access with `wafv2:*` permissions
- [ ] ALB deployed and accessible (note its ARN)
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] CloudWatch Logs: `logs:CreateLogGroup` permission

---

## Step 1 — Navigate to AWS WAF & Shield

1. Sign in to **AWS Management Console**
2. Search for **WAF** in the top search bar
3. Click **AWS WAF & Shield**
4. You see the WAF Dashboard with Web ACLs, IP sets, Rule groups
5. Ensure region is set to **US East (N. Virginia)** (top right)

📸 Screenshot: WAF & Shield navigation page with Web ACLs listed

**Decision Point: Regional vs Global (CloudFront)?**
- **Regional** = protects ALB, API Gateway in a specific region ✅ for this project
- **Global** = protects CloudFront distributions (must create in us-east-1)

---

## Step 2 — Create Web ACL (Start Wizard)

1. In left nav: click **Web ACLs**
2. Click **Create web ACL** (orange button)
3. **Step 1 — Describe web ACL and associate it to AWS resources:**
   - **Resource type**: `Regional resources (Application Load Balancer and API Gateway)`
   - **Region**: `US East (N. Virginia)`
   - **Name**: `myapp-web-acl`
   - **Description**: `WAF v2 for myapp — OWASP + rate limiting`
   - **CloudWatch metric name**: `myapp-web-acl` (auto-filled)
4. **Associated AWS resources** → Click **Add AWS resources**
   - Select your ALB from the list
   - Click **Add**
5. Click **Next**

📸 Screenshot: Web ACL creation step 1 with name and ALB association

---

## Step 3 — Add Managed Rule Groups (OWASP)

1. **Step 2 — Add rules and rule groups:**
2. Click **Add rules** → **Add managed rule groups**
3. Expand **AWS managed rule groups**
4. Enable:
   - ✅ `Core rule set` (AWSManagedRulesCommonRuleSet) — OWASP Top 10
     - Click **Add to web ACL** → Override: None (Block mode)
   - ✅ `Known bad inputs` (AWSManagedRulesKnownBadInputsRuleSet)
     - Click **Add to web ACL**
5. Optionally add:
   - `SQL database` — if you have SQL-exposed endpoints
   - `Linux operating system` — for Linux-based backends
6. Click **Add rules** to confirm

📸 Screenshot: Managed rule groups list with Core rule set checked

---

## Step 4 — Add Rate-Based Rule

1. Click **Add rules** → **Add my own rules and rule groups**
2. **Rule type**: `Rate-based rule`
3. Configure:
   - **Name**: `RateLimitPerIP`
   - **Rate limit**: `2000` (requests per 5 minutes)
   - **Aggregation**: `Source IP address`
   - **Scope of inspection and rate limiting**: `Consider all requests`
4. **Action**: `Block`
5. **CloudWatch metric name**: `RateLimitPerIP`
6. Click **Add rule**

📸 Screenshot: Rate-based rule configuration with 2000 limit and Block action

---

## Step 5 — Add Custom IP Block Rule

1. First create an IP set (separate step):
   - Left nav → **IP sets** → **Create IP set**
   - **Name**: `blocked-ips`
   - **Region**: US East (N. Virginia)
   - **IP version**: IPv4
   - **IP addresses**: Enter CIDRs to block (one per line)
   - Click **Create IP set**
2. Back in Web ACL creation → **Add rules** → **Add my own rules**
   - **Rule type**: `IP set`
   - **Name**: `BlockCustomIPs`
   - **IP set**: Select `blocked-ips`
   - **Action**: Block
   - Click **Add rule**

📸 Screenshot: IP set rule configuration with blocked-ips selected

---

## Step 6 — Set Rule Priority

1. **Step 2 continued** — Rule priority order (drag to reorder):
   - Priority 0: `BlockCustomIPs` (check your own block list first)
   - Priority 1: `AWSManagedRulesCommonRuleSet`
   - Priority 2: `AWSManagedRulesKnownBadInputsRuleSet`
   - Priority 3: `RateLimitPerIP`
2. **Default web ACL action**: `Allow` (anything not blocked passes through)
3. Click **Next**

📸 Screenshot: Rule priority list with drag handles for reordering

**Troubleshooting — Rules not firing:**
- Verify Default action is `Allow` — if set to `Block`, all traffic blocked
- Rules evaluated top to bottom; a matching rule stops evaluation

---

## Step 7 — Configure Metrics

1. **Step 3 — Configure metrics:**
2. **CloudWatch Metrics**: ✅ Enable
3. **Sampled requests**: ✅ Enable (lets you view example blocked/allowed requests)
4. **Web ACL metric name**: `myapp-web-acl`
5. Click **Next**

📸 Screenshot: Metrics configuration page with sampling enabled

---

## Step 8 — Review and Create

1. **Step 4 — Review and create web ACL:**
2. Review:
   - Associated resources (ALB shown)
   - Rules list with priorities
   - Default action: Allow
3. Click **Create web ACL**
4. Wait ~30 seconds — Web ACL appears in list as `Active`

📸 Screenshot: Web ACL creation confirmation with Active status badge

---

## Step 9 — Enable Logging

1. Click on your `myapp-web-acl` name
2. Go to **Logging and metrics** tab
3. Click **Enable logging**
4. **Logging destination**: CloudWatch Logs
5. **Log group**: Create new or select existing
   - Name must start with `aws-waf-logs-`
   - Enter: `aws-waf-logs-myapp`
6. **Redacted fields** (optional): Redact `uri-path` or `query-string` if sensitive
7. Click **Enable logging**

📸 Screenshot: WAF logging configuration with CloudWatch Logs destination

---

## Step 10 — View Sampled Requests and Metrics

1. Go to Web ACL → **Sampled requests** tab
2. Select a rule (e.g., `AWSManagedRulesCommonRuleSet`)
3. See actual blocked requests with:
   - Source IP, timestamp, URI, action taken
   - Matched rule within the rule group
4. **Metrics** tab → View AllowedRequests, BlockedRequests, CountedRequests graphs

📸 Screenshot: Sampled requests table showing blocked SQL injection attempts

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| ALB not showing in dropdown | Wrong region | Change region selector to match ALB region |
| Web ACL shows but not blocking | ACL not associated | Check Associated resources tab |
| False positives (legitimate requests blocked) | Rule too strict | Switch rule to COUNT mode → review sampled requests → tune |
| No metrics in CloudWatch | Metrics disabled | Re-enable in Logging and metrics tab |
| Can't delete Web ACL | Still associated to ALB | Disassociate first: Associated resources → remove |

---

## Console Navigation Quick Reference

```
AWS WAF & Shield
├── Web ACLs          → Create, view, edit ACLs
├── IP sets           → Manage block/allow IP lists
├── Regex pattern sets → Pattern-based filtering
├── Rule groups       → Reusable custom rule sets
└── AWS managed rules → Browse managed rule catalog
    └── [Web ACL Name]
        ├── Rules tab      → Rule list + priorities
        ├── Associated resources → ALB/API GW attachments
        ├── Logging and metrics  → CloudWatch config
        └── Sampled requests     → Debug blocked traffic
```
