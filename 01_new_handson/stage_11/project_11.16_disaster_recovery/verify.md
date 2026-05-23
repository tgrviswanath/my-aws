# Verification & Validation — Project 11.16 Disaster Recovery Network

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Primary ALB | EC2 → Load Balancers (us-east-1) | `alb-primary-11-16`, State = active |
| DR ALB | EC2 → Load Balancers (us-west-2) | `alb-dr-11-16`, State = active |
| Health Check | Route 53 → Health checks | `hc-primary-11-16`, Status = **Healthy** |
| Primary DNS Record | Route 53 → Hosted zone | `app.yourdomain.com`, Failover = PRIMARY, HC attached |
| Secondary DNS Record | Route 53 → Hosted zone | `app.yourdomain.com`, Failover = SECONDARY |
| DNS Resolution | nslookup | Resolves to primary ALB under normal conditions |

📸 Screenshot: Route 53 health check showing Status = Healthy (green)  
📸 Screenshot: Both failover DNS records (PRIMARY + SECONDARY) in hosted zone  
📸 Screenshot: DNS failover in action — nslookup returning DR ALB IP after primary failure

---

## 2. AWS CLI Verification

```bash
# 2.1 Health check status from all Route 53 health checker regions
aws route53 get-health-check-status --health-check-id $HC_ID \
  --query "HealthCheckObservations[*].{Region:Region,Status:StatusReport.Status}"
# Expected: Success from all regions

# 2.2 Failover DNS records
aws route53 list-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --query "ResourceRecordSets[?Name=='app.yourdomain.com.'].{Name:Name,Failover:Failover,HC:HealthCheckId}"
# Expected: PRIMARY record with HC, SECONDARY record without HC

# 2.3 DNS resolves to primary under normal conditions
nslookup app.yourdomain.com
# Expected: primary ALB IP

# 2.4 Simulate failure — stop primary EC2s
aws ec2 stop-instances --instance-ids <PRIMARY_EC2_IDS> --region us-east-1

# 2.5 Watch health check fail
aws route53 get-health-check-status --health-check-id $HC_ID \
  --query "HealthCheckObservations[0].StatusReport.Status"
# Expected: changes to "Failure" within ~30s

# 2.6 After 60-90s — DNS switches to DR
sleep 90
nslookup app.yourdomain.com
# Expected: DR ALB IP (us-west-2)
curl http://app.yourdomain.com/health
# Expected: 200 OK from DR region
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected (key resources):
# aws_lb.primary          (us-east-1 provider)
# aws_lb.dr               (us-west-2 provider)
# aws_route53_health_check.primary
# aws_route53_record.primary
# aws_route53_record.secondary

terraform state show aws_route53_health_check.primary
# Shows: fqdn, port=80, resource_path=/health, request_interval=10, failure_threshold=3

terraform state show aws_route53_record.primary
# Shows: failover_routing_policy=PRIMARY, health_check_id set

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — RTO Measurement

```bash
# Measure actual Recovery Time Objective:
START=$(date +%s)

# Stop primary instances
aws ec2 stop-instances --instance-ids <PRIMARY_EC2_IDS> --region us-east-1

# Poll until DR responds
while true; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://app.yourdomain.com/health)
  if [ "$RESPONSE" = "200" ]; then
    END=$(date +%s)
    echo "RTO: $((END - START)) seconds"
    break
  fi
  echo "Waiting... ($(( $(date +%s) - START ))s elapsed)"
  sleep 5
done
# Record this RTO — target for warm standby is < 2 minutes
```

---

## 5. Expected Successful Outputs

**Health check status (normal):**
```json
[
  { "Region": "us-east-1", "Status": "Success" },
  { "Region": "us-west-2", "Status": "Success" },
  { "Region": "eu-west-1", "Status": "Success" }
]
```

**DNS during failover:**
```
Before failure: app.yourdomain.com → 52.x.x.x (primary ALB, us-east-1)
After failure:  app.yourdomain.com → 54.x.x.x (DR ALB, us-west-2)
```

**RTO measurement:**
```
RTO: 87 seconds   ← typical warm standby failover time
```

---

## 6. Verification Checklist

- [ ] Primary VPC with ALB and EC2 in us-east-1
- [ ] DR VPC with ALB and EC2 in us-west-2
- [ ] Route 53 health check monitoring primary ALB `/health`
- [ ] Health check status = Healthy under normal conditions
- [ ] DNS resolves to primary ALB under normal conditions
- [ ] Stopping primary EC2 → health check fails within 30s
- [ ] DNS switches to DR ALB within 60-90s of failure
- [ ] `curl app.yourdomain.com` returns 200 from DR region
- [ ] Restarting primary → health check passes → DNS switches back (failback)
- [ ] RTO measured and documented
- [ ] `terraform plan` shows no changes
