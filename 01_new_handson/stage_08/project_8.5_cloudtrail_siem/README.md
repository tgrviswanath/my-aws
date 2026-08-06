# Project 8.5 — CloudTrail Audit Logging & SIEM

**Stage:** 08 | **Level:** Intermediate | **Est. Time:** 90 min | **Cost:** ~$2/month (S3 storage + Athena queries)

Create a CloudTrail multi-region trail that writes every API call to an S3 bucket and simultaneously
streams events to CloudWatch Logs for real-time analysis. A metric filter on the log group detects
root account logins and triggers a CloudWatch Alarm. Athena queries the raw JSON trail files in S3
through a Glue table to support ad-hoc forensic analysis — who called what API, from which IP, and
when — across the full account history.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS CloudTrail | Multi-region trail recording all management API calls | Free (management events) |
| Amazon S3 | Long-term storage for trail JSON files and digest files | $0.023/GB/month |
| Amazon CloudWatch Logs | Real-time log stream; metric filter for root login detection | $0.50/GB ingested |
| Amazon CloudWatch Alarms | Fires alarm when root login metric exceeds 0 in 5-min window | $0.10/alarm/month |
| Amazon Athena | SQL queries on CloudTrail JSON stored in S3 | $5/TB scanned |
| AWS Glue | Data catalog table mapping Athena to S3 CloudTrail partition | Free (first million objects) |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| Trail name | management-trail | Multi-region, all management events |
| S3 bucket | cloudtrail-logs-123456789012 | Versioning + MFA delete recommended |
| CloudWatch log group | /aws/cloudtrail/management-trail | IAM role grants CloudTrail delivery |
| Metric filter pattern | `{ $.userIdentity.type = "Root" && $.eventType = "AwsConsoleSignIn" }` | Detects root console login |
| Alarm threshold | ≥1 in 5-minute period | Any root login triggers alarm |
| Athena database | cloudtrail_db | Glue catalog database |

### Output

| Artifact | Description |
|---|---|
| S3 trail files | JSON logs partitioned by account/region/year/month/day |
| Digest files | SHA-256 chain in S3 proving log integrity (one digest/hour) |
| CloudWatch metric | RootAccountLogins — increments on each root console sign-in event |
| CloudWatch Alarm | ROOT_LOGIN_DETECTED — state ALARM triggers SNS notification |
| Athena table | cloudtrail_db.cloudtrail_logs — queryable across full history |
| Sample Athena query | Top 10 IAM users by API call volume in the last 7 days |

---

## Architecture

```
Every AWS API Call
(Console, CLI, SDK, Service)
          |
          v
  +---------------+
  | AWS CloudTrail |  multi-region trail
  | management-    |
  | trail          |
  +---------------+
       |       |
       |       +----> Amazon CloudWatch Logs
       |              /aws/cloudtrail/management-trail
       |                      |
       |               Metric Filter
       |               "Root console login"
       |                      |
       |               CloudWatch Alarm
       |               ROOT_LOGIN_DETECTED
       |                      |
       |                  SNS email
       |
       v
  Amazon S3
  cloudtrail-logs-123456789012/
  AWSLogs/123456789012/CloudTrail/
  us-east-1/2025/01/15/
       |
       | (+ digest files every hour)
       v
  AWS Glue Table
  cloudtrail_db.cloudtrail_logs
       |
       v
  Amazon Athena
  SQL queries on raw JSON
```

---

## Quick Start

```cmd
REM 1. Create S3 bucket for trail storage and apply bucket policy
aws s3api create-bucket --bucket cloudtrail-logs-123456789012 --region us-east-1
aws s3api put-bucket-policy ^
  --bucket cloudtrail-logs-123456789012 --policy file://cloudtrail-s3-policy.json

REM 2. Create multi-region trail with CloudWatch Logs integration
aws cloudtrail create-trail ^
  --name management-trail ^
  --s3-bucket-name cloudtrail-logs-123456789012 ^
  --is-multi-region-trail --include-global-service-events ^
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail/management-trail:* ^
  --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/cloudtrail-cloudwatch-role
aws cloudtrail start-logging --name management-trail

REM 3. Create metric filter detecting root account logins
aws logs put-metric-filter ^
  --log-group-name /aws/cloudtrail/management-trail ^
  --filter-name RootAccountLogins ^
  --filter-pattern "{ $.userIdentity.type = \"Root\" && $.eventType = \"AwsConsoleSignIn\" }" ^
  --metric-transformations metricName=RootAccountLogins,metricNamespace=CloudTrailMetrics,metricValue=1

REM 4. Create alarm that fires on any root login
aws cloudwatch put-metric-alarm ^
  --alarm-name ROOT_LOGIN_DETECTED --metric-name RootAccountLogins ^
  --namespace CloudTrailMetrics --statistic Sum --period 300 ^
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold ^
  --evaluation-periods 1 ^
  --alarm-actions arn:aws:sns:us-east-1:123456789012:security-alerts

REM 5. Create Glue database and run sample Athena query
aws glue create-database --database-input Name=cloudtrail_db
aws athena start-query-execution ^
  --query-string "SELECT useridentity.arn, COUNT(*) as calls FROM cloudtrail_db.cloudtrail_logs GROUP BY useridentity.arn ORDER BY calls DESC LIMIT 10;" ^
  --work-group primary ^
  --result-configuration OutputLocation=s3://cloudtrail-logs-123456789012/athena-results/
```

---

## Data Flow

1. Any AWS API call (console, CLI, SDK, or service-to-service) is captured by CloudTrail automatically.
2. CloudTrail writes compressed JSON event files to S3 under `AWSLogs/{accountId}/CloudTrail/{region}/{year}/{month}/{day}/`.
3. Every hour CloudTrail writes a digest file with SHA-256 hashes of delivered log files, chained to the previous digest for tamper detection.
4. Simultaneously, CloudTrail streams the same events to the CloudWatch Logs log group in near real-time.
5. The metric filter scans each log event — when `userIdentity.type = "Root"` and `eventType = "AwsConsoleSignIn"` match, it increments `RootAccountLogins` by 1.
6. CloudWatch evaluates the alarm over a 5-minute period — if `Sum >= 1`, the alarm transitions to ALARM and publishes to the SNS topic.
7. For forensic analysis, Athena queries the S3 JSON files through the Glue table — partition projection on year/month/day limits scanned data to control the $5/TB query cost.

---

## Project Files

| File | Description |
|---|---|
| `cloudtrail-s3-policy.json` | S3 bucket policy required for CloudTrail to write log files |
| `cloudtrail-cloudwatch-role.json` | IAM role and trust policy granting CloudTrail CloudWatch Logs delivery |
| `create_glue_table.sql` | DDL to create cloudtrail_db.cloudtrail_logs with partition projection |
| `sample_queries.sql` | Athena queries: root API calls, failed auth events, IAM changes by date |
| `test_root_login_alarm.sh` | Steps to simulate a root login event and verify alarm state changes |
| `digest_verify.py` | Python script to validate the SHA-256 digest chain proving log integrity |

---

## Lessons Learned

- CloudTrail records every API call including service name, caller identity, source IP, timestamp, request parameters, and HTTP response code — it is the primary audit source for all AWS activity.
- The default 90-day Event History in the CloudTrail console is free but not exportable for long-term analysis; creating an S3 trail is required for Athena queries and retention beyond 90 days.
- Management events (IAM operations, S3 bucket-level operations) are free to record; data events (S3 object reads/writes, Lambda invocations) cost $0.10 per 100,000 events — enable them selectively.
- Athena queries CloudTrail JSON directly in S3 using a Glue catalog table — partition projection on `year`, `month`, `day` columns eliminates full-bucket scans and significantly reduces the $5/TB query cost.
- CloudTrail digest files use SHA-256 hashing chained across hourly files — `validate-logs` CLI command verifies the chain and proves no log files were deleted or modified.
- The metric filter pattern uses the CloudWatch filter syntax with JSON field selectors (`$.userIdentity.type`) — test patterns with `filter-log-events` before creating alarms to confirm matches work correctly.
- Multi-region trails capture events from all regions including global services (IAM, STS, CloudFront) in a single S3 prefix — simpler to manage than per-region trails.
