# Project 8.5 — CloudTrail + SIEM Integration

## What This Does
Enables CloudTrail for full API audit logging and integrates it with a SIEM (Security Information and Event Management) system for incident investigation and threat hunting.

## What CloudTrail Records
- Every API call made in your account (who, what, when, from where)
- Console logins and failures
- IAM changes (user creation, policy changes)
- Resource creation and deletion
- Data events (S3 object access, Lambda invocations)

## SIEM Integration Options
| Option | Cost | Complexity |
|--------|------|-----------|
| CloudWatch Logs Insights | Low | Low |
| Athena (Project 7.4) | Very low | Medium |
| OpenSearch/Kibana (Project 7.2) | Medium | Medium |
| Splunk | High | High |
| Datadog | High | Low |

## Key Investigation Queries
- Who deleted this resource?
- What did this IAM user do in the last 24 hours?
- Which IPs accessed our S3 bucket?
- Were there any failed login attempts?
- What changed before the outage?

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- CloudTrail management events: free for first trail, $2/100K for additional
- Data events (S3, Lambda): $0.10 per 100K events — enable selectively
- CloudTrail Insights: detects unusual API activity automatically
- Log file integrity validation: SHA-256 hash proves logs weren't tampered with
- Multi-region trail: captures events from all regions in one place

## Code

### `code/cloudtrail_analyzer.py` — Analyze CloudTrail logs for suspicious activity

```bash
pip install boto3

# Analyze last 7 days of CloudTrail logs
python code/cloudtrail_analyzer.py --bucket my-cloudtrail-bucket --days 7

# Analyze last 30 days
python code/cloudtrail_analyzer.py --bucket my-cloudtrail-bucket --days 30

# Use a specific region and profile
python code/cloudtrail_analyzer.py \
  --bucket my-cloudtrail-bucket \
  --days 7 \
  --region us-east-1 \
  --profile security
```

Detects:
| Event | Severity |
|-------|----------|
| Root account API calls | CRITICAL |
| Failed console logins | HIGH |
| IAM policy changes | HIGH |
| Security group modifications | MEDIUM |
| API calls from unusual regions | MEDIUM |
| S3 bucket policy changes | MEDIUM |

Prints events sorted by severity with timestamps and source IPs.
