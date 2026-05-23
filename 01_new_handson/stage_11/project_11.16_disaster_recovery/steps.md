# Steps — Project 11.16 Disaster Recovery Network

## Phase 1 — Console

### 1.1 Create Primary VPC (us-east-1)
- VPC: `vpc-primary-11-16`, CIDR: `10.0.0.0/16`
- Public subnets: `10.0.1.0/24` (AZ-a), `10.0.2.0/24` (AZ-b)
- Private subnets: `10.0.3.0/24` (AZ-a), `10.0.4.0/24` (AZ-b)
- IGW, NAT Gateway, route tables
- ALB: `alb-primary-11-16` in public subnets
- EC2 web servers in private subnets behind ALB
- Health check endpoint: `/health` returns 200

### 1.2 Create DR VPC (us-west-2)
- VPC: `vpc-dr-11-16`, CIDR: `10.1.0.0/16`
- Public subnets: `10.1.1.0/24` (AZ-a), `10.1.2.0/24` (AZ-b)
- Private subnets: `10.1.3.0/24` (AZ-a), `10.1.4.0/24` (AZ-b)
- IGW, NAT Gateway, route tables
- ALB: `alb-dr-11-16` in public subnets
- Minimal EC2 (1 instance) in private subnet

### 1.3 Create Route 53 Health Check for Primary
1. **Route 53** → **Health checks** → **Create**
2. Name: `hc-primary-11-16`
3. What to monitor: Endpoint
4. Protocol: HTTP, Port: 80
5. Domain: `<alb-primary-11-16 DNS name>`
6. Path: `/health`
7. Request interval: 10 seconds
8. Failure threshold: 3

### 1.4 Create Route 53 Failover Records
1. **Route 53** → **Hosted zones** → your domain → **Create record**

**Primary record:**
- Name: `app.yourdomain.com`
- Type: A (Alias → ALB primary)
- Routing policy: Failover
- Failover record type: Primary
- Health check: `hc-primary-11-16`
- TTL: 60

**Secondary record:**
- Name: `app.yourdomain.com`
- Type: A (Alias → ALB DR)
- Routing policy: Failover
- Failover record type: Secondary
- No health check needed

---

## Phase 2 — AWS CLI

```bash
# Create health check
HC_ID=$(aws route53 create-health-check \
  --caller-reference "hc-primary-$(date +%s)" \
  --health-check-config '{
    "Type": "HTTP",
    "FullyQualifiedDomainName": "<ALB_PRIMARY_DNS>",
    "Port": 80,
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3
  }' \
  --query "HealthCheck.Id" --output text)
aws route53 change-tags-for-resource \
  --resource-type healthcheck --resource-id $HC_ID \
  --add-tags Key=Name,Value=hc-primary-11-16
echo "Health Check ID: $HC_ID"

# Create failover DNS records
HOSTED_ZONE_ID=<your-hosted-zone-id>
ALB_PRIMARY_DNS=<alb-primary-dns>
ALB_DR_DNS=<alb-dr-dns>
ALB_PRIMARY_ZONE=Z35SXDOTRQ7X7K  # us-east-1 ALB hosted zone
ALB_DR_ZONE=Z1H1FL5HABSF5       # us-west-2 ALB hosted zone

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.yourdomain.com",
          "Type": "A",
          "SetIdentifier": "primary",
          "Failover": "PRIMARY",
          "HealthCheckId": "'$HC_ID'",
          "AliasTarget": {
            "HostedZoneId": "'$ALB_PRIMARY_ZONE'",
            "DNSName": "'$ALB_PRIMARY_DNS'",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.yourdomain.com",
          "Type": "A",
          "SetIdentifier": "secondary",
          "Failover": "SECONDARY",
          "AliasTarget": {
            "HostedZoneId": "'$ALB_DR_ZONE'",
            "DNSName": "'$ALB_DR_DNS'",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check health check status
aws route53 get-health-check-status --health-check-id $HC_ID \
  --query "HealthCheckObservations[*].{Region:Region,Status:StatusReport.Status}"
# Expected: Healthy from all regions

# 2. Verify DNS resolves to primary ALB
nslookup app.yourdomain.com
# Should return primary ALB IP

# 3. Check failover record configuration
aws route53 list-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --query "ResourceRecordSets[?Name=='app.yourdomain.com.']"
# Should show PRIMARY and SECONDARY records
```

---

## Phase 5 — Test

```bash
# Test 1: Normal operation — traffic goes to primary
curl http://app.yourdomain.com/health
# Expected: 200 OK from primary region

# Test 2: Simulate primary failure
# Stop all EC2 instances in primary region OR block port 80 on ALB SG
aws ec2 stop-instances --instance-ids <PRIMARY_EC2_IDS> --region us-east-1

# Watch health check status change
watch -n 5 'aws route53 get-health-check-status --health-check-id $HC_ID \
  --query "HealthCheckObservations[0].StatusReport.Status"'
# Expected: changes from "Success" to "Failure" within ~30s

# Test 3: Verify DNS failover
# Wait 60-90s for health check to fail + DNS TTL to expire
sleep 90
nslookup app.yourdomain.com
# Should now return DR ALB IP (us-west-2)

curl http://app.yourdomain.com/health
# Expected: 200 OK from DR region

# Test 4: Restore primary and verify failback
aws ec2 start-instances --instance-ids <PRIMARY_EC2_IDS> --region us-east-1
# Wait for health check to pass again (~30s)
sleep 90
nslookup app.yourdomain.com
# Should return primary ALB IP again

# Test 5: Measure RTO (Recovery Time Objective)
# Time from: stopping primary instances
# Time to: curl returns 200 from DR
# Record this time — it should be < 2 minutes for warm standby

# Run automated checker
python code/dr_checker.py --hc-id $HC_ID --domain app.yourdomain.com
```

### Verification Checklist
- [ ] Primary VPC with ALB and EC2 in us-east-1
- [ ] DR VPC with ALB and EC2 in us-west-2
- [ ] Route 53 health check monitoring primary ALB `/health`
- [ ] Health check status = Healthy
- [ ] DNS resolves to primary ALB under normal conditions
- [ ] Stopping primary EC2 → health check fails within 30s
- [ ] DNS switches to DR ALB within 60-90s of failure
- [ ] `curl app.yourdomain.com` returns 200 from DR region
- [ ] Restarting primary → health check passes → DNS switches back
- [ ] RTO measured and documented

---

## Teardown
```bash
terraform destroy  # run for both regions
# Also delete Route 53 health check and failover records
```
