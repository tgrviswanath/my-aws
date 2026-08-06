# Console UI Guide — Project 2.4: Route 53 DNS and Intelligent Traffic Routing

> Step-by-step console walkthrough with decision points, screenshot markers, and troubleshooting at each stage.

---

## Prerequisites Check

Complete all checks before starting the console steps:

| Check | Where to Verify | Required |
|---|---|---|
| Route 53 permissions | IAM → Your User → Permissions → route53 | `route53:*` and `route53health:*` |
| EC2 instances running | EC2 → Instances (both target IPs needed) | At least 2 instances with public IPs |
| Domain name available | Your domain registrar or Route 53 Domains | Owned domain OR use private hosted zone |
| Region awareness | Route 53 is a global service | No region selector — all changes are global |
| NS delegation capability | Domain registrar control panel | Ability to change NS records at registrar |

> 💡 **No domain?** You can still complete this lab using a Route 53 private hosted zone associated with your VPC — DNS queries only work from within the VPC, which is sufficient for testing.

---

## Step 1 — Create Hosted Zone

### Decision Point 1: Public vs Private Hosted Zone

| Zone Type | Resolves From | Use Case | DNS Query Source |
|---|---|---|---|
| ✅ Public hosted zone | Anywhere on internet | Production websites, APIs | Public internet clients |
| Private hosted zone | Within your VPC only | Internal services, databases | EC2 instances in your VPC |
| Both (split-horizon) | Public from internet, private from VPC | Return different IPs internally vs externally | Both |

> **For this lab:** Choose Public if you own a domain. Choose Private if you want to test without a domain — queries will work from EC2 instances inside the VPC.

**Navigate:** Route 53 → Hosted zones → Create hosted zone

1. **Domain name:** `myapp.yourdomain.com` (replace with your actual domain)
   - For private zone testing: use `internal.lab` (no real domain needed)
2. **Type:** Public hosted zone (or Private for VPC-only testing)
3. If Private: select your lab VPC in the VPC section
4. **Description:** `Lab 2.4 Route 53 routing`
5. Click **Create hosted zone**

**Record the NS Servers (Public Zone Only)**
After creation, 4 NS records are automatically created. Copy them:
```
ns-xxx.awsdns-xx.com
ns-xxx.awsdns-xx.net
ns-xxx.awsdns-xx.org
ns-xxx.awsdns-xx.co.uk
```
Go to your domain registrar → DNS settings → Replace NS records with these 4 values.
**DNS propagation takes 24–48 hours for NS changes globally** (A record changes propagate per TTL).

### 📸 Screenshot
> Take a screenshot of the newly created hosted zone showing:
> - Domain name
> - The 4 NS records (nameservers)
> - The SOA record
> Label it: `01_hosted_zone_created_ns_records.png`

### Expected Outcome
- Hosted zone created with a Zone ID (format: `/hostedzone/ZXXXXXXXXXX`)
- 4 NS records and 1 SOA record automatically present
- If public zone: NS records match what you update at registrar
- If private zone: associated with your VPC, only queries from VPC resolve this zone

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Domain not available" error | Using a domain you don't own | Use a subdomain of a domain you own, or use private zone |
| NS records not resolving after 1 hour | Propagation still in progress | Wait up to 48 hours; test with `dig NS yourdomain.com @8.8.8.8` |
| Private zone not resolving from EC2 | VPC DNS hostnames not enabled | VPC → Edit DNS settings → Enable DNS hostnames + DNS resolution |

---

## Step 2 — Create A Records with Weighted Routing

### Decision Point 2: Routing Policy Selection Guide

| Policy | Console Option | When to Use | Example |
|---|---|---|---|
| Simple | Simple routing | One resource, no HA needed | Static website |
| ✅ Weighted | Weighted routing | A/B testing, gradual rollout | 90/10 canary deploy |
| Latency | Latency-based routing | Multi-region, minimize latency | US users → us-east-1, EU users → eu-west-1 |
| Failover | Failover routing | Active/passive DR | Primary EC2 + backup EC2 in another region |
| Geolocation | Geolocation routing | Data residency, localized content | EU users get GDPR-compliant endpoint |
| Multivalue | Multivalue answer | Basic round-robin + health checks | Returns up to 8 IPs |

> **For this step:** Use Weighted routing to demonstrate 50/50 A/B testing split.

**Get EC2 IP Addresses First**
Open EC2 → Instances and note the public IPs for both instances.

**Navigate:** Route 53 → Hosted zones → Click your zone → Create record

**Create Record for v1 (first of two weighted records)**
1. **Record name:** `app` *(creates `app.yourdomain.com`)*
2. **Record type:** A — Routes traffic to an IPv4 address
3. **Value:** `1.2.3.4` *(replace with EC2 v1 public IP)*
4. **TTL:** `60` *(low for testing — changes propagate in 60 seconds)*
5. **Routing policy:** Weighted
6. **Weight:** `50`
7. **Health check:** Attach if already created (or skip for now)
8. **Record ID:** `v1-production` *(must be unique across records with same name)*
9. Click **Add another record** (do NOT save yet)

**Create Record for v2 (second weighted record)**
10. **Record name:** `app` *(same name as v1)*
11. **Record type:** A
12. **Value:** `5.6.7.8` *(replace with EC2 v2 public IP)*
13. **TTL:** `60`
14. **Routing policy:** Weighted
15. **Weight:** `50`
16. **Record ID:** `v2-canary`
17. Click **Create records**

### 📸 Screenshot
> Take a screenshot of the record creation form showing:
> - Two A records being created for `app.yourdomain.com`
> - Routing policy: Weighted
> - Weights: 50 and 50
> - Different IPs for each record
> Label it: `02_weighted_record_set_form.png`

### Expected Outcome
- Two A records visible in the hosted zone list for `app.yourdomain.com`
- Both show "Weighted" routing policy with 50/50 split
- Running `dig app.yourdomain.com` multiple times returns v1 IP ~50% and v2 IP ~50%
- TTL of 60 means each answer is cached by resolvers for 60 seconds

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Record ID must be unique" error | Both records have same Record ID | Give each a unique ID (v1-production, v2-canary) |
| `dig` always returns same IP | DNS caching at resolver level | Use `dig +nocache` or query a different DNS: `dig @8.8.8.8` |
| Both records show 0% routing | Missing health check or health check failing | Create and attach health check, ensure EC2 is running and accessible |
| Can't see Weighted option | Route selection varies by wizard mode | Switch to "Other routing policies" tab in the record creation form |

---

## Step 3 — Create Health Checks

### Decision Point 3: Health Check Protocol and Sensitivity

| Protocol | Port | Checks | Best For |
|---|---|---|---|
| ✅ HTTP | 80 | HTTP 200-399 response from path | Web applications |
| HTTPS | 443 | Same + valid SSL certificate | Production HTTPS apps |
| ✅ TCP | Any | TCP connection success | Non-HTTP services, databases |
| HTTP_STR_MATCH | 80 | HTTP 200 + body contains string | Deep health validation |
| HTTPS_STR_MATCH | 443 | HTTPS 200 + body string | Production with content check |

| Interval | Frequency | Response Time Budget | Cost |
|---|---|---|---|
| Standard (30s) | Every 30s | 10 seconds | Included in base cost |
| Fast (10s) | Every 10s | 2 seconds | Additional $1/month per check |

**Navigate:** Route 53 → Health checks → Create health check

**Create health check for v1 EC2**
1. **Name:** `hc-v1-ec2`
2. **What to monitor:** Endpoint
3. **Protocol:** HTTP
4. **Specify endpoint by:** IP address
5. **IP address:** `1.2.3.4` *(EC2 v1 public IP)*
6. **Port:** 80
7. **Path:** `/health`
8. **Advanced configuration:**
   - Request interval: Standard (30 seconds)
   - Failure threshold: 3 (fails after 3 consecutive failed checks = ~90 seconds)
9. Click **Create health check**

**Repeat for v2 EC2**
- Name: `hc-v2-ec2`
- IP: v2 EC2 public IP
- All other settings same

**Attach Health Checks to Weighted Records**
1. Route 53 → Hosted zones → Your zone → Click `app.yourdomain.com` (v1 record)
2. Edit → Health check: select `hc-v1-ec2` → Save
3. Repeat for v2 record with `hc-v2-ec2`

### 📸 Screenshot
> Take a screenshot of the health check list showing:
> - Both health checks in "Healthy" status (green)
> - Protocol: HTTP, Port: 80
> - The health check graph showing request latency
> Label it: `03_health_checks_healthy_status.png`

### Expected Outcome
- Both health checks show Status: "Healthy" (green) within 2 minutes of creation
- Health check latency graph shows response times < 500ms
- If you stop one EC2: its health check turns "Unhealthy" within ~90s
- Route 53 automatically removes unhealthy records from rotation when health check attached

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Health check shows "Unhealthy" immediately | EC2 SG blocks health checker IPs | Add inbound rule: TCP 80 from `0.0.0.0/0` OR from Route 53 health checker IP ranges |
| Health check shows "Insufficient data" | Still warming up | Wait 2–3 minutes |
| Path `/health` returning 404 | No `/health` endpoint on web server | Change path to `/` or add a `/health` route to your app |
| Health check passes but DNS still fails | Health check not attached to record | Edit each weighted record and attach its health check |

**Route 53 Health Checker IP Ranges (for SG rules)**
```bash
# Get current Route 53 health checker IP ranges
curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
  python3 -c "import json,sys; data=json.load(sys.stdin); \
  [print(p['ip_prefix']) for p in data['prefixes'] if p['service']=='ROUTE53_HEALTHCHECKS']"
```

---

## Step 4 — Test Routing and Verify DNS Behavior

### 📸 Screenshot
> Take a screenshot of your terminal showing the `dig` output with different IPs across multiple queries.
> Label it: `04_dig_weighted_routing_verification.png`

**Open AWS CloudShell** (top navigation bar icon) and run these tests:

```bash
DOMAIN="app.yourdomain.com"

# Test 1: Confirm DNS resolves
echo "=== Basic DNS resolution ==="
dig ${DOMAIN} +short

# Test 2: Query multiple times to see weighted distribution
echo "=== Testing 50/50 weighted split (10 queries) ==="
for i in {1..10}; do
  dig ${DOMAIN} +short @8.8.8.8
  sleep 1
done | sort | uniq -c | sort -rn
# Expected: approximately 5 counts each for v1 IP and v2 IP

# Test 3: Query directly to avoid caching
echo "=== Direct Route 53 query (bypasses resolver cache) ==="
dig ${DOMAIN} +short @ns-xxx.awsdns-xx.com
# Replace with your actual Route 53 nameserver

# Test 4: nslookup
echo "=== nslookup test ==="
nslookup ${DOMAIN} 8.8.8.8

# Test 5: Simulate v1 failure — stop the EC2, watch routing shift
# (Stop EC2 v1 from console, then re-run above queries after ~90 seconds)
echo "=== After failing v1 — all queries should return v2 IP only ==="
# dig ${DOMAIN} +short
```

**Test Failover Behavior (Optional)**
1. EC2 → Stop instance (v1 instance)
2. Wait 90 seconds for health check to detect failure (3 × 30s intervals)
3. Run `dig app.yourdomain.com +short` — should only return v2 IP now
4. Restart v1 EC2 → after another 90s, both IPs return again

### Expected Outcome
- 50/50 split visible across multiple `dig` queries
- After stopping one EC2: 100% of queries return the surviving instance's IP
- After restarting stopped EC2: 50/50 split resumes within ~2 minutes
- `nslookup` confirms DNS is resolving to correct IPs

---

## Routing Policy Quick Reference Card

| Scenario | Use This Policy |
|---|---|
| Single resource, no routing needed | Simple |
| Gradually roll out new version | Weighted |
| Route users to lowest-latency region | Latency |
| Active/passive DR failover | Failover |
| Route EU users to EU servers | Geolocation |
| Return multiple healthy IPs | Multivalue |
| Fine-grained geographic control | Geoproximity (Traffic Flow) |

---

## Cleanup Summary

From console:
1. Route 53 → Health checks → Select both → Delete
2. Route 53 → Hosted zones → Your zone → Select all custom records → Delete records
3. Route 53 → Hosted zones → Delete the hosted zone (only possible when empty)

Or via CLI — see GUIDE.md Section 10.
