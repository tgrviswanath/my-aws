# Verification & Validation — Project 0.4 AWS Cost & Billing Fundamentals

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Billing alerts enabled | Billing → Billing preferences | "Receive Billing Alerts" = **enabled** |
| Free Tier alerts enabled | Billing → Billing preferences | "Receive Free Tier Usage Alerts" = **enabled** |
| SNS Topic | SNS → Topics (us-east-1) | `billing-alerts` topic exists |
| SNS Subscription | SNS → Subscriptions | Your email, Status = **Confirmed** |
| CloudWatch Alarm | CloudWatch → Alarms (us-east-1) | `billing-alert-10usd`, State = **OK** |
| AWS Budget | Billing → Budgets | `monthly-aws-budget`, $20 limit, 3 alert thresholds |
| Cost Explorer | Billing → Cost Explorer | Enabled (not showing "Enable" button) |

📸 Screenshot: Billing preferences page with both alert checkboxes enabled  
📸 Screenshot: CloudWatch alarm `billing-alert-10usd` showing State = OK  
📸 Screenshot: AWS Budget showing all 3 thresholds (50%, 80%, 100%)

---

## 2. AWS CLI Verification

```bash
# Must use us-east-1 for billing resources
export AWS_DEFAULT_REGION=us-east-1

# 2.1 SNS topic exists
aws sns list-topics --region us-east-1 \
  --query "Topics[?contains(TopicArn,'billing-alerts')].TopicArn"
# Expected: arn:aws:sns:us-east-1:<account-id>:billing-alerts

# 2.2 SNS subscription confirmed
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:<ACCOUNT_ID>:billing-alerts \
  --region us-east-1 \
  --query "Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint,Status:SubscriptionArn}"
# Expected: Protocol=email, Status=confirmed (not PendingConfirmation)

# 2.3 CloudWatch alarm exists
aws cloudwatch describe-alarms \
  --alarm-names "billing-alert-10usd" \
  --region us-east-1 \
  --query "MetricAlarms[*].{Name:AlarmName,State:StateValue,Threshold:Threshold,Metric:MetricName}"
# Expected: State=OK, Threshold=10, Metric=EstimatedCharges

# 2.4 Budget exists
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws budgets describe-budgets \
  --account-id $ACCOUNT_ID \
  --query "Budgets[?BudgetName=='monthly-aws-budget'].{Name:BudgetName,Limit:BudgetLimit.Amount,Type:BudgetType}"
# Expected: Name=monthly-aws-budget, Limit=20, Type=COST
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_sns_topic.billing_alerts
# aws_sns_topic_subscription.email
# aws_cloudwatch_metric_alarm.billing_10
# aws_budgets_budget.monthly

terraform state show aws_cloudwatch_metric_alarm.billing_10
# Shows: threshold=10, metric_name=EstimatedCharges, namespace=AWS/Billing

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Billing Monitor Script

```bash
pip install boto3
python code/billing_monitor.py
```

Expected output:
```
=== AWS Cost Report ===
Month-to-date spend: $X.XX
Top services:
  1. Amazon EC2:        $X.XX
  2. Amazon S3:         $X.XX
  ...
Forecast (end of month): $X.XX

=== Budget Status ===
monthly-aws-budget: $X.XX / $20.00 (X%)
  ✅ Under 50% threshold
```

📸 Screenshot: billing_monitor.py output showing cost summary

---

## 5. Cost Allocation Tags Verification

```bash
# Confirm tags are activated in Billing console
# Billing → Cost allocation tags → User-defined tags
# Expected: Project, Stage, Owner, Environment tags listed as Active

# Verify a tagged resource (example with an EC2 instance)
aws ec2 describe-tags \
  --filters "Name=key,Values=Project" "Name=value,Values=handson" \
  --query "Tags[*].{Resource:ResourceId,Key:Key,Value:Value}"
# Expected: resources tagged with Project=handson
```

---

## 6. Expected Successful Outputs

**CloudWatch alarm:**
```json
[{
  "Name": "billing-alert-10usd",
  "State": "OK",
  "Threshold": 10.0,
  "Metric": "EstimatedCharges"
}]
```

**Budget:**
```json
[{
  "Name": "monthly-aws-budget",
  "Limit": "20",
  "Type": "COST"
}]
```

**SNS subscription:**
```json
[{
  "Protocol": "email",
  "Endpoint": "your@email.com",
  "Status": "arn:aws:sns:us-east-1:xxx:billing-alerts:xxx"
}]
```

---

## 7. Verification Checklist

- [ ] Billing alerts enabled in Billing preferences (root user)
- [ ] Free Tier usage alerts enabled
- [ ] SNS topic `billing-alerts` created in us-east-1
- [ ] Email subscription confirmed (not PendingConfirmation)
- [ ] CloudWatch alarm `billing-alert-10usd` state = OK
- [ ] AWS Budget `monthly-aws-budget` created with $20 limit
- [ ] Budget has 3 alert thresholds: 50%, 80%, 100% forecasted
- [ ] Cost Explorer enabled
- [ ] Cost allocation tags activated (Project, Stage, Owner, Environment)
- [ ] `terraform plan` shows no changes
- [ ] `billing_monitor.py` runs and shows cost summary

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
