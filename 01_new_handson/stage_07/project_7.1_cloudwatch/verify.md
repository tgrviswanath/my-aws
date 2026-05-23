# Verification & Validation — Project 7.1 CloudWatch Monitoring System

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| SNS Topic | SNS → Topics | `handson-alerts` listed |
| SNS Subscription | SNS → Subscriptions | Email subscription = **Confirmed** |
| CloudWatch Alarms | CloudWatch → Alarms | All alarms listed, state = **OK** or **INSUFFICIENT_DATA** |
| CloudWatch Dashboard | CloudWatch → Dashboards | `handson-overview` dashboard exists |
| Log Group | CloudWatch → Log Groups | `/ecs/handson-flask-api` with retention = 30 days |
| Log Insights Queries | CloudWatch → Logs Insights | Saved queries visible |
| Composite Alarm | CloudWatch → Alarms | `handson-composite-alarm` listed |

📸 Screenshot: CloudWatch Alarms list showing all alarms  
📸 Screenshot: Dashboard `handson-overview` with all 4 widgets populated  
📸 Screenshot: Alarm in ALARM state (red) after manual trigger  
📸 Screenshot: Email notification received from SNS

---

## 2. AWS CLI Verification

```bash
# 2.1 List all alarms and their states
aws cloudwatch describe-alarms \
  --alarm-name-prefix "handson-" \
  --query "MetricAlarms[*].{Name:AlarmName,State:StateValue,Metric:MetricName}"
# Expected: all alarms listed with state OK or INSUFFICIENT_DATA

# 2.2 Confirm dashboard exists
aws cloudwatch list-dashboards \
  --query "DashboardEntries[*].{Name:DashboardName,Size:Size}"
# Expected: handson-overview listed

# 2.3 Confirm log group with retention
aws logs describe-log-groups \
  --log-group-name-prefix "/ecs/handson" \
  --query "logGroups[*].{Name:logGroupName,Retention:retentionInDays}"
# Expected: retentionInDays=30

# 2.4 Confirm SNS topic exists
aws sns list-topics \
  --query "Topics[*].TopicArn" | grep handson-alerts
# Expected: ARN printed

# 2.5 Confirm SNS subscription confirmed
aws sns list-subscriptions-by-topic \
  --topic-arn $(aws sns list-topics --query "Topics[?contains(TopicArn,'handson-alerts')].TopicArn" --output text) \
  --query "Subscriptions[*].{Protocol:Protocol,Status:SubscriptionArn}"
# Expected: Protocol=email, Status not PendingConfirmation

# 2.6 Manually trigger alarm and verify notification
aws cloudwatch set-alarm-state \
  --alarm-name "handson-ecs-cpu-high" \
  --state-value ALARM \
  --state-reason "Verification test"
# Check email for SNS notification, then reset:
aws cloudwatch set-alarm-state \
  --alarm-name "handson-ecs-cpu-high" \
  --state-value OK \
  --state-reason "Verification complete"

# 2.7 Run a Log Insights query
QUERY_ID=$(aws logs start-query \
  --log-group-name /ecs/handson-flask-api \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string "fields @timestamp, @message | limit 5" \
  --query queryId --output text)
sleep 5
aws logs get-query-results --query-id $QUERY_ID \
  --query "results[*][?field=='@message'].value"
# Expected: log entries returned
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources in state
terraform state list
# Expected:
# aws_cloudwatch_metric_alarm.cpu_high
# aws_cloudwatch_metric_alarm.memory_high
# aws_cloudwatch_metric_alarm.error_rate
# aws_cloudwatch_metric_alarm.alb_latency
# aws_cloudwatch_composite_alarm.main
# aws_cloudwatch_dashboard.main
# aws_sns_topic.alerts
# aws_sns_topic_subscription.email
# aws_cloudwatch_log_group.app

# 3.2 Inspect alarm thresholds
terraform state show aws_cloudwatch_metric_alarm.cpu_high
# Shows: threshold=80, comparison_operator=GreaterThanThreshold, period=300

# 3.3 Confirm dashboard URL output
terraform output dashboard_url
# Expected: https://console.aws.amazon.com/cloudwatch/home#dashboards:name=handson-overview

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Alarm Trigger Test

```bash
# Generate traffic to populate metrics
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"
for i in {1..50}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/items  > /dev/null
done

# Verify metrics are flowing into CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=handson-flask-api-service \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average \
  --query "Datapoints[*].{Time:Timestamp,CPU:Average}"
# Expected: datapoints returned (metrics flowing)
```

---

## 5. Expected Successful Outputs

**CLI — describe-alarms:**
```json
[
  { "Name": "handson-ecs-cpu-high",    "State": "OK", "Metric": "CPUUtilization" },
  { "Name": "handson-ecs-memory-high", "State": "OK", "Metric": "MemoryUtilization" },
  { "Name": "handson-5xx-errors",      "State": "OK", "Metric": "HTTPCode_Target_5XX_Count" },
  { "Name": "handson-alb-latency",     "State": "OK", "Metric": "TargetResponseTime" }
]
```

**terraform output:**
```
dashboard_url = "https://console.aws.amazon.com/cloudwatch/home#dashboards:name=handson-overview"
sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:handson-alerts"
```

**Log Insights query result:**
```
[
  [{ "field": "@timestamp", "value": "2024-01-01 12:00:00.000" },
   { "field": "@message",   "value": "GET /health 200" }]
]
```

---

## 6. Verification Checklist

- [ ] SNS topic `handson-alerts` exists
- [ ] SNS email subscription confirmed (not pending)
- [ ] All CloudWatch alarms created (CPU, memory, 5xx, latency, composite)
- [ ] Dashboard `handson-overview` exists with 4 widgets
- [ ] Log group `/ecs/handson-flask-api` with 30-day retention
- [ ] Alarm manual trigger → email notification received
- [ ] Alarm resets to OK after manual reset
- [ ] Log Insights query returns results
- [ ] CloudWatch metrics datapoints flowing (traffic generated)
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows all alarm + dashboard resources
