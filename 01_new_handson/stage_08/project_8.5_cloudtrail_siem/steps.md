# Steps — Project 8.5 CloudTrail + SIEM Integration

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -var="alert_email=your@email.com" -auto-approve
terraform output
```

---

## Phase 2 — Verify CloudTrail is Recording

```bash
# Check trail status
aws cloudtrail get-trail-status --name handson-trail \
  --query "{IsLogging:IsLogging,LatestDeliveryTime:LatestDeliveryTime}"

# List recent events
aws cloudtrail lookup-events \
  --start-time $(date -d '1 hour ago' --iso-8601=seconds) \
  --max-results 10 \
  --query "Events[*].{Time:EventTime,Name:EventName,User:Username,Source:EventSource}"
```

---

## Phase 3 — Incident Investigation Queries

```bash
# Who deleted a resource?
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time $(date -d '24 hours ago' --iso-8601=seconds) \
  --query "Events[*].{Time:EventTime,User:Username,Resource:Resources[0].ResourceName}"

# What did a specific user do?
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=admin-yourname \
  --start-time $(date -d '24 hours ago' --iso-8601=seconds) \
  --query "Events[*].{Time:EventTime,Action:EventName,Source:EventSource}"

# Failed API calls (access denied)
aws cloudtrail lookup-events \
  --start-time $(date -d '1 hour ago' --iso-8601=seconds) \
  --query "Events[?contains(CloudTrailEvent, 'AccessDenied')].{Time:EventTime,Name:EventName,User:Username}"
```

---

## Phase 4 — Test Root Account Alert

```bash
# Log in to AWS Console as root user
# This triggers the EventBridge rule → SNS → email alert
# Check your email for the notification
```

---

## Phase 5 — Log File Integrity Validation

```bash
# Validate CloudTrail log files haven't been tampered with
aws cloudtrail validate-logs \
  --trail-arn $(terraform output -raw cloudtrail_arn) \
  --start-time $(date -d '24 hours ago' --iso-8601=seconds) \
  --verbose
# Expected: "Results requested for..."
# "No invalid log files found"
```

---

## Phase 6 — CloudWatch Logs Insights Query

```bash
# Query CloudTrail logs in CloudWatch
aws logs start-query \
  --log-group-name /aws/cloudtrail/handson \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, eventName, userIdentity.arn, sourceIPAddress
    | filter errorCode like /AccessDenied/
    | sort @timestamp desc
    | limit 20
  '
```

---

## Screenshots to Take
- [ ] CloudTrail trail active with multi-region enabled
- [ ] Log file integrity validation passing
- [ ] CloudTrail Insights showing unusual activity
- [ ] Root account usage alert email received
- [ ] IAM change alert triggered
- [ ] CloudWatch Logs Insights query results
