# Cost Estimate — Project 2.4: Route 53 DNS and Intelligent Traffic Routing

## Architecture Summary
Route 53 public hosted zone for `myapp.example.com` with weighted A records (50/50 A/B split), 2 health checks monitoring EC2 targets every 30s, and optional latency-based and failover records.

---

## ⚠️ Free Tier Status for Route 53

Route 53 has **no free tier** for hosted zones and query charges apply from the first query. However, Route 53 is one of AWS's most affordable services — a full month of realistic lab usage typically costs less than $2.

---

## Pricing Breakdown

### Hosted Zone Cost

| Zone Type | Cost |
|---|---|
| Public hosted zone | **$0.50/month** (first 25 zones) |
| Private hosted zone | **$0.50/month** (per VPC association) |
| Additional hosted zones | $0.10/month each (after 25) |

> Deleting a hosted zone within 12 hours of creation incurs no charge. After 12 hours, you're billed for that month.

### DNS Query Cost

| Query Type | Rate |
|---|---|
| Standard queries (first 1 billion/month) | $0.40 per million queries |
| Standard queries (over 1 billion/month) | $0.20 per million queries |
| Latency-based routing queries | $0.60 per million queries |
| Geo DNS / Geoproximity queries | $0.70 per million queries |
| Alias record queries (to AWS resources) | **$0.00 — Free** |

> 💡 **Key optimization:** Use Alias records to route to ALB, CloudFront, or S3 instead of A records with IPs — Alias record queries are free.

### Health Check Cost

| Health Check Type | Cost |
|---|---|
| HTTP/HTTPS/TCP endpoint | **$0.50/month per health check** |
| Fast interval (10s instead of 30s) | +$1.00/month per health check |
| HTTPS with SNI | $0.75/month per health check |
| Calculated health check (combines others) | $0.50/month |
| CloudWatch alarm health check | $0.50/month |

---

## Lab Session Cost Estimate

| Component | Quantity | Cost/Month | Lab Cost (1 week) |
|---|---|---|---|
| Public hosted zone | 1 | $0.50 | $0.50 |
| DNS queries (lab testing) | ~10,000 queries | $0.004 | < $0.01 |
| Health check — v1 EC2 | 1 (standard 30s) | $0.50 | $0.50 |
| Health check — v2 EC2 | 1 (standard 30s) | $0.50 | $0.50 |
| Latency-based routing queries | ~5,000 | $0.003 | < $0.01 |
| **Total (1 month)** | | **~$1.50** | |
| **Total (1 week lab session)** | | | **~$1.00** |

> ✅ **Very affordable** — Route 53 is one of the cheapest AWS services to learn with.

---

## Cost Scenarios

| Scenario | Monthly Cost | Notes |
|---|---|---|
| Minimal lab (1 zone, no health checks) | $0.50 | Just hosted zone + minimal queries |
| Standard lab (1 zone + 2 health checks) | ~$1.50 | This project's setup |
| Production setup (1 zone + 4 health checks + HTTPS) | ~$3.50 | 4 HTTPS health checks at $0.75 each |
| Multi-region failover (1 zone + 4 health checks + latency routing) | ~$4-5 | Latency queries cost more |
| Large production (10 zones + 20 health checks) | ~$15 | Still cheap vs other infrastructure |

---

## Alias Record Optimization (Free Queries)

Replace expensive A record queries with free Alias records when pointing to AWS resources:

| Record Type | Target | Query Cost |
|---|---|---|
| A record → EC2 IP | Raw IP address | $0.40/million |
| ✅ Alias → ALB DNS | ALB DNS name | **$0.00** |
| ✅ Alias → CloudFront | CloudFront distribution | **$0.00** |
| ✅ Alias → S3 static site | S3 website endpoint | **$0.00** |
| ✅ Alias → API Gateway | API GW custom domain | **$0.00** |
| ✅ Alias → another Route 53 record | Same hosted zone | **$0.00** |

For this lab's weighted routing, switching from raw IP A records to ALB Alias records saves the $0.40/million query charge.

---

## Health Check Frequency Trade-off

| Setting | Detection Time | Extra Cost | Use Case |
|---|---|---|---|
| Standard 30s (3 failures) | ~90 seconds | $0 | General lab and most production |
| Fast 10s (3 failures) | ~30 seconds | +$1.00/month per check | Critical production, low RTO requirement |

For a lab with 2 health checks, fast interval would add $2.00/month — not worth it for learning purposes.

---

## Cleanup Commands

### Delete in Correct Order (records before zone)

```bash
ZONE_ID="ZXXXXXXXXXXXXXXXXXX"    # Your hosted zone ID
DOMAIN="myapp.yourdomain.com"
EC2_V1_IP="1.2.3.4"
EC2_V2_IP="5.6.7.8"
HC_V1_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
HC_V2_ID="yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"

# Step 1: Delete all custom A records (you must provide exact values for deletion)
aws route53 change-resource-record-sets \
  --hosted-zone-id ${ZONE_ID} \
  --change-batch "{
    \"Changes\": [
      {\"Action\": \"DELETE\", \"ResourceRecordSet\": {
        \"Name\": \"app.${DOMAIN}\", \"Type\": \"A\",
        \"SetIdentifier\": \"v1-production\", \"Weight\": 50,
        \"TTL\": 60, \"ResourceRecords\": [{\"Value\": \"${EC2_V1_IP}\"}],
        \"HealthCheckId\": \"${HC_V1_ID}\"
      }},
      {\"Action\": \"DELETE\", \"ResourceRecordSet\": {
        \"Name\": \"app.${DOMAIN}\", \"Type\": \"A\",
        \"SetIdentifier\": \"v2-canary\", \"Weight\": 50,
        \"TTL\": 60, \"ResourceRecords\": [{\"Value\": \"${EC2_V2_IP}\"}],
        \"HealthCheckId\": \"${HC_V2_ID}\"
      }}
    ]
  }"
echo "Custom records deleted"

# Step 2: Delete health checks
aws route53 delete-health-check --health-check-id ${HC_V1_ID}
aws route53 delete-health-check --health-check-id ${HC_V2_ID}
echo "Health checks deleted — $0.50/month each billing stops"

# Step 3: Delete the hosted zone (only works when empty of custom records)
# NS and SOA records are deleted automatically
aws route53 delete-hosted-zone --id ${ZONE_ID}
echo "Hosted zone deleted — $0.50/month billing stops"
```

### Verify Cleanup
```bash
# Confirm zone is gone
aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='myapp.yourdomain.com.']" \
  --output text

# Confirm health checks are gone
aws route53 list-health-checks \
  --query "HealthChecks[?HealthCheckConfig.IPAddress=='${EC2_V1_IP}']" \
  --output text

echo "Cleanup complete if both outputs are empty."
```

---

## Cost Summary

| Item | Monthly | Notes |
|---|---|---|
| Hosted zone | $0.50 | First 25 zones |
| Standard DNS queries | ~$0.004 | Per million: $0.40 |
| HTTP health checks × 2 | $1.00 | $0.50 each |
| **Total (typical lab month)** | **~$1.50** | Very affordable |
| **Total if deleted within 1 week** | **~$0.50–1.00** | Proportional to days used |

> Route 53 is one of AWS's most cost-effective services. The entire lab costs about as much as a cup of coffee for the month.

---

*Region: Global service | Prices as of 2024 — verify at https://aws.amazon.com/route53/pricing/*
