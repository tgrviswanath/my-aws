# Architecture — Project 8.3 AWS Config Compliance Automation

## How Config Works

```
Resource created/modified (EC2, S3, RDS, etc.)
    │
    │ Config records configuration change
    ▼
Config Configuration Recorder
    │
    ├── Stores snapshot in S3 bucket
    └── Evaluates against Config Rules
          │
          ├── COMPLIANT   → no action
          └── NON_COMPLIANT → EventBridge event
                                │
                                ▼
                          SNS → Email alert
```

## Rules Evaluation

```
Config Rule: s3-bucket-server-side-encryption-enabled

Trigger: Configuration change (S3 bucket created/modified)

Evaluation:
  Check: does bucket have SSE enabled?
  YES → COMPLIANT
  NO  → NON_COMPLIANT → alert

Config Rule: required-tags

Trigger: Configuration change + periodic (every 24h)

Evaluation:
  Check: does resource have Project, Environment, ManagedBy tags?
  YES → COMPLIANT
  NO  → NON_COMPLIANT → alert
```

## Compliance Dashboard

```
AWS Config Dashboard
    ├── Overall compliance: 85% (17/20 rules passing)
    ├── Non-compliant resources: 3
    │   ├── S3 bucket: my-old-bucket (no encryption)
    │   ├── EC2 instance: i-xxx (missing tags)
    │   └── RDS: db-old (publicly accessible)
    └── Configuration history: full audit trail
```
