# Steps — Project 2.4 Route53 Advanced Routing

## Prerequisites
- A registered domain in Route53 (or transferred to Route53)
- At least 2 EC2 instances or ALBs to route between

---

## Phase 1 — Health Checks

### 1.1 Create Health Check for Primary Endpoint
1. **Route53** → **Health checks** → **Create**
2. What to monitor: Endpoint
3. Protocol: HTTP, IP: your primary EC2 IP, Port: 80, Path: `/health`
4. Request interval: 30 seconds
5. Failure threshold: 3
6. Name: `primary-health-check`

### 1.2 Create CloudWatch Alarm for Health Check
1. After creating health check, click **Create alarm**
2. Notify SNS topic: `billing-alerts` (from Project 0.4)
3. This alerts you when the primary goes down

---

## Phase 2 — Weighted Routing (A/B Testing)

```bash
# Create weighted records — 90% to v1, 10% to v2
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.yourdomain.com",
          "Type": "A",
          "SetIdentifier": "v1-primary",
          "Weight": 90,
          "TTL": 60,
          "ResourceRecords": [{"Value": "PRIMARY_EC2_IP"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.yourdomain.com",
          "Type": "A",
          "SetIdentifier": "v2-canary",
          "Weight": 10,
          "TTL": 60,
          "ResourceRecords": [{"Value": "SECONDARY_EC2_IP"}]
        }
      }
    ]
  }'

# Test: run 10 times, ~1 should hit v2
for i in {1..10}; do
  curl -s http://app.yourdomain.com | grep "Server"
done
```

---

## Phase 3 — Failover Routing

```bash
# Primary record (active)
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "failover.yourdomain.com",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "TTL": 30,
        "HealthCheckId": "YOUR_HEALTH_CHECK_ID",
        "ResourceRecords": [{"Value": "PRIMARY_IP"}]
      }
    }]
  }'

# Secondary record (passive — only used if primary fails)
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "failover.yourdomain.com",
        "Type": "A",
        "SetIdentifier": "secondary",
        "Failover": "SECONDARY",
        "TTL": 30,
        "ResourceRecords": [{"Value": "SECONDARY_IP"}]
      }
    }]
  }'
```

### Test Failover
```bash
# Verify primary is serving
curl http://failover.yourdomain.com

# Stop primary EC2 instance
aws ec2 stop-instances --instance-ids PRIMARY_INSTANCE_ID

# Wait for health check to fail (~90 seconds with 3 failures at 30s interval)
# Then test again — should now hit secondary
sleep 120
curl http://failover.yourdomain.com

# Restart primary
aws ec2 start-instances --instance-ids PRIMARY_INSTANCE_ID
```

---

## Phase 4 — Latency Routing

```bash
# Record in us-east-1
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "latency.yourdomain.com",
        "Type": "A",
        "SetIdentifier": "us-east-1",
        "Region": "us-east-1",
        "TTL": 60,
        "ResourceRecords": [{"Value": "US_EAST_IP"}]
      }
    }]
  }'

# Record in eu-west-1 (if you have a resource there)
# Route53 will route each user to the lowest-latency region
```

---

## Phase 5 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

---

## Screenshots to Take
- [ ] Health check showing Healthy status (green)
- [ ] Weighted records showing 90/10 split
- [ ] Failover test: primary down → traffic shifts to secondary
- [ ] CloudWatch alarm triggered when health check fails
- [ ] Route53 record sets in hosted zone
- [ ] `terraform apply` success output
