# Project 0.4 — Billing & Cost Management

**Stage:** 00 | **Level:** Beginner | **Est. Time:** 1 hour | **Cost:** $0

Configure AWS billing visibility before spending any money. Set a $10 monthly budget with an SNS email alert at 85% and 100% thresholds. Enable Cost Anomaly Detection so ML flags unusual spend automatically. Explore Cost Explorer's 12-month usage graph and the free tier dashboard to stay within free limits.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| AWS Budgets | Monthly $10 budget with email alert | Free: first 2 budgets/month |
| Cost Explorer | 12-month usage and cost visualisation | Free |
| SNS | Email notification delivery for budget alerts | Free for email (first 1,000 email/month) |
| CloudWatch | Billing metric alarms (`EstimatedCharges`) | Free tier: 10 alarms |
| Cost Anomaly Detection | ML-based unusual spend detection | Free (charges only on anomalies flagged) |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| AWS account | Root account or IAM user with billing console access enabled |
| Email address | SNS subscription target for budget alert emails |
| Budget threshold | $10/month total cost budget |
| Anomaly threshold | Alert if spend increases by $5 or 20% above baseline |

### Output
| Type | Description |
|------|-------------|
| AWS Budget | `MyMonthlyBudget` — $10/month, alerts at 85% ($8.50) and forecasted 100% |
| SNS subscription | Email confirmed, alert delivery tested |
| CloudWatch alarm | Triggers when `EstimatedCharges` > $5 in billing region `us-east-1` |
| Cost Anomaly Detector | Monitor on all AWS services, email alert on anomaly |
| Free tier dashboard | Shows % used for EC2 hours, S3 GB, Lambda invocations |

---

## Architecture

```
AWS Billing (us-east-1)
  │
  ├── Cost Explorer
  │     └── 12-month history, service breakdown, forecast
  │
  ├── AWS Budgets
  │     ├── Budget: $10/month
  │     ├── Alert 1: Actual spend ≥ 85% ($8.50) → SNS → email
  │     └── Alert 2: Forecasted spend ≥ 100% ($10.00) → SNS → email
  │
  ├── CloudWatch Alarm
  │     └── Metric: AWS/Billing EstimatedCharges > $5.00 → SNS → email
  │
  └── Cost Anomaly Detection
        └── Monitor: all services
              └── Threshold: $5 absolute or 20% relative anomaly → email alert
```

---

## Quick Start

```cmd
REM All billing actions require the billing console to be enabled for IAM users.
REM Root account: My Account → IAM user and role access to Billing → Activate

REM -- Create SNS topic for alerts --
aws sns create-topic --name billing-alerts --region us-east-1

REM -- Subscribe your email to the topic (replace EMAIL and TOPIC_ARN)
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:ACCOUNT:billing-alerts ^
    --protocol email --notification-endpoint your@email.com

REM -- Confirm the subscription link sent to your inbox before continuing --

REM -- Create a $10 monthly budget (saves to budget.json first) --
REM   See code/budget.json for the full JSON template
aws budgets create-budget --account-id ACCOUNT_ID ^
    --budget file://code/budget.json ^
    --notifications-with-subscribers file://code/budget_notifications.json

REM -- Create CloudWatch billing alarm (billing metrics are in us-east-1 only) --
aws cloudwatch put-metric-alarm ^
    --alarm-name "BillingOver5Dollars" ^
    --metric-name EstimatedCharges ^
    --namespace AWS/Billing ^
    --statistic Maximum ^
    --period 86400 ^
    --threshold 5.00 ^
    --comparison-operator GreaterThanThreshold ^
    --dimensions Name=Currency,Value=USD ^
    --evaluation-periods 1 ^
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:billing-alerts ^
    --region us-east-1

REM -- Enable Cost Anomaly Detection in Cost Explorer UI --
REM   Cost Management → Cost Anomaly Detection → Create monitor
```

---

## Data Flow

```
1. Billing data is aggregated daily — AWS updates EstimatedCharges metric once per day
2. CloudWatch evaluates the EstimatedCharges metric against the $5 threshold at the daily period
3. If threshold crossed, CloudWatch publishes to SNS topic → email delivered to subscriber
4. Budgets service evaluates actual vs budgeted spend and forecast separately:
     - Actual ≥ 85% fires the first alert immediately
     - Forecasted to reach 100% fires the second alert (can fire before month end)
5. Cost Anomaly Detection trains an ML baseline on your historical spend per service
6. When daily spend deviates from the expected range by $5 or 20%, an anomaly alert is sent
7. Cost Explorer reads the same underlying Cost and Usage Report (CUR) data — no additional config
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — billing setup overview |
| `GUIDE.md` | Full walkthrough for Budgets, CloudWatch, and Anomaly Detection |
| `steps.md` | CLI commands for budget and alarm creation |
| `steps_awsconsoleui.md` | Console UI walkthrough: Cost Explorer, Budgets, free tier dashboard |
| `verify.md` | Checklist: budget exists, SNS confirmed, alarm state OK |
| `cost_estimate.md` | Cost of the billing tools themselves ($0) |
| `code/` | `budget.json`, `budget_notifications.json` templates for CLI |
| `docs/` | Alert threshold explanation, free tier limits reference |
| `terraform/` | IaC for budget and SNS (reference only — not needed for this project) |

---

## Lessons Learned

- The AWS Billing console is only accessible by root by default — you must explicitly enable IAM user access under root account → My Account → IAM User and Role Access to Billing
- Cost Explorer has a 12-month lookback window with daily granularity — it takes ~24 hours after account creation before any data appears
- Budget alerts have two separate trigger types: **actual** (spend already happened) and **forecasted** (projected to exceed by month end) — setting both at 85% actual and 100% forecasted gives early warning
- SNS email subscriptions require the recipient to click a confirmation link before any alerts are delivered — a missing confirmation is the most common reason alerts never arrive
- Cost Anomaly Detection uses ML to build a per-service spend baseline — it does not fire alerts the first week as it needs data to train; budget alarms are the more reliable short-term fallback
- CloudWatch billing metrics only exist in `us-east-1` regardless of your working region — always add `--region us-east-1` when querying `AWS/Billing` metrics
- Free tier tracks 85+ individual limits (EC2 hours, S3 GB, Lambda invocations, etc.) — the Free Tier Usage Alerts under Billing Preferences sends an email when any limit hits 85%
