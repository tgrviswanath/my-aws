# AWS Billing Setup — GUIDE.md

> **Stage:** 00 — Foundational Setup  
> **Project:** 0.4 — AWS Billing, Budgets & Cost Management  
> **Cost:** ~$0.00 (first 2 budget actions free; $0.02/budget/day after)  
> **Time:** 30–45 minutes

---

## 1. Project Overview

### Title: AWS Billing Setup — Cost Visibility from Day One

**Problem Statement:**  
AWS bills can grow unexpectedly. A forgotten EC2 instance, an accidental NAT Gateway, or a runaway Lambda invocation loop can generate hundreds of dollars in charges before you notice. Even during learning, forgetting to delete a resource can cost real money. This project establishes cost visibility and alerting before you deploy any billable resources, so you are never surprised by your AWS bill.

**Objectives:**
- Understand the AWS Billing console layout
- Enable Cost Explorer for historical cost analysis
- Create a budget with a $5 alert threshold (catches even small charges)
- Set up a CloudWatch billing alarm as a secondary alert
- Apply cost allocation tags to future resources
- Understand free tier usage tracking

**What You Will Learn:**
- Navigating the AWS Billing and Cost Management console
- Difference between Budgets and CloudWatch billing alarms
- How to read Cost Explorer graphs
- Cost allocation tags for multi-project cost tracking
- Free tier limits and how to monitor them
- AWS CLI commands for programmatic cost queries

**Skill Level:** Beginner  
**AWS Services Used:** AWS Budgets, Cost Explorer, CloudWatch, SNS  
**Tools Required:** AWS Console, AWS CLI

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  AWS BILLING ARCHITECTURE                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            AWS Billing Console                        │   │
│  │                                                       │   │
│  │  Cost Explorer ──► Historical charts & forecasts      │   │
│  │  Free Tier     ──► Current month usage vs limits      │   │
│  │  Bills         ──► Line-item invoice breakdown        │   │
│  │  Cost Alloc.   ──► Tag-based cost grouping            │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            AWS Budgets                                │   │
│  │                                                       │   │
│  │  Budget: "Monthly $5 Alert"                           │   │
│  │  ├── Threshold: 80% ($4.00) → SNS → Email alert       │   │
│  │  └── Threshold: 100% ($5.00) → SNS → Email alert      │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Amazon SNS (Simple Notification Service)   │   │
│  │                                                       │   │
│  │  Topic: billing-alerts                                │   │
│  │  Subscription: your@email.com                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│             📧 Email Alert: "AWS Budget Exceeded"            │
└──────────────────────────────────────────────────────────────┘
```

**Additional monitoring path:**
```
CloudWatch → Billing Alarm → SNS → Email
(secondary alert, monitors estimated charges metric)
```

---

## 3. Prerequisites

### Account Requirements
| Requirement | Status |
|-------------|--------|
| AWS account created | Required |
| Email address for alerts | Required |
| IAM user or root access | Required (billing console needs special permission) |
| Completed Project 0.1 | Recommended (for CLI commands) |

### Enable Billing Access for IAM Users
By default, only the root account can see billing data. Enable IAM billing access:

1. Log in as **root user**
2. Top-right → Account → IAM user and role access to Billing information
3. Click **Edit** → Check "Activate IAM Access"
4. Click **Update**

> After this, IAM users with the `AdministratorAccess` policy can view billing.

### Billing Console Region
The Billing console is **global** — not region-specific. You access it from any region and it shows charges across all regions.

---

## 4. Project Folder Structure

```
project_0.4_billing/
├── GUIDE.md                        ← This file
├── steps_awsconsoleui.md           ← Console navigation walkthrough
├── cost_estimate.md                ← Meta cost breakdown (cost of billing tools)
├── scripts/
│   ├── create_budget.sh            ← AWS CLI script to create budget
│   ├── get_cost_report.sh          ← Query current month costs
│   └── list_free_tier_usage.sh     ← Check free tier consumption
└── templates/
    └── budget_template.json        ← JSON template for budget creation
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method — Billing Console Navigation

#### Prerequisites Check

Before starting:
- [ ] You are logged in to the AWS Console
- [ ] You have billing access (root user, or IAM billing access enabled)
- [ ] Your email address is accessible to confirm SNS subscription
- [ ] Region: billing is global (any region works)

---

#### Decision Point 1: Budget Alert vs CloudWatch Billing Alarm

| Feature | AWS Budgets | CloudWatch Billing Alarm |
|---------|-------------|--------------------------|
| ✅ **Recommended for cost control** | Yes | No |
| Alert on forecasted cost | Yes | No |
| Alert on actual cost | Yes | Yes |
| Monthly cost budget types | Cost, Usage, Reservation, Savings Plans | Estimated charges only |
| Free | First 2 actions/month free | $0.10/alarm/month (within free tier: 10 alarms free) |
| Granularity | Daily, monthly, quarterly, annual | Monthly only |
| Per-service budgets | Yes | No |

**✅ Use AWS Budgets for:** Cost alerting, forecasting, staying within limits.  
**Use CloudWatch for:** Usage metric alerts (CPU, request counts — not just cost).

> **Decision: Create an AWS Budget.** We'll also create a CloudWatch billing alarm as a backup.

---

#### Step 1 — Open the Billing Console

1. Log in to https://console.aws.amazon.com
2. Click your account name (top-right corner)
3. Click **Billing and Cost Management**
   - Alternatively: search "Billing" in the top search bar

   **📸 Screenshot:** Capture the Billing Dashboard showing the current month summary

4. You see the **Billing Dashboard** with:
   - Month-to-date charges (likely $0.00)
   - Service charges breakdown
   - Free tier usage

---

#### Step 2 — Enable Cost Explorer

5. In the left sidebar, click **Cost Explorer**
6. If this is your first visit, click **Enable Cost Explorer**
7. Wait 24 hours for historical data to populate (first-time activation delay)
8. Once enabled, you see:
   - Daily cost bar chart (last 6 months)
   - Service breakdown
   - Forecast for current month

   **📸 Screenshot:** Capture the Cost Explorer chart (even if showing $0.00)

---

#### Step 3 — Create a Budget with $5 Alert

9. In the left sidebar, click **Budgets**
10. Click **Create budget**
11. Choose budget type: **Cost budget** — Recommended
12. Click **Next**
13. Configure budget:
    - Budget name: `monthly-learning-budget`
    - Period: **Monthly**
    - Budget renewal type: **Recurring budget**
    - Start month: Current month
    - Budgeted amount: `5.00` (USD)
14. Click **Next** (skip filtering for now)
15. Configure alerts:
    - Click **Add alert threshold**
    - Alert threshold: `80` (%)
    - Trigger: **Actual**
    - Email recipients: `your-email@example.com`
16. Add a second alert:
    - Alert threshold: `100` (%)
    - Trigger: **Actual**
    - Email recipients: `your-email@example.com`
17. Click **Next** → Review → **Create budget**

    **📸 Screenshot:** Capture the budget creation confirmation page

**Expected Outcome:**
```
Budget created: monthly-learning-budget
Amount: $5.00
Alerts: 2 configured (80% and 100%)
Current spend: $0.00
```

---

#### Step 4 — Create a CloudWatch Billing Alarm (Secondary Alert)

18. Open CloudWatch console: https://console.aws.amazon.com/cloudwatch
19. **Important:** Switch region to **US East (N. Virginia) — us-east-1**
    - Billing metrics are only available in us-east-1
20. In left sidebar: click **Alarms** → **All alarms**
21. Click **Create alarm**
22. Click **Select metric** → **Billing** → **Total Estimated Charge**
23. Select `EstimatedCharges` (Currency: USD) → **Select metric**
24. Configure:
    - Statistic: **Maximum**
    - Period: **6 hours**
    - Threshold type: **Static**
    - Condition: **Greater than**
    - Threshold value: `5`
25. Click **Next**
26. Configure notification:
    - In alarm state → Create new SNS topic
    - Topic name: `billing-alerts`
    - Email endpoint: `your-email@example.com`
    - Click **Create topic**
27. Click **Next**
28. Alarm name: `billing-over-5-dollars`
29. Click **Next** → **Create alarm**

    **📸 Screenshot:** Capture the CloudWatch alarm in "OK" state (green)

30. Check your email and **confirm the SNS subscription** (click the confirmation link)

---

#### Step 5 — Check Free Tier Usage

31. Back in the Billing console, click **Free Tier** in the left sidebar
32. You see a table showing:
    - Service name
    - Usage limit (e.g., 750 hours EC2 t2.micro/month)
    - Current month usage
    - Forecasted usage

    **📸 Screenshot:** Capture the Free Tier dashboard

33. Enable free tier alerts:
    - Billing → Billing preferences
    - Check: **Receive AWS Free Tier Usage Alerts**
    - Enter your email
    - Save preferences

---

#### Step 6 — Enable Cost Allocation Tags

34. Billing console → **Cost allocation tags**
35. You'll see tag keys that exist in your account (likely empty for new accounts)
36. After you create your first AWS resources with tags, activate them here
37. For now, note the pattern — we'll use these tags:

| Tag Key | Example Value | Purpose |
|---------|--------------|---------|
| `Project` | `stage-00` | Track by project stage |
| `Owner` | `your-name` | Personal responsibility |
| `Environment` | `learning` | Dev/staging/prod separation |

---

### 5B. AWS CLI Method

#### Create a Budget via CLI

```bash
# First, get your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Create a basic cost budget with email alert
aws budgets create-budget \
    --account-id $ACCOUNT_ID \
    --budget '{
        "BudgetName": "monthly-learning-budget-cli",
        "BudgetLimit": {
            "Amount": "5",
            "Unit": "USD"
        },
        "TimeUnit": "MONTHLY",
        "BudgetType": "COST"
    }' \
    --notifications-with-subscribers '[
        {
            "Notification": {
                "NotificationType": "ACTUAL",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 80,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [
                {
                    "SubscriptionType": "EMAIL",
                    "Address": "your-email@example.com"
                }
            ]
        }
    ]'

echo "Budget created successfully"
```

#### List and Describe Budgets

```bash
# List all budgets
aws budgets describe-budgets \
    --account-id $ACCOUNT_ID \
    --output table

# Get details of a specific budget
aws budgets describe-budget \
    --account-id $ACCOUNT_ID \
    --budget-name "monthly-learning-budget-cli" \
    --output json
```

#### Query Current Month Cost with Cost Explorer

```bash
# Get current month costs (requires Cost Explorer enabled)
START_DATE=$(date +%Y-%m-01)
END_DATE=$(date +%Y-%m-%d)

aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --output table

# Get cost breakdown by service
aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --output table

# Get cost breakdown by tag (after you start tagging resources)
aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=TAG,Key=Project \
    --output table
```

#### Check Free Tier Usage via CLI

```bash
# List free tier usage (requires billing access)
aws freetier get-free-tier-usage \
    --output table 2>/dev/null || \
    echo "Free Tier API requires root access or Billing Console access"

# Alternative: Use Cost Explorer for free tier
aws ce get-cost-and-usage \
    --time-period Start=$START_DATE,End=$END_DATE \
    --granularity MONTHLY \
    --metrics UsageQuantity \
    --filter '{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit"]}}' \
    --output json
```

---

## 6. Code Deep Dive

### Budget JSON Template

```json
{
    "BudgetName": "monthly-learning-budget",
    "BudgetLimit": {
        "Amount": "5",
        "Unit": "USD"
    },
    "CostFilters": {},
    "CostTypes": {
        "IncludeTax": true,
        "IncludeSubscription": true,
        "UseBlended": false,
        "IncludeRefund": false,
        "IncludeCredit": false,
        "IncludeUpfront": true,
        "IncludeRecurring": true,
        "IncludeOtherSubscription": true,
        "IncludeSupport": true,
        "IncludeDiscount": true,
        "UseAmortized": false
    },
    "TimeUnit": "MONTHLY",
    "TimePeriod": {
        "Start": "2024-01-01T00:00:00Z",
        "End": "2087-06-15T00:00:00Z"
    },
    "BudgetType": "COST"
}
```

### Cost Explorer API Filters

```bash
# Filter to only EC2 costs
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --filter '{
        "Dimensions": {
            "Key": "SERVICE",
            "Values": ["Amazon Elastic Compute Cloud - Compute"]
        }
    }'

# Filter to only Free Tier eligible services
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity DAILY \
    --metrics UsageQuantity \
    --filter '{
        "Dimensions": {
            "Key": "RECORD_TYPE",
            "Values": ["Usage"]
        }
    }'
```

### Cost Allocation Tag Script

```bash
# Tag resources consistently with this pattern
# (Run this for future EC2/S3 resources)

resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123"

aws resourcegroupstaggingapi tag-resources \
    --resource-arn-list "$resource_arn" \
    --tags '{
        "Project": "stage-00",
        "Owner": "your-name",
        "Environment": "learning",
        "CostCenter": "personal"
    }'
```

---

## 7. Verification

```bash
# 1. Verify budget was created
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws budgets describe-budgets --account-id $ACCOUNT_ID --output table
# Expected: Table showing your budget(s)

# 2. Verify current month spend
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost
# Expected: JSON with BlendedCost Amount (should be 0 or very low for new accounts)

# 3. Verify CloudWatch alarm exists (must be in us-east-1)
aws cloudwatch describe-alarms \
    --alarm-names "billing-over-5-dollars" \
    --region us-east-1 \
    --output table
# Expected: Alarm in OK state

# 4. Verify SNS subscription confirmed
aws sns list-subscriptions-by-topic \
    --topic-arn "arn:aws:sns:us-east-1:$ACCOUNT_ID:billing-alerts" \
    --region us-east-1
# Expected: Your email with Status: Confirmed

# 5. Verify billing console access (IAM user)
aws ce get-dimension-values \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --dimension SERVICE
# Expected: List of AWS services (confirms billing API access)
```

---

## 8. Observations & Key Learnings

### Budget vs Alarm: Use Both
AWS Budgets and CloudWatch billing alarms are complementary:
- **Budgets** let you forecast and alert on expected charges before they happen (forecasted threshold)
- **CloudWatch** lets you react to actual charges as they occur (metric-based)
- Having both provides redundancy: if one alert fails to reach you, the other might

### The $5 Threshold Is Strategic
Setting the budget at $5 instead of higher values:
- Catches accidental resource creation (left-on EC2 = ~$8-15/month)
- Triggers before your bill becomes painful
- $5 = roughly 430 hours of t2.micro runtime (above free tier)
- Low enough to catch mistakes early in learning phase

### Free Tier Tracking
The free tier has three types:
1. **Always free** — e.g., Lambda 1M requests/month, DynamoDB 25 GB
2. **12 months free** — e.g., EC2 t2.micro 750 hours/month, S3 5 GB
3. **Trial** — e.g., some services offer 30-90 day free trials

### Common Billing Mistakes in Learning
| Mistake | Monthly Impact | Prevention |
|---------|---------------|------------|
| Forgot to delete EC2 instance | $8–$50+ | Budget alert |
| NAT Gateway left running | $32+ | Budget alert + tag review |
| RDS instance not stopped | $15–$50 | Use snapshots + delete |
| Data transfer out to internet | Variable | Monitor in Cost Explorer |
| Elastic IP not attached | $3.60/month | Release unattached EIPs |

### Programmatic Cost Monitoring
```bash
# Daily cost check script — run from cron or GitHub Actions
#!/bin/bash
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

COST=$(aws ce get-cost-and-usage \
    --time-period Start=$YESTERDAY,End=$TODAY \
    --granularity DAILY \
    --metrics BlendedCost \
    --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
    --output text)

echo "Yesterday's AWS cost: \$$COST"
```

---

## 9. Screenshots

Document these for your records:

1. **Billing Dashboard** — month-to-date charges (hopefully $0.00)
2. **Cost Explorer** — enabled screen or the chart view
3. **Budget created** — showing `monthly-learning-budget` in the Budgets list
4. **Budget detail** — showing the alert thresholds at 80% and 100%
5. **CloudWatch Alarm** — `billing-over-5-dollars` in OK (green) state
6. **Free Tier** — usage dashboard showing current vs limit
7. **SNS subscription confirmation email** — in your inbox

---

## 10. Cleanup

### Keep the Budget and Alarm
Unlike most resources, keeping billing alerts running costs almost nothing and protects you. The recommendation is to keep them.

### Delete Budget (if desired)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete via CLI
aws budgets delete-budget \
    --account-id $ACCOUNT_ID \
    --budget-name "monthly-learning-budget-cli"

# Verify deletion
aws budgets describe-budgets --account-id $ACCOUNT_ID
```

Or via console: Billing → Budgets → select budget → Delete

### Delete CloudWatch Alarm

```bash
aws cloudwatch delete-alarms \
    --alarm-names "billing-over-5-dollars" \
    --region us-east-1
```

### Delete SNS Topic and Subscription

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# List subscriptions
aws sns list-subscriptions --region us-east-1

# Delete the SNS topic (and all subscriptions)
aws sns delete-topic \
    --topic-arn "arn:aws:sns:us-east-1:$ACCOUNT_ID:billing-alerts" \
    --region us-east-1
```

### Cleanup Checklist
- [ ] Budget deleted or retained (recommend: retain)
- [ ] CloudWatch alarm deleted or retained (recommend: retain)
- [ ] SNS subscription confirmed (not just created)
- [ ] Cost Explorer enabled (keep enabled — it's free)
- [ ] Billing preferences set to email free tier alerts

---

*End of GUIDE.md — Project 0.4: AWS Billing Setup*

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
