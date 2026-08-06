# Project 8.5 — CloudTrail SIEM: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] IAM permissions: `cloudtrail:*`, `s3:CreateBucket`, `athena:*`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] S3 bucket names planned (must be globally unique)
- [ ] Note: First trail per region is free; Athena charges $5/TB scanned

---

## Step 1 — Navigate to CloudTrail

1. Sign in to the **AWS Management Console**
2. Search for **CloudTrail** in the search bar
3. Click **AWS CloudTrail**
4. You see the **Dashboard** showing recent events and active trails
5. **Event history** tab shows last 90 days of management events (always free, no trail needed)

📸 Screenshot: CloudTrail dashboard with Event history tab and trails list

---

## Step 2 — Create a Trail

1. Click **Trails** in left nav
2. Click **Create trail**
3. **Step 1 — Choose trail attributes:**
   - **Trail name**: `myapp-audit-trail`
   - **Storage location**: Create new S3 bucket
     - Bucket name: `cloudtrail-logs-[your-account-id]` (auto-suggested)
   - **Log file SSE-KMS encryption**: Optional (enable with CMK for production)
   - ✅ **Log file validation**: Enable (detects if logs are tampered)
   - **CloudWatch Logs**: ✅ Enable for real-time alerting
     - Log group: `/aws/cloudtrail/myapp-audit`
     - Create new IAM role: `CloudTrailRole` (auto-created)
   - **Tags**: Key=`Project` Value=`siem`
4. Click **Next**

📸 Screenshot: Trail creation form with S3 bucket and CloudWatch Logs settings

---

## Step 3 — Configure Events to Log

1. **Step 2 — Choose log events:**
2. **Management events:**
   - ✅ **Read** events (describe, list, get actions)
   - ✅ **Write** events (create, delete, modify actions — most important)
   - ✅ **Exclude AWS KMS events** (reduces noise) — optional
3. **Data events** (optional — additional cost):
   - S3 Object-level: Enable to track individual file reads/writes
   - Lambda: Enable to track function invocations
   - Leave unchecked for this exercise
4. **Insights events** (optional):
   - Enable to detect unusual API activity patterns
5. Click **Next** → Review → **Create trail**

📸 Screenshot: Event type selection with Management events checked

**Decision Point: Enable S3 data events?**
- Enabled: See exactly which files were read/deleted in S3 (~$0.10/100K events)
- Disabled: Only management events (bucket creation/deletion) recorded — free

---

## Step 4 — View Event History

1. Navigate to **Event history** in left nav
2. You see last 90 days of management events (no trail required)
3. Filter options:
   - **Event name**: e.g., `DeleteBucket`
   - **User name**: Find all actions by a specific user
   - **Resource type**: Filter to EC2, S3, IAM, etc.
   - **Resource name**: Specific resource ID
4. Click any event to see full JSON detail
5. Download event history as CSV for reporting

📸 Screenshot: Event history table with filter dropdowns and event rows

---

## Step 5 — Enable Athena Integration

1. Navigate to your trail in **Trails** → click trail name
2. In the **General details** section, find **Athena**
3. Click **Configure** or find the S3 bucket link
4. Navigate to **S3** → your trail bucket → click **Query with S3 Select** or:

**Recommended: Use Athena directly**
1. Navigate to **Amazon Athena**
2. In the left nav, click **Query editor**
3. Set **Data source**: `AwsDataCatalog`
4. Set **Database**: Create new `cloudtrail_db`
5. Run the CREATE EXTERNAL TABLE statement from the GUIDE.md

📸 Screenshot: Athena query editor with cloudtrail_db selected and table creation query

---

## Step 6 — Run Athena Security Queries

1. In **Athena Query editor**
2. Select database: `cloudtrail_db`
3. Run: **Who deleted an S3 bucket?**
```sql
SELECT eventtime, useridentity.username, useridentity.arn,
       sourceipaddress, requestparameters
FROM cloudtrail_logs
WHERE eventsource = 's3.amazonaws.com'
  AND eventname = 'DeleteBucket'
ORDER BY eventtime DESC
LIMIT 20;
```
4. Click **Run** — results appear below
5. Download results as CSV

📸 Screenshot: Athena query results showing S3 DeleteBucket events with usernames

**Troubleshooting — No results:**
- CloudTrail might not have data yet (wait 15 minutes for first delivery)
- Verify S3 path in LOCATION matches your actual bucket structure
- Use `SELECT * FROM cloudtrail_logs LIMIT 5` to verify table works

---

## Step 7 — View Trail in CloudWatch Logs

1. Navigate to **CloudWatch** → **Logs** → **Log groups**
2. Find `/aws/cloudtrail/myapp-audit`
3. Click on a log stream (format: `ACCOUNT_CloudTrail_REGION`)
4. See real-time JSON events as they arrive
5. Use **Filter events** to search: `{ $.eventName = "ConsoleLogin" }`

📸 Screenshot: CloudWatch Logs showing CloudTrail JSON events in real time

---

## Step 8 — Create Metric Filter for Root Login Alert

1. In CloudWatch → **Log groups** → `/aws/cloudtrail/myapp-audit`
2. Click **Metric filters** tab
3. Click **Create metric filter**
4. **Filter pattern**:
```
{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }
```
5. Click **Test pattern** — verify it matches root events
6. Click **Next**:
   - **Filter name**: `RootAccountLogin`
   - **Metric namespace**: `CloudTrailMetrics`
   - **Metric name**: `RootAccountLogins`
   - **Metric value**: `1`
7. Click **Create metric filter**
8. Create alarm: click **Create alarm** on the filter → set threshold = 1

📸 Screenshot: Metric filter creation with root login pattern and CloudWatch metric config

---

## Step 9 — Explore Trail Insights

1. Go to your trail → click **Insights** tab
2. If enabled, see anomaly detection results:
   - Unusual spikes in API call volume
   - Unusual patterns for specific API
3. **Insights event** shows time period and % deviation from baseline

📸 Screenshot: Trail Insights tab showing API activity baseline and anomalies

---

## Step 10 — Validate Log File Integrity

1. Download a CloudTrail digest file from S3:
   - Navigate to your trail S3 bucket
   - Path: `AWSLogs/ACCOUNT/CloudTrail-Digest/REGION/YEAR/MONTH/DAY/`
   - Download the `.json.gz` digest file
2. Use AWS CLI to validate:
```bash
aws cloudtrail validate-logs \
  --trail-arn "arn:aws:cloudtrail:us-east-1:ACCOUNT:trail/myapp-audit-trail" \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-02T00:00:00Z"
```
3. Output: `Logs from X to Y are valid` — confirms no tampering

📸 Screenshot: CloudTrail digest validation showing valid log chain

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Trail not in list | Wrong region | CloudTrail is regional — check region |
| No S3 logs after 15 min | Bucket policy missing | Re-add S3 bucket policy for CloudTrail |
| Athena table scans too much | No partition filter | Add `WHERE year='2024' AND month='01'` |
| CloudWatch Logs not receiving | Role permission | Ensure CloudTrailRole has `logs:PutLogEvents` |
| Event history only shows 90 days | By design | Full history requires trail + S3 + Athena |

---

## Console Navigation Quick Reference

```
AWS CloudTrail
├── Dashboard          → Recent activity + active trails
├── Event history      → Last 90 days (no trail needed)
├── Trails             → Configure + manage trails
│   └── [Trail Name]
│       ├── Logging status
│       ├── S3 bucket link
│       ├── CloudWatch Logs link
│       └── Insights tab
├── Lake               → CloudTrail Lake (alternative to Athena)
└── Settings           → Organization trail config

Amazon Athena (separate service)
├── Query editor       → Run SQL queries
├── Saved queries      → Store reusable security queries
└── Query history      → Review past queries + costs
```
