# Verification & Validation — Project 8.5 CloudTrail + SIEM Integration

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| CloudTrail Trail | CloudTrail → Trails | `handson-trail` listed, Logging = **ON** |
| Multi-region | Trail details | Multi-region trail = **Yes** |
| Log file validation | Trail details | Log file validation = **Enabled** |
| S3 Bucket | S3 → Buckets | `handson-cloudtrail-*` bucket exists with log files |
| CloudWatch Logs | CloudWatch → Log Groups | `/aws/cloudtrail/handson` log group exists |
| CloudTrail Insights | Trail → Insights | Insights enabled (API call rate + error rate) |
| SNS Notification | Trail → SNS notification | SNS topic configured |

📸 Screenshot: CloudTrail trail showing Logging=ON, multi-region, validation enabled  
📸 Screenshot: S3 bucket with CloudTrail log files (AWSLogs/ prefix)  
📸 Screenshot: cloudtrail_analyzer.py output showing suspicious events

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm trail exists and is logging
aws cloudtrail describe-trails \
  --query "trailList[?Name=='handson-trail'].{Name:Name,S3Bucket:S3BucketName,MultiRegion:IsMultiRegionTrail,Validation:LogFileValidationEnabled}"
# Expected: MultiRegion=true, Validation=true

aws cloudtrail get-trail-status \
  --name handson-trail \
  --query "{IsLogging:IsLogging,LatestDelivery:LatestDeliveryTime,LatestDigest:LatestDigestDeliveryTime}"
# Expected: IsLogging=true, LatestDelivery populated

# 2.2 Confirm log files exist in S3
BUCKET=$(aws cloudtrail describe-trails \
  --query "trailList[?Name=='handson-trail'].S3BucketName" --output text)
aws s3 ls s3://$BUCKET/AWSLogs/ --recursive | head -5
# Expected: log files listed

# 2.3 Verify log file integrity
aws cloudtrail validate-logs \
  --trail-arn $(aws cloudtrail describe-trails \
    --query "trailList[?Name=='handson-trail'].TrailARN" --output text) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)
# Expected: "Files validated: N, Files invalid: 0"

# 2.4 Look up recent events (last 10 minutes)
aws cloudtrail lookup-events \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 5 \
  --query "Events[*].{Time:EventTime,User:Username,Event:EventName,Source:EventSource}"
# Expected: recent API calls listed

# 2.5 Search for specific event type (IAM changes)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateUser \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --query "Events[*].{Time:EventTime,User:Username,Event:EventName}"
# Expected: any IAM CreateUser events in last 24h

# 2.6 Check CloudWatch Logs integration
aws logs describe-log-groups \
  --log-group-name-prefix /aws/cloudtrail \
  --query "logGroups[*].{Name:logGroupName,Retention:retentionInDays}"
# Expected: /aws/cloudtrail/handson listed

# 2.7 Run CloudTrail analyzer
python code/cloudtrail_analyzer.py --bucket $BUCKET --days 1
# Expected: events sorted by severity, suspicious activity flagged
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_cloudtrail.main
# aws_s3_bucket.cloudtrail
# aws_s3_bucket_policy.cloudtrail
# aws_cloudwatch_log_group.cloudtrail
# aws_iam_role.cloudtrail_cloudwatch
# aws_sns_topic.cloudtrail_alerts
# aws_cloudwatch_log_metric_filter.root_usage (if configured)
# aws_cloudwatch_metric_alarm.root_usage

# 3.2 Inspect trail
terraform state show aws_cloudtrail.main
# Shows: is_multi_region_trail=true, enable_log_file_validation=true, s3_bucket_name

# 3.3 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Incident Investigation Simulation

```bash
# Generate some API activity to analyze
aws s3 ls > /dev/null
aws ec2 describe-instances > /dev/null
aws iam list-users > /dev/null

# Wait for CloudTrail to deliver logs (~5 minutes)
sleep 60

# Look up your own recent activity
MY_USER=$(aws sts get-caller-identity --query "Arn" --output text)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=$(echo $MY_USER | cut -d'/' -f2) \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --query "Events[*].{Time:EventTime,Event:EventName,Source:EventSource}" \
  --output table
# Expected: your recent API calls listed (s3:ListBuckets, ec2:DescribeInstances, iam:ListUsers)
```

---

## 5. Expected Successful Outputs

**CLI — get-trail-status:**
```json
{ "IsLogging": true, "LatestDeliveryTime": "2024-01-01T12:00:00Z", "LatestDigestDeliveryTime": "2024-01-01T12:00:00Z" }
```

**CLI — lookup-events:**
```
| EventTime           | Username | EventName          | EventSource          |
|---------------------|----------|--------------------|----------------------|
| 2024-01-01 12:00:00 | admin    | DescribeInstances  | ec2.amazonaws.com    |
| 2024-01-01 12:00:01 | admin    | ListBuckets        | s3.amazonaws.com     |
```

**cloudtrail_analyzer.py output:**
```
=== CloudTrail Security Analysis (last 1 day) ===
CRITICAL: 0 root account API calls
HIGH:     0 failed console logins
HIGH:     0 IAM policy changes
MEDIUM:   2 security group modifications
INFO:     142 total API calls analyzed

No critical threats detected ✅
```

---

## 6. Verification Checklist

- [ ] Trail `handson-trail` IsLogging = true
- [ ] Multi-region trail = true
- [ ] Log file validation = enabled
- [ ] S3 bucket exists with AWSLogs/ prefix containing log files
- [ ] CloudWatch Logs integration active (log group exists)
- [ ] Log file integrity validation passes (0 invalid files)
- [ ] Recent API events visible via `lookup-events`
- [ ] CloudTrail Insights enabled
- [ ] SNS notification configured on trail
- [ ] `cloudtrail_analyzer.py` runs and prints severity-sorted events
- [ ] `terraform plan` shows no changes
