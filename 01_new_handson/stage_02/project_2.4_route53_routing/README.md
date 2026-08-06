# Project 2.4 — Route 53 DNS Routing Policies

**Stage:** 02 | **Level:** Intermediate | **Est. Time:** 2–3 hours | **Cost:** ~$2–4/month

Configure a Route 53 hosted zone with three routing policies on the same domain name. Weighted routing splits traffic 70/30 between two EC2 instances (or ALBs) to simulate a canary deployment. Latency-based routing directs users to the nearest region by measuring resolver-to-region latency between us-east-1 and us-west-2. Route 53 health checks monitor both endpoints and automatically remove any unhealthy record from DNS responses, providing DNS-level failover without manual intervention.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Route 53 Hosted Zone | Authoritative DNS for the domain | $0.50/hosted zone/month |
| Weighted Records | 70/30 traffic split between two endpoints | $0.40/1M queries |
| Latency Records | Routes users to lowest-latency region | $0.40/1M queries |
| Health Checks (×2) | HTTP health monitors on both endpoints | $0.50/health check/month |
| EC2 us-east-1 | Primary endpoint, t3.micro | ~$8/month |
| EC2 us-west-2 | Secondary endpoint, t3.micro | ~$8/month |

## Input / Output

### Input

| Parameter | Value |
|---|---|
| Domain name | `lab.example.com` (or any Route 53 hosted zone) |
| Primary endpoint | EC2 EIP in us-east-1 (or ALB DNS) |
| Secondary endpoint | EC2 EIP in us-west-2 (or ALB DNS) |
| Weighted split | 70 (primary) + 30 (secondary) |
| Health check path | `GET /health` expects HTTP 200 |
| Health check interval | 30 seconds (standard) |
| TTL on weighted records | 60 seconds |

### Output

| Resource | Result |
|---|---|
| Weighted DNS | `lab.example.com` resolves to primary 70% of the time |
| Latency DNS | `latency.example.com` resolves to us-east-1 or us-west-2 based on resolver proximity |
| Failover behavior | If health check fails, the unhealthy record is excluded from DNS responses |
| Health check status | Visible in Route 53 console under Health Checks → Status |
| Query count | Tracked in CloudWatch metric `Route53/HealthCheckStatus` |

## Architecture

```
  DNS Query: lab.example.com
          │
  ┌───────▼──────────────────────────────────┐
  │  Route 53 Hosted Zone: example.com       │
  │                                          │
  │  Weighted Records (SetIdentifier):       │
  │  ├─ primary  Weight=70 → 54.x.x.x (1a)  │
  │  └─ secondary Weight=30 → 52.x.x.x (1b) │
  │                                          │
  │  Latency Records:                        │
  │  ├─ us-east-1 → ALB-east DNS             │
  │  └─ us-west-2 → ALB-west DNS             │
  │                                          │
  │  Health Checks:                          │
  │  ├─ hc-east: GET 54.x.x.x/health :80    │
  │  └─ hc-west: GET 52.x.x.x/health :80    │
  └──────────────────────────────────────────┘
         │                    │
  [EC2 us-east-1]      [EC2 us-west-2]
  54.x.x.x              52.x.x.x
```

## Quick Start

```cmd
REM Step 1: Create hosted zone (skip if already exists)
aws route53 create-hosted-zone ^
  --name example.com ^
  --caller-reference 2024-project24

REM Step 2: Create health check for primary endpoint (us-east-1)
aws route53 create-health-check ^
  --caller-reference hc-east-2024 ^
  --health-check-config ^
    IPAddress=<EC2_EAST_EIP>,Port=80,Type=HTTP,ResourcePath=/health,^
    RequestInterval=30,FailureThreshold=3

REM Step 3: Create health check for secondary endpoint (us-west-2)
aws route53 create-health-check ^
  --caller-reference hc-west-2024 ^
  --health-check-config ^
    IPAddress=<EC2_WEST_EIP>,Port=80,Type=HTTP,ResourcePath=/health,^
    RequestInterval=30,FailureThreshold=3

REM Step 4: Create weighted A record — primary (weight 70)
aws route53 change-resource-record-sets ^
  --hosted-zone-id <ZONE_ID> ^
  --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"lab.example.com\",\"Type\":\"A\",\"SetIdentifier\":\"primary\",\"Weight\":70,\"TTL\":60,\"ResourceRecords\":[{\"Value\":\"<EC2_EAST_EIP>\"}],\"HealthCheckId\":\"<HC_EAST_ID>\"}}]}"

REM Step 5: Create weighted A record — secondary (weight 30)
aws route53 change-resource-record-sets ^
  --hosted-zone-id <ZONE_ID> ^
  --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"lab.example.com\",\"Type\":\"A\",\"SetIdentifier\":\"secondary\",\"Weight\":30,\"TTL\":60,\"ResourceRecords\":[{\"Value\":\"<EC2_WEST_EIP>\"}],\"HealthCheckId\":\"<HC_WEST_ID>\"}}]}"

REM Step 6: Create latency record for us-east-1
aws route53 change-resource-record-sets ^
  --hosted-zone-id <ZONE_ID> ^
  --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"latency.example.com\",\"Type\":\"A\",\"SetIdentifier\":\"latency-east\",\"Region\":\"us-east-1\",\"TTL\":60,\"ResourceRecords\":[{\"Value\":\"<EC2_EAST_EIP>\"}],\"HealthCheckId\":\"<HC_EAST_ID>\"}}]}"

REM Step 7: Create latency record for us-west-2
aws route53 change-resource-record-sets ^
  --hosted-zone-id <ZONE_ID> ^
  --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"latency.example.com\",\"Type\":\"A\",\"SetIdentifier\":\"latency-west\",\"Region\":\"us-west-2\",\"TTL\":60,\"ResourceRecords\":[{\"Value\":\"<EC2_WEST_EIP>\"}],\"HealthCheckId\":\"<HC_WEST_ID>\"}}]}"

REM Step 8: Verify DNS resolution (run from multiple locations for latency test)
nslookup lab.example.com 8.8.8.8
nslookup latency.example.com 8.8.8.8

REM Step 9: Check health check status
aws route53 get-health-check-status --health-check-id <HC_EAST_ID>
```

## Data Flow

1. Client's stub resolver queries its configured DNS server (e.g., `8.8.8.8`) for `lab.example.com`.
2. The recursive resolver has no cached answer (or TTL expired) and queries Route 53's authoritative name servers.
3. Route 53 evaluates weighted records: both health checks are passing, so it returns the primary IP 70% of the time and secondary IP 30% of the time based on the weight ratio.
4. If a health check is failing, Route 53 excludes that record and returns only the healthy endpoint — the weight of the surviving record effectively becomes 100%.
5. For `latency.example.com`, Route 53 measures the latency from the resolver's IP to each configured AWS region and returns the record for the closest region.
6. The resolver caches the returned A record for 60 seconds (the TTL); during that window, the same IP is returned to clients regardless of weight or health changes.
7. After 60 seconds the TTL expires, the resolver re-queries Route 53, and any routing policy changes (including health check exclusions) take effect for new queries.

## Project Files

| File | Description |
|---|---|
| `README.md` | This document |
| `create-hosted-zone.sh` | Creates the Route 53 hosted zone |
| `weighted-records.sh` | Creates weighted A records with health check associations |
| `latency-records.sh` | Creates latency-based records for us-east-1 and us-west-2 |
| `health-checks.sh` | Creates HTTP health checks for both endpoints |
| `test-failover.sh` | Stops the primary EC2 and polls DNS to measure failover time |

## Lessons Learned

- **Route 53 is a global service, not regional:** The hosted zone is created once and served from Route 53's global anycast network. You do not specify a region when creating a hosted zone — unlike almost every other AWS service.
- **Weighted routing uses relative ratios, not percentages:** Setting weights 70 and 30 produces the same split as weights 7 and 3, or 700 and 300. Route 53 divides each weight by the total. A weight of 0 means the record is never returned (useful to temporarily remove a target).
- **Latency routing measures resolver-to-region, not client-to-instance:** Route 53 looks up the approximate location of the recursive resolver IP, not the end user's IP. A user in Europe using Google DNS (`8.8.8.8`) may be routed to us-east-1 if Google's resolver is closer to Virginia than Oregon.
- **Health check interval 10s (fast) costs 3× more than 30s (standard):** Fast health checks ($1.00/month each) detect failures in ~20 seconds. Standard health checks ($0.50/month each) can take up to 90 seconds to mark a record unhealthy. Use fast for production failover SLAs.
- **TTL directly controls failover speed:** A TTL of 300 seconds means cached DNS responses persist for 5 minutes after a health check marks an endpoint unhealthy. Set TTL to 60 seconds or lower for records associated with health checks.
- **Alias records are free; CNAME records are charged per query:** When pointing to an AWS resource (ALB, CloudFront, S3), use an Alias record. Alias records resolve server-side and do not appear as a separate DNS query. CNAME records require an additional lookup and are billed at standard query rates.
