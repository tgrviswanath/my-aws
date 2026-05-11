# Steps — Project 7.1 CloudWatch Monitoring System

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="alert_email=your@email.com" \
  -var="alb_arn_suffix=$(aws elbv2 describe-load-balancers --names handson-flask-api-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text | cut -d'/' -f2-)"

terraform output dashboard_url
```

---

## Phase 2 — Generate Traffic to Populate Metrics

```bash
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"

# Generate normal traffic
for i in {1..100}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/items  > /dev/null
  sleep 0.1
done

# Generate some errors
curl $ALB_URL/nonexistent-path
curl -X POST $ALB_URL/items -d 'invalid json'
```

---

## Phase 3 — View Dashboard

```bash
# Open dashboard URL from terraform output
# Or navigate: CloudWatch → Dashboards → handson-overview
```

---

## Phase 4 — Test Alarms

```bash
# Trigger CPU alarm by running a CPU-intensive task in the container
# (or lower the threshold temporarily for testing)

# Manually set alarm state for testing
aws cloudwatch set-alarm-state \
  --alarm-name "handson-ecs-cpu-high" \
  --state-value ALARM \
  --state-reason "Testing alarm notification"

# Check your email for the SNS notification
# Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name "handson-ecs-cpu-high" \
  --state-value OK \
  --state-reason "Test complete"
```

---

## Phase 5 — Log Insights Queries

```bash
# Run saved query via CLI
aws logs start-query \
  --log-group-name /ecs/handson-flask-api \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string "fields @timestamp, @message | filter @message like /ERROR/ | limit 20"

# Get results
QUERY_ID=$(aws logs start-query ... --query queryId --output text)
aws logs get-query-results --query-id $QUERY_ID
```

---

## Screenshots to Take
- [ ] CloudWatch dashboard showing all 4 widgets
- [ ] Alarm in ALARM state (red) after manual trigger
- [ ] Email notification received from SNS
- [ ] Log Insights query results
- [ ] Composite alarm showing combined state
- [ ] `terraform apply` success with dashboard URL
