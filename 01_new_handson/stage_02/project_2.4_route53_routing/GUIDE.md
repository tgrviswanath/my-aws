# Project 2.4 — Route 53 DNS and Intelligent Traffic Routing

---

## 1. Overview

**Problem Statement**
A static DNS `A record` pointing to one IP address provides no resilience, no A/B testing capability, and no performance optimization. When the server goes down, DNS still sends traffic there. When you want to test a new deployment, you have no way to gradually shift traffic.

**What You'll Learn**
- Creating and managing a Route 53 hosted zone
- Adding A, CNAME, and Alias records
- Weighted routing policy for A/B testing (50/50 traffic split)
- Latency-based routing for multi-region performance
- Failover routing with automated health checks
- Geolocation routing for compliance or localization

**Objectives**
1. Create a Route 53 hosted zone (public or private)
2. Configure A records with weighted routing policy (50/50 split)
3. Set up health checks that ping targets every 30 seconds
4. Implement failover policy with primary/secondary designation
5. Compare all routing policy types and choose the right one

---

## 2. Architecture

```
Client (browser / curl / dig)
    │
    ▼ DNS query for myapp.example.com
┌─────────────────────────────────────────────┐
│          Route 53 Hosted Zone               │
│          myapp.example.com                  │
│                                             │
│  Routing Policy: Weighted (A/B test)        │
│  ┌─────────────────────────────────────┐    │
│  │ Record A: → EC2 v1 IP  weight=50   │    │
│  │ Record B: → EC2 v2 IP  weight=50   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  Health Checks (every 30s)                  │
│  ├── Check 1: HTTP GET EC2 v1 /health       │
│  └── Check 2: HTTP GET EC2 v2 /health       │
└────────────────────┬────────────────────────┘
                     │ Returns IP based on policy
                     ▼
         ┌──────────────────────┐
         │   EC2 v1 or EC2 v2   │
         │   (50% each)         │
         └──────────────────────┘
```

**Failover Architecture**
```
Route 53 Failover Policy
├── Primary record → EC2 in us-east-1 ← Health check monitors this
└── Secondary record → EC2 in us-west-2 (activates if primary unhealthy)
```

---

## 3. Prerequisites

**AWS Account & Permissions**
- IAM permissions: `route53:*`, `route53health:*`, `ec2:DescribeInstances`
- AWS CLI configured with `us-east-1` as default region
- For a real domain: you must own the domain (or have Route 53 as authoritative NS)
- For lab without a domain: use Route 53 private hosted zone with an EC2 VPC

**Infrastructure Requirements**
- At least 2 EC2 instances (simulating v1 and v2 deployments) with public IPs
- A domain name, OR use a `.aws` test domain if working with private hosted zone
- If testing cross-region failover: one EC2 in us-east-1, one in us-west-2

**Quick Check**
```bash
# Verify EC2 instances are running with public IPs
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].{ID:InstanceId,IP:PublicIpAddress,Region:Placement.AvailabilityZone}" \
  --output table

# Verify Route 53 permissions
aws route53 list-hosted-zones --output text
```

---

## 4. Folder Structure

```
project_2.4_route53_routing/
├── GUIDE.md                          # This file
├── steps_awsconsoleui.md             # Console walkthrough with screenshots
├── cost_estimate.md                  # Route 53 pricing breakdown
├── scripts/
│   ├── create_hosted_zone.sh         # Create public hosted zone
│   ├── create_weighted_records.sh    # Weighted routing A records
│   ├── create_health_checks.sh       # HTTP health checks for each target
│   ├── create_failover_records.sh    # Primary/secondary failover records
│   └── cleanup.sh                    # Delete all Route 53 resources
└── configs/
    ├── weighted_record_set.json      # Change batch for weighted records
    ├── failover_record_set.json      # Change batch for failover records
    └── health_check_config.json      # Health check configuration
```

---

## 5. Implementation

### 5A. Console Walkthrough

#### Prerequisites Check
- [ ] You are in Route 53 console (global service — no region selector)
- [ ] You have at least 2 running EC2 instances with known public IP addresses
- [ ] If using a real domain, you can update its NS records at your registrar
- [ ] IAM permissions include `route53:CreateHostedZone`, `route53:ChangeResourceRecordSets`

#### Decision Point 1: Routing Policy Selection

| Policy | Best For | Traffic Behavior |
|---|---|---|
| Simple | Single resource, no routing logic | All traffic to one record |
| ✅ Weighted | A/B testing, gradual deployments | Traffic split by weight ratio |
| ✅ Latency | Multi-region performance | Routes to lowest-latency region |
| ✅ Failover | Disaster recovery, HA | Active/passive with health check |
| Geolocation | Compliance, localization | Routes based on user's country/continent |
| Geoproximity | Fine-grained geo control | Routes with adjustable bias |
| Multivalue | Basic load distribution | Returns up to 8 healthy records |
| IP-based | Traffic from specific CIDRs | Routes based on source IP range |

**Create Hosted Zone via Console**
1. Route 53 → Hosted zones → Create hosted zone
2. Domain name: `myapp.example.com` (or your owned domain)
3. Type: Public hosted zone (internet-accessible) or Private (internal VPC only)
4. Click Create hosted zone
5. Note the 4 NS records — update your domain registrar to point to these

**Create Weighted A Records (A/B Test)**
1. Click "Create record"
2. Record name: `app` (creates `app.myapp.example.com`)
3. Type: A
4. Value: `<EC2 v1 public IP>`
5. TTL: 60 (low TTL for testing so changes propagate quickly)
6. Routing policy: Weighted
7. Weight: 50
8. Record ID: `v1-production`
9. Health check: attach health check (create one if needed)
10. Repeat with v2 IP, weight 50, Record ID `v2-canary`

**Expected Outcome**
- 2 A records exist for the same name with different weights
- `dig app.myapp.example.com` returns v1 IP ~50% of the time and v2 IP ~50%
- Change weight to 90/10 for canary release (90% to v1, 10% to v2)

**Troubleshooting**
- DNS not resolving: Check NS records at registrar match Route 53 NS records
- Failover not switching: Health check must be in "Healthy" → "Unhealthy" state first (~3 failed checks in 30s each = ~90s)
- TTL too long: Reduce TTL to 60 seconds when testing routing changes
- `dig` returning only one IP: That's correct — Route 53 returns one record per query; query multiple times to see the split

---

### 5B. CLI Implementation

```bash
# --- Variables ---
DOMAIN="myapp.example.com"
EC2_V1_IP="1.2.3.4"           # Replace with actual EC2 v1 public IP
EC2_V2_IP="5.6.7.8"           # Replace with actual EC2 v2 public IP
REGION="us-east-1"

# --- Create Hosted Zone ---
HOSTED_ZONE=$(aws route53 create-hosted-zone \
  --name ${DOMAIN} \
  --caller-reference "lab-$(date +%s)" \
  --hosted-zone-config Comment="Lab 2.4 Route 53 routing",PrivateZone=false \
  --query "HostedZone.Id" \
  --output text)

ZONE_ID=$(echo ${HOSTED_ZONE} | cut -d'/' -f3)
echo "Hosted Zone ID: ${ZONE_ID}"

# Get NS records to configure at registrar
aws route53 get-hosted-zone --id ${ZONE_ID} \
  --query "DelegationSet.NameServers" --output text

# --- Create Health Checks ---
HC_V1=$(aws route53 create-health-check \
  --caller-reference "hc-v1-$(date +%s)" \
  --health-check-config "{
    \"IPAddress\": \"${EC2_V1_IP}\",
    \"Port\": 80,
    \"Type\": \"HTTP\",
    \"ResourcePath\": \"/health\",
    \"FullyQualifiedDomainName\": \"${EC2_V1_IP}\",
    \"RequestInterval\": 30,
    \"FailureThreshold\": 3,
    \"MeasureLatency\": true,
    \"EnableSNI\": false
  }" \
  --query "HealthCheck.Id" --output text)
echo "Health Check v1 ID: ${HC_V1}"

HC_V2=$(aws route53 create-health-check \
  --caller-reference "hc-v2-$(date +%s)" \
  --health-check-config "{
    \"IPAddress\": \"${EC2_V2_IP}\",
    \"Port\": 80,
    \"Type\": \"HTTP\",
    \"ResourcePath\": \"/health\",
    \"FullyQualifiedDomainName\": \"${EC2_V2_IP}\",
    \"RequestInterval\": 30,
    \"FailureThreshold\": 3,
    \"MeasureLatency\": true,
    \"EnableSNI\": false
  }" \
  --query "HealthCheck.Id" --output text)
echo "Health Check v2 ID: ${HC_V2}"

# --- Create Weighted A Records ---
aws route53 change-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --change-batch "{
    \"Comment\": \"Create weighted A records for A/B testing\",
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"app.${DOMAIN}\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"v1-production\",
          \"Weight\": 50,
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"${EC2_V1_IP}\"}],
          \"HealthCheckId\": \"${HC_V1}\"
        }
      },
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"app.${DOMAIN}\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"v2-canary\",
          \"Weight\": 50,
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"${EC2_V2_IP}\"}],
          \"HealthCheckId\": \"${HC_V2}\"
        }
      }
    ]
  }"

echo "Weighted records created"

# --- Verify Records ---
aws route53 list-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --query "ResourceRecordSets[?Name=='app.${DOMAIN}.']" \
  --output table
```

---

## 6. Code Deep Dive

### Weighted Routing Change Batch
```json
{
  "Comment": "Weighted routing for A/B testing",
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "app.myapp.example.com",
      "Type": "A",
      "SetIdentifier": "v1-production",
      "Weight": 90,
      "TTL": 60,
      "ResourceRecords": [{"Value": "1.2.3.4"}],
      "HealthCheckId": "abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
  }]
}
```

### Failover Record Batch
```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.myapp.example.com",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "TTL": 30,
        "ResourceRecords": [{"Value": "1.2.3.4"}],
        "HealthCheckId": "primary-health-check-id"
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.myapp.example.com",
        "Type": "A",
        "SetIdentifier": "secondary",
        "Failover": "SECONDARY",
        "TTL": 30,
        "ResourceRecords": [{"Value": "5.6.7.8"}]
      }
    }
  ]
}
```

---

## 7. Verification

```bash
# Test DNS resolution (run multiple times to see weighted split)
for i in {1..10}; do
  dig +short app.myapp.example.com @8.8.8.8
done | sort | uniq -c
# Expected: ~5 lines showing v1 IP, ~5 lines showing v2 IP

# Check health check status
aws route53 get-health-check-status --health-check-id ${HC_V1} \
  --query "HealthCheckObservations[].{Region:Region,Status:StatusReport.Status}" \
  --output table

# List all records in zone
aws route53 list-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --output table

# Test with nslookup
nslookup app.myapp.example.com
```

---

## 8. Observations

| Feature | Detail |
|---|---|
| TTL behavior | Low TTL (60s) means changes propagate faster but more DNS queries |
| Health check frequency | 30s standard interval, 10s fast (additional cost) |
| Failover switch time | ~90s standard (3 failures × 30s) or ~30s fast health checks |
| Weight 0 | Setting weight=0 takes a record out of rotation (zero traffic) |
| Weight total | Weights don't need to add to 100 — they're ratios (50/50 = 10/10) |

---

## 9. Screenshots

1. Hosted zone created showing 4 NS records
2. Two weighted A records with same name, different IPs and weights
3. Health check showing "Healthy" status in all regions
4. Console graph showing health check latency over time
5. Terminal showing `dig` command returning different IPs across queries

---

## 10. Cleanup

```bash
# Step 1: Delete all non-NS/SOA resource records first
aws route53 change-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --change-batch "{
    \"Changes\": [
      {\"Action\": \"DELETE\", \"ResourceRecordSet\": {
        \"Name\": \"app.${DOMAIN}\", \"Type\": \"A\",
        \"SetIdentifier\": \"v1-production\", \"Weight\": 50,
        \"TTL\": 60, \"ResourceRecords\": [{\"Value\": \"${EC2_V1_IP}\"}],
        \"HealthCheckId\": \"${HC_V1}\"
      }},
      {\"Action\": \"DELETE\", \"ResourceRecordSet\": {
        \"Name\": \"app.${DOMAIN}\", \"Type\": \"A\",
        \"SetIdentifier\": \"v2-canary\", \"Weight\": 50,
        \"TTL\": 60, \"ResourceRecords\": [{\"Value\": \"${EC2_V2_IP}\"}],
        \"HealthCheckId\": \"${HC_V2}\"
      }}
    ]
  }"

# Step 2: Delete health checks
aws route53 delete-health-check --health-check-id ${HC_V1}
aws route53 delete-health-check --health-check-id ${HC_V2}

# Step 3: Delete hosted zone (only works when empty of custom records)
aws route53 delete-hosted-zone --id ${ZONE_ID}

echo "Route 53 cleanup complete"
```
