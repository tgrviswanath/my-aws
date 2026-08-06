# Project 8.5 — CloudTrail SIEM with Athena
## API Audit Trail → S3 → Athena Queries for Security Investigation

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `cloudtrail:*`, `s3:*`, `athena:*`, `glue:*`, `logs:*`
- [ ] Region: `us-east-1`
- [ ] S3 bucket for CloudTrail logs (separate from Config bucket)
- [ ] Athena result bucket
- [ ] jq installed: `jq --version`

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
TRAIL_BUCKET="cloudtrail-logs-${ACCOUNT_ID}"
ATHENA_BUCKET="athena-results-${ACCOUNT_ID}"
```

---

## Decision Point 1

**CloudTrail vs CloudWatch Logs — what's the difference?**

| Service | What It Captures | Best For | Retention |
|---------|-----------------|----------|-----------|
| **CloudTrail** ✅ | All AWS API calls (who did what, when) | Security audit, incident investigation | S3: indefinite |
| **CloudWatch Logs** | Application logs, OS metrics, custom events | App debugging, performance, alerting | 1 day – 10 years |
| **VPC Flow Logs** | Network traffic (IP, port, protocol) | Network security, connectivity debug | CloudWatch or S3 |

**CloudTrail captures:**
- Every API call to AWS services
- Management console logins
- IAM changes, S3 bucket policy changes
- EC2 start/stop/terminate
- Who, what resource, when, from where

**CloudWatch Logs captures:**
- Your application's stdout/stderr
- EC2 instance system logs
- Custom application metrics

**Verdict:** Both are complementary. CloudTrail for API audit, CloudWatch for app logs.

---

## 1. Architecture Overview

```
AWS API Calls (Console, CLI, SDK)
        │
        ▼
  CloudTrail Trail
        │
        ▼
   S3 Bucket (cloudtrail-logs-ACCOUNT)
   └── AWSLogs/ACCOUNT/CloudTrail/REGION/YEAR/MONTH/DAY/
        └── ACCOUNT_CloudTrail_REGION_TIMESTAMP.json.gz
        │
        ▼
   AWS Glue Data Catalog
   └── Table: cloudtrail_logs
        │
        ▼
   Amazon Athena (SQL queries)
   ├── "Who deleted S3 bucket?"
   ├── "All console logins today"
   ├── "IAM policy changes last 7 days"
   └── "Failed API calls by user"
```

---

## 2. Create S3 Buckets

```bash
# Trail bucket
aws s3 mb s3://${TRAIL_BUCKET} --region $REGION

# Block public access on trail bucket
aws s3api put-public-access-block \
  --bucket $TRAIL_BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Bucket policy for CloudTrail
cat > /tmp/cloudtrail-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::${TRAIL_BUCKET}",
      "Condition": {"StringEquals": {"AWS:SourceAccount": "$ACCOUNT_ID"}}
    },
    {
      "Sid": "AWSCloudTrailWrite",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${TRAIL_BUCKET}/AWSLogs/${ACCOUNT_ID}/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-acl": "bucket-owner-full-control",
          "AWS:SourceAccount": "$ACCOUNT_ID"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket $TRAIL_BUCKET \
  --policy file:///tmp/cloudtrail-bucket-policy.json

# Athena results bucket
aws s3 mb s3://${ATHENA_BUCKET} --region $REGION
```

---

## 3. Create CloudTrail Trail

```bash
# Create trail (first trail per region is free)
TRAIL_ARN=$(aws cloudtrail create-trail \
  --name "myapp-audit-trail" \
  --s3-bucket-name $TRAIL_BUCKET \
  --include-global-service-events \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --tags-list '[{"Key":"Project","Value":"siem"},{"Key":"Environment","Value":"production"}]' \
  --query 'TrailARN' \
  --output text)

echo "Trail ARN: $TRAIL_ARN"

# Start logging
aws cloudtrail start-logging --name "myapp-audit-trail"

# Enable data events for S3 (optional — additional cost)
aws cloudtrail put-event-selectors \
  --trail-name "myapp-audit-trail" \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": []
    }
  ]'

# Verify trail is active
aws cloudtrail get-trail-status \
  --name "myapp-audit-trail" \
  --query '{IsLogging:IsLogging,LatestDeliveryTime:LatestDeliveryTime}'
```

---

## 4. Set Up CloudWatch Logs Integration (Optional)

```bash
# Create CloudWatch log group for real-time CloudTrail events
aws logs create-log-group \
  --log-group-name "/aws/cloudtrail/myapp-audit" \
  --retention-in-days 90

# Update trail to send to CloudWatch Logs
CW_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/CloudTrailCloudWatchLogsRole"

aws cloudtrail update-trail \
  --name "myapp-audit-trail" \
  --cloud-watch-logs-log-group-arn \
    "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/cloudtrail/myapp-audit:*" \
  --cloud-watch-logs-role-arn "$CW_ROLE_ARN"
```

---

## 5A. Console: Create Trail with Athena Integration

1. Navigate to **CloudTrail** → **Create trail**
2. **Trail name**: `myapp-audit-trail`
3. **Storage location**: New S3 bucket (auto-creates with policy)
4. **Log file SSE-KMS encryption**: Optional (enable for production)
5. **Log file validation**: ✅ Enable
6. **CloudWatch Logs**: ✅ Enable (for real-time alerting)
7. **Events**:
   - ✅ Management events (Read + Write)
   - Data events: S3, Lambda (optional, adds cost)
8. Click **Create trail**

**Enable Athena integration:**
1. Open your trail → **Event history** tab
2. Click **Create Athena table** (or use **Run query in Athena**)
3. Athena table created automatically with correct schema

---

## 5B. CLI: Create Athena Table for CloudTrail

```bash
# Set Athena workgroup and output
aws athena create-work-group \
  --name "cloudtrail-siem" \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://'"$ATHENA_BUCKET"'/results/"
    }
  }'

# Create Athena database
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS cloudtrail_db" \
  --work-group "cloudtrail-siem" \
  --query-execution-context 'Database=default'

# Create Athena table for CloudTrail logs
QUERY=$(cat << SQLEOF
CREATE EXTERNAL TABLE IF NOT EXISTS cloudtrail_db.cloudtrail_logs (
  eventVersion STRING,
  userIdentity STRUCT<
    type: STRING,
    principalId: STRING,
    arn: STRING,
    accountId: STRING,
    userName: STRING,
    sessionContext: STRUCT<
      sessionIssuer: STRUCT<
        type: STRING,
        principalId: STRING,
        arn: STRING,
        accountId: STRING,
        userName: STRING
      >
    >
  >,
  eventTime STRING,
  eventSource STRING,
  eventName STRING,
  awsRegion STRING,
  sourceIPAddress STRING,
  userAgent STRING,
  errorCode STRING,
  errorMessage STRING,
  requestParameters STRING,
  responseElements STRING,
  requestId STRING,
  eventId STRING,
  resources ARRAY<STRUCT<ARN: STRING, accountId: STRING, type: STRING>>,
  eventType STRING,
  apiVersion STRING,
  readOnly STRING,
  recipientAccountId STRING,
  serviceEventDetails STRING,
  sharedEventId STRING,
  vpcEndpointId STRING
)
ROW FORMAT SERDE 'com.amazon.emr.hive.serde.CloudTrailSerde'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://${TRAIL_BUCKET}/AWSLogs/${ACCOUNT_ID}/CloudTrail/'
SQLEOF
)

QUERY_ID=$(aws athena start-query-execution \
  --query-string "$QUERY" \
  --work-group "cloudtrail-siem" \
  --query-execution-context 'Database=cloudtrail_db' \
  --query 'QueryExecutionId' \
  --output text)

echo "Creating Athena table. Query ID: $QUERY_ID"
sleep 5
aws athena get-query-execution --query-execution-id $QUERY_ID \
  --query 'QueryExecution.Status.State'
```

---

## 6. Run Security Investigation Queries

```bash
run_athena_query() {
  local QUERY="$1"
  local QUERY_ID=$(aws athena start-query-execution \
    --query-string "$QUERY" \
    --work-group "cloudtrail-siem" \
    --query-execution-context 'Database=cloudtrail_db' \
    --query 'QueryExecutionId' \
    --output text)
  
  # Wait for completion
  while true; do
    STATUS=$(aws athena get-query-execution \
      --query-execution-id $QUERY_ID \
      --query 'QueryExecution.Status.State' --output text)
    [ "$STATUS" = "SUCCEEDED" ] && break
    [ "$STATUS" = "FAILED" ] && echo "Query failed" && return 1
    sleep 2
  done
  
  aws athena get-query-results \
    --query-execution-id $QUERY_ID \
    --query 'ResultSet.Rows[*].Data[*].VarCharValue'
}

# Query 1: Who deleted an S3 bucket?
run_athena_query "
SELECT eventtime, useridentity.username, useridentity.arn, 
       sourceipaddress, requestparameters
FROM cloudtrail_db.cloudtrail_logs
WHERE eventsource = 's3.amazonaws.com'
  AND eventname = 'DeleteBucket'
  AND eventtime > '2024-01-01'
ORDER BY eventtime DESC
LIMIT 20;"

# Query 2: All console logins today
run_athena_query "
SELECT eventtime, useridentity.username, sourceipaddress, 
       useragent, errorcode
FROM cloudtrail_db.cloudtrail_logs
WHERE eventname = 'ConsoleLogin'
  AND eventtime >= date_format(current_date, '%Y-%m-%dT00:00:00Z')
ORDER BY eventtime DESC;"

# Query 3: IAM changes last 7 days
run_athena_query "
SELECT eventtime, eventname, useridentity.username,
       useridentity.arn, sourceipaddress
FROM cloudtrail_db.cloudtrail_logs
WHERE eventsource = 'iam.amazonaws.com'
  AND eventname IN ('CreateUser','DeleteUser','AttachUserPolicy',
                    'DetachUserPolicy','CreateAccessKey','DeleteAccessKey',
                    'UpdateLoginProfile','CreateRole')
  AND eventtime >= date_format(date_add('day', -7, current_date), '%Y-%m-%dT00:00:00Z')
ORDER BY eventtime DESC
LIMIT 50;"

# Query 4: Failed API calls (access denied, unauthorized)
run_athena_query "
SELECT eventtime, eventname, eventsource, useridentity.username,
       useridentity.arn, errorcode, errormessage, sourceipaddress
FROM cloudtrail_db.cloudtrail_logs
WHERE errorcode IN ('AccessDenied', 'UnauthorizedAccess', 
                    'Client.UnauthorizedOperation')
  AND eventtime > '2024-01-01'
ORDER BY eventtime DESC
LIMIT 50;"

# Query 5: Root account activity
run_athena_query "
SELECT eventtime, eventname, eventsource, 
       sourceipaddress, useragent
FROM cloudtrail_db.cloudtrail_logs
WHERE useridentity.type = 'Root'
  AND eventname != 'ConsoleLogin'
ORDER BY eventtime DESC
LIMIT 20;"
```

---

## 7. Create CloudWatch Alarms for Real-Time Alerting

```bash
# Create metric filter for root login
aws logs put-metric-filter \
  --log-group-name "/aws/cloudtrail/myapp-audit" \
  --filter-name "RootAccountLogin" \
  --filter-pattern '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }' \
  --metric-transformations \
    metricName=RootAccountLogins,metricNamespace=CloudTrailMetrics,metricValue=1

# Create alarm on root login
aws cloudwatch put-metric-alarm \
  --alarm-name "CloudTrail-RootLogin" \
  --alarm-description "Root account login detected" \
  --metric-name RootAccountLogins \
  --namespace CloudTrailMetrics \
  --statistic Sum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:${REGION}:${ACCOUNT_ID}:security-alerts"

# IAM policy change alarm
aws logs put-metric-filter \
  --log-group-name "/aws/cloudtrail/myapp-audit" \
  --filter-name "IAMPolicyChange" \
  --filter-pattern '{($.eventName=DeleteGroupPolicy)||($.eventName=DeleteRolePolicy)||($.eventName=DeleteUserPolicy)||($.eventName=PutGroupPolicy)||($.eventName=PutRolePolicy)||($.eventName=PutUserPolicy)||($.eventName=CreatePolicy)||($.eventName=DeletePolicy)||($.eventName=AttachRolePolicy)}' \
  --metric-transformations \
    metricName=IAMPolicyChanges,metricNamespace=CloudTrailMetrics,metricValue=1
```

---

## 8. Enable Athena Partitioning (Cost Optimization)

```bash
# Add partition for specific date (avoids full table scan)
aws athena start-query-execution \
  --query-string "
    ALTER TABLE cloudtrail_db.cloudtrail_logs
    ADD PARTITION (region='${REGION}', year='2024', month='01', day='15')
    LOCATION 's3://${TRAIL_BUCKET}/AWSLogs/${ACCOUNT_ID}/CloudTrail/${REGION}/2024/01/15/'" \
  --work-group "cloudtrail-siem"

# Query with partition filter (much cheaper — scans less data)
run_athena_query "
SELECT eventtime, eventname, useridentity.username
FROM cloudtrail_db.cloudtrail_logs
WHERE region = 'us-east-1'
  AND year = '2024' AND month = '01' AND day = '15'
  AND eventname = 'DeleteBucket';"
```

---

## 9. Automate with AWS Glue Crawler (Auto-Partition)

```bash
# Create Glue Crawler to auto-discover partitions
aws glue create-crawler \
  --name "cloudtrail-partition-crawler" \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/GlueServiceRole" \
  --database-name "cloudtrail_db" \
  --targets '{
    "S3Targets": [{"Path": "s3://'"$TRAIL_BUCKET"'/AWSLogs/'"$ACCOUNT_ID"'/CloudTrail/"}]
  }' \
  --schedule '{"ScheduleExpression": "cron(0 1 * * ? *)"}' \
  --description "Daily partition discovery for CloudTrail logs"

# Run crawler now
aws glue start-crawler --name "cloudtrail-partition-crawler"
```

---

## 10. Verify Complete Setup

```bash
echo "=== CloudTrail SIEM Verification ==="

# 1. Trail is logging
aws cloudtrail get-trail-status --name "myapp-audit-trail" \
  --query '{IsLogging:IsLogging,LatestDelivery:LatestDeliveryTime}'

# 2. Logs in S3
aws s3 ls s3://${TRAIL_BUCKET}/AWSLogs/${ACCOUNT_ID}/CloudTrail/ --recursive \
  | head -5

# 3. Athena table exists
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name cloudtrail_db \
  --query 'TableMetadataList[].Name'

# 4. Sample query works
run_athena_query "SELECT COUNT(*) FROM cloudtrail_db.cloudtrail_logs LIMIT 1;"

echo "=== SIEM Setup Complete ==="
```

---

## Troubleshooting

**Trail not delivering to S3:**
```bash
# Check delivery status
aws cloudtrail get-trail-status --name "myapp-audit-trail" \
  --query '{LatestDeliveryError:LatestDeliveryError}'
# Common fix: bucket policy missing Config Service principal
```

**Athena query fails with "table not found":**
```bash
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name cloudtrail_db
# If empty, re-run CREATE TABLE query in Section 5B
```

**Athena scans too much data (high cost):**
```bash
# Always filter by partition columns: region, year, month, day
# Add WHERE year='2024' AND month='01' to every query
```

---

## Expected Outcome

- ✅ CloudTrail trail active, delivering to S3
- ✅ Multi-region trail captures global API activity
- ✅ Athena table set up with CloudTrail schema
- ✅ Security queries running: S3 deletes, IAM changes, console logins
- ✅ CloudWatch metric filters alerting on root login, IAM changes
- ✅ Log file validation enabled (detect tampering)

---

## Cleanup

```bash
# Stop logging (first trail free, but stop to be safe)
aws cloudtrail stop-logging --name "myapp-audit-trail"
aws cloudtrail delete-trail --name "myapp-audit-trail"

# Delete Athena resources
aws athena delete-work-group \
  --work-group "cloudtrail-siem" \
  --recursive-delete-option

# Delete Glue database
aws glue delete-database --name "cloudtrail_db"

# Empty and delete S3 buckets
aws s3 rm s3://${TRAIL_BUCKET} --recursive
aws s3 rb s3://${TRAIL_BUCKET}
aws s3 rm s3://${ATHENA_BUCKET} --recursive
aws s3 rb s3://${ATHENA_BUCKET}

# Delete CloudWatch log group and alarms
aws logs delete-log-group --log-group-name "/aws/cloudtrail/myapp-audit"
aws cloudwatch delete-alarms --alarm-names "CloudTrail-RootLogin"

echo "Cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
