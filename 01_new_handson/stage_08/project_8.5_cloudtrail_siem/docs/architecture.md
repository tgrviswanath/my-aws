# Architecture — Project 8.5 CloudTrail + SIEM Integration

## CloudTrail Data Flow

```
Every AWS API call
    │
    │ CloudTrail records event
    ▼
S3 bucket: handson-cloudtrail-ACCOUNTID
    └── AWSLogs/ACCOUNTID/CloudTrail/us-east-1/YYYY/MM/DD/
          └── ACCOUNTID_CloudTrail_us-east-1_YYYYMMDDTHHMMSSZ_xxx.json.gz

CloudWatch Logs: /aws/cloudtrail/handson
    └── Real-time stream for alerting

Log file integrity validation:
    └── SHA-256 digest files prove logs weren't tampered with
```

## Alert Rules

```
EventBridge Rules:
    ├── Root account usage → SNS → Email (CRITICAL)
    ├── IAM policy changes → SNS → Email (HIGH)
    ├── Security group changes → SNS → Email (MEDIUM)
    └── S3 bucket deletions → SNS → Email (HIGH)
```

## Investigation Workflow

```
Incident reported: "Who deleted the production database?"
    │
    ▼
CloudTrail lookup-events
    --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteDBInstance
    │
    ▼
Found: admin-user deleted db-prod at 2024-01-15T14:32:00Z from IP 1.2.3.4
    │
    ▼
Cross-reference with:
    ├── CloudWatch Logs (what else did they do?)
    ├── VPC Flow Logs (where did they connect from?)
    └── GuardDuty (any threat findings for that user?)
```
