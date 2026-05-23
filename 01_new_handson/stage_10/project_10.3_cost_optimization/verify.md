# Verification & Validation — Project 10.3 Cost Optimization Automation

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Cost Anomaly Detection | Cost Management → Cost Anomaly Detection | Monitor created, alert threshold set |
| AWS Budgets | Cost Management → Budgets | Budget with alert configured |
| Compute Optimizer | Compute Optimizer → Dashboard | Recommendations available |
| S3 Lifecycle Rules | S3 → Bucket → Management → Lifecycle | Rules moving objects to IA/Glacier |
| Lambda (scheduler) | Lambda → Functions | `handson-cost-optimizer` function exists |
| EventBridge Rule | EventBridge → Rules | Scheduled rule triggering Lambda |
| Cost Explorer Tags | Cost Management → Cost Explorer | Resources tagged and visible |

📸 Screenshot: AWS Budgets alert configured  
📸 Screenshot: Compute Optimizer showing rightsizing recommendations  
📸 Screenshot: `cost_optimizer.py --dry-run` output showing savings opportunities

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm budget exists
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --query "Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Type:BudgetType}"
# Expected: handson-monthly-budget listed

# 2.2 Check cost anomaly monitors
aws ce get-anomaly-monitors \
  --query "AnomalyMonitors[*].{Name:MonitorName,Type:MonitorType,Status:MonitorStatus}"
# Expected: monitor listed, Status=ACTIVE

# 2.3 Check Compute Optimizer recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --query "instanceRecommendations[*].{Instance:instanceArn,Finding:finding,Savings:recommendationOptions[0].estimatedMonthlySavings.value}" \
  --output table 2>/dev/null || echo "No EC2 recommendations (account may need 14 days of data)"
# Expected: recommendations listed (or message if insufficient data)

# 2.4 Confirm S3 lifecycle rules
BUCKET=$(aws s3 ls | grep handson | awk '{print $3}' | head -1)
aws s3api get-bucket-lifecycle-configuration \
  --bucket $BUCKET \
  --query "Rules[*].{ID:ID,Status:Status,Transitions:Transitions[*].{Days:Days,Class:StorageClass}}"
# Expected: rules moving to STANDARD_IA after 30 days, GLACIER after 90 days

# 2.5 Check for idle EC2 instances (dry run)
python src/cost_optimizer.py --dry-run --action stop-idle-ec2
# Expected: list of EC2 instances with CPU < 5% for 7 days (or "No idle instances found")

# 2.6 Check for unattached EBS volumes
python src/cost_optimizer.py --dry-run --action delete-unattached-ebs
# Expected: list of unattached volumes (or "No unattached volumes found")

# 2.7 Check for old snapshots
python src/cost_optimizer.py --dry-run --action remove-old-snapshots
# Expected: list of snapshots > 30 days (or "No old snapshots found")

# 2.8 Check resource tagging compliance
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=handson \
  --query "ResourceTagMappingList[*].ResourceARN" | wc -l
# Expected: tagged resources count > 0
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_budgets_budget.monthly
# aws_ce_anomaly_monitor.main
# aws_ce_anomaly_subscription.main
# aws_lambda_function.cost_optimizer
# aws_cloudwatch_event_rule.weekly_cleanup
# aws_cloudwatch_event_target.cost_optimizer
# aws_iam_role.cost_optimizer
# aws_s3_bucket_lifecycle_configuration.data_lake

terraform state show aws_budgets_budget.monthly
# Shows: budget_limit.amount, time_unit=MONTHLY, notification thresholds

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Cost Optimization Scan

```bash
# Full dry-run scan (no changes made)
python src/cost_optimizer.py --dry-run

# Expected output:
# === Cost Optimization Scan (DRY RUN) ===
# Idle EC2 instances (CPU < 5% for 7 days):
#   None found ✅
#
# Unattached EBS volumes:
#   vol-0abc123 (20 GB, gp2) — unattached for 8 days — saves $2.00/month
#
# Old snapshots (> 30 days):
#   snap-0def456 (50 GB) — 45 days old — saves $2.50/month
#
# Total potential savings: $4.50/month
# Run without --dry-run to apply changes

# Verify Lambda is scheduled
aws events list-rules \
  --query "Rules[?contains(Name,'cost')].{Name:Name,Schedule:ScheduleExpression,State:State}"
# Expected: weekly schedule rule listed, State=ENABLED
```

---

## 5. Expected Successful Outputs

**CLI — describe-budgets:**
```json
[{ "Name": "handson-monthly-budget", "Limit": "50.00", "Type": "COST" }]
```

**cost_optimizer.py --dry-run:**
```
=== Cost Optimization Scan (DRY RUN) ===
Idle EC2 instances:     0 found
Unattached EBS volumes: 1 found → saves $2.00/month
Old snapshots:          2 found → saves $5.00/month
Total potential savings: $7.00/month
```

**S3 lifecycle rules:**
```json
[{
  "ID": "move-to-ia",
  "Status": "Enabled",
  "Transitions": [
    { "Days": 30,  "Class": "STANDARD_IA" },
    { "Days": 90,  "Class": "GLACIER" },
    { "Days": 365, "Class": "DEEP_ARCHIVE" }
  ]
}]
```

---

## 6. Verification Checklist

- [ ] AWS Budget `handson-monthly-budget` exists with alert threshold
- [ ] Cost Anomaly Detection monitor Status = ACTIVE
- [ ] Compute Optimizer enabled (recommendations available after 14 days)
- [ ] S3 lifecycle rules: STANDARD_IA at 30 days, GLACIER at 90 days
- [ ] Lambda `handson-cost-optimizer` exists
- [ ] EventBridge weekly schedule rule State = ENABLED
- [ ] `cost_optimizer.py --dry-run` runs without error
- [ ] Resources tagged with Project=handson (tagging compliance)
- [ ] `terraform plan` shows no changes
