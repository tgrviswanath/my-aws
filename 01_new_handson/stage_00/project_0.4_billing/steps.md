# Steps — Project 0.4 AWS Cost & Billing Fundamentals

## Phase 1 — Enable Billing Alerts (Console — Root User Required)

1. Log in to AWS Console as **root user**
2. Click your account name (top right) → **Account**
3. Scroll to **Billing preferences**
4. Enable:
   - ✅ Receive AWS Free Tier Usage Alerts
   - ✅ Receive Billing Alerts
5. Click **Save preferences**

> ⚠️ This must be done as root. IAM users cannot enable billing alerts.

---

## Phase 2 — Create SNS Topic for Alerts

```bash
# Must use us-east-1 for billing metrics
aws sns create-topic \
  --name billing-alerts \
  --region us-east-1

# Subscribe your email (replace with your email)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:billing-alerts \
  --protocol email \
  --notification-endpoint your@email.com \
  --region us-east-1

# ✅ Check your email and click "Confirm subscription"
```

---

## Phase 3 — Create CloudWatch Billing Alarm

```bash
# $10 alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "billing-alert-10usd" \
  --alarm-description "Alert when estimated charges exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:billing-alerts \
  --region us-east-1

# Verify alarm was created
aws cloudwatch describe-alarms \
  --alarm-names "billing-alert-10usd" \
  --region us-east-1
```

---

## Phase 4 — Create AWS Budget

```bash
# Get your account ID
aws sts get-caller-identity --query Account --output text

# Create $20/month budget with 80% alert
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget '{
    "BudgetName": "monthly-aws-budget",
    "BudgetLimit": {"Amount": "20", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 50,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
    },
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
    },
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
    }
  ]'
```

---

## Phase 5 — Set Up Cost Allocation Tags

```bash
# In AWS Console: Billing → Cost allocation tags → Activate user-defined tags
# Then tag all resources you create going forward:

# Example: tag an EC2 instance
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags \
    Key=Project,Value=handson \
    Key=Stage,Value=stage-01 \
    Key=Owner,Value=yourname \
    Key=Environment,Value=learning

# Tagging convention for this roadmap:
# Project=handson
# Stage=stage-XX
# Owner=yourname
# Environment=learning
```

---

## Phase 6 — Enable Cost Explorer

1. Go to **Billing** → **Cost Explorer**
2. Click **Enable Cost Explorer** (first time only)
3. Wait 24 hours for data to populate
4. Explore:
   - Cost by service
   - Cost by region
   - Free tier usage tracker

---

## Phase 7 — Deploy with Terraform

```bash
cd terraform

# Initialize
terraform init

# Preview
terraform plan -var="alert_email=your@email.com" -var="budget_limit=20"

# Apply
terraform apply -var="alert_email=your@email.com" -var="budget_limit=20"

# Verify outputs
terraform output
```

---

## Screenshots to Take
- [ ] Billing preferences page with alerts enabled
- [ ] SNS subscription confirmed in email
- [ ] CloudWatch alarm created (green in console)
- [ ] AWS Budget created with thresholds visible
- [ ] Cost Explorer enabled
- [ ] `terraform apply` success output
