# Verification & Validation — Project 2.4 Route53 Advanced Routing

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Health Check | Route53 → Health checks | `primary-health-check`, Status = **Healthy** |
| CloudWatch Alarm | CloudWatch → Alarms | Health check alarm, State = OK |
| Weighted Records | Route53 → Hosted zone | 2 A records for `app.yourdomain.com`, weights 90 + 10 |
| Failover Records | Route53 → Hosted zone | PRIMARY + SECONDARY records for `failover.yourdomain.com` |
| Latency Records | Route53 → Hosted zone | Records with Region attribute set |

📸 Screenshot: Health check showing Status = Healthy (green)  
📸 Screenshot: Weighted records showing 90/10 split  
📸 Screenshot: Failover test — DNS switching to secondary after primary stops

---

## 2. AWS CLI Verification

```bash
ZONE_ID=YOUR_HOSTED_ZONE_ID

# 2.1 Health check is healthy
HC_ID=$(aws route53 list-health-checks \
  --query "HealthChecks[?HealthCheckConfig.FullyQualifiedDomainName!=null].Id" \
  --output text | head -1)
aws route53 get-health-check-status --health-check-id $HC_ID \
  --query "HealthCheckObservations[*].{Region:Region,Status:StatusReport.Status}"
# Expected: Success from all regions

# 2.2 Weighted records exist with correct weights
aws route53 list-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --query "ResourceRecordSets[?Name=='app.yourdomain.com.'].{ID:SetIdentifier,Weight:Weight,Value:ResourceRecords[0].Value}"
# Expected: v1-primary=90, v2-canary=10

# 2.3 Failover records exist
aws route53 list-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --query "ResourceRecordSets[?Name=='failover.yourdomain.com.'].{ID:SetIdentifier,Failover:Failover,HC:HealthCheckId}"
# Expected: PRIMARY (with HC), SECONDARY (no HC)

# 2.4 Weighted routing test — ~10% should hit v2
for i in {1..10}; do
  nslookup app.yourdomain.com | grep "Address:" | tail -1
done
# Expected: mostly v1 IP, ~1 hit on v2 IP

# 2.5 Failover test
# Stop primary instance
aws ec2 stop-instances --instance-ids PRIMARY_INSTANCE_ID
# Wait ~90s for health check to fail
sleep 100
nslookup failover.yourdomain.com
# Expected: secondary IP now returned

# Restart primary
aws ec2 start-instances --instance-ids PRIMARY_INSTANCE_ID
sleep 60
nslookup failover.yourdomain.com
# Expected: primary IP returned again (failback)

# 2.6 Run DNS checker
python code/dns_checker.py --hosted-zone-id $ZONE_ID
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_route53_health_check.primary
# aws_route53_record.weighted_v1
# aws_route53_record.weighted_v2
# aws_route53_record.failover_primary
# aws_route53_record.failover_secondary
# aws_cloudwatch_metric_alarm.health_check

terraform state show aws_route53_health_check.primary
# Shows: fqdn, port=80, resource_path=/health,
#        request_interval=30, failure_threshold=3

terraform state show aws_route53_record.weighted_v1
# Shows: weighted_routing_policy.weight=90

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Failover Timing

```bash
# Measure actual failover time
START=$(date +%s)
aws ec2 stop-instances --instance-ids PRIMARY_INSTANCE_ID

while true; do
  RESOLVED=$(nslookup failover.yourdomain.com 2>/dev/null | grep "Address:" | tail -1 | awk '{print $2}')
  if [ "$RESOLVED" = "$SECONDARY_IP" ]; then
    END=$(date +%s)
    echo "Failover completed in $((END - START)) seconds"
    break
  fi
  echo "Still resolving to primary... ($(( $(date +%s) - START ))s)"
  sleep 10
done
# Expected: failover in ~90-120s (3 failures × 30s interval + TTL)
```

---

## 5. Expected Successful Outputs

**Health check status:**
```json
[
  { "Region": "us-east-1", "Status": "Success" },
  { "Region": "us-west-2", "Status": "Success" },
  { "Region": "eu-west-1", "Status": "Success" }
]
```

**Weighted records:**
```json
[
  { "ID": "v1-primary", "Weight": 90, "Value": "PRIMARY_IP" },
  { "ID": "v2-canary",  "Weight": 10, "Value": "SECONDARY_IP" }
]
```

**dns_checker.py output:**
```
Hosted Zone: yourdomain.com
Records: 8 total
  app.yourdomain.com    Weighted   v1-primary (90) → PRIMARY_IP
  app.yourdomain.com    Weighted   v2-canary  (10) → SECONDARY_IP
  failover.yourdomain.com  Failover  primary   → PRIMARY_IP  [HC: Healthy]
  failover.yourdomain.com  Failover  secondary → SECONDARY_IP
```

---

## 6. Verification Checklist

- [ ] Health check `primary-health-check` status = Healthy
- [ ] CloudWatch alarm for health check state = OK
- [ ] Weighted records: `app.yourdomain.com` with weights 90 + 10
- [ ] Failover records: PRIMARY (with HC) + SECONDARY
- [ ] Weighted routing: ~10% of requests hit v2 (test with 10 nslookups)
- [ ] Failover: stopping primary → DNS switches to secondary within ~120s
- [ ] Failback: restarting primary → DNS returns to primary
- [ ] Latency records created with Region attribute
- [ ] `terraform plan` shows no changes
- [ ] `dns_checker.py` shows all records with correct routing policies

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
