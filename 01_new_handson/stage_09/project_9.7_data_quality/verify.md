# Verification & Validation — Project 9.7 Data Quality Validation

> Lambda: `handson-data-quality-check` | SNS: `handson-data-quality-alerts`
> EventBridge: `handson-glue-job-success` | IAM: `handson-quality-lambda-role`

---

## 1. Local Validation Verification

| Test | Command | Expected |
|------|---------|----------|
| Clean data | `python src/validate_orders.py` (clean parquet) | PASSED, exit code=0 |
| Dirty data | `python src/validate_orders.py` (dirty parquet) | FAILED, exit code=1 |
| Null detection | Dirty data with `order_id=None` | `expect_column_values_to_not_be_null` FAILS |
| Duplicate detection | Dirty data with duplicate `ORD-001` | `expect_column_values_to_be_unique` FAILS |
| Negative amount | Dirty data with `amount=-5.00` | `expect_column_values_to_be_between` FAILS |

📸 Screenshot: FAILED output with 3 specific failing checks named
📸 Screenshot: PASSED output — all 10 checks green

---

## 2. AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| SNS Topic | SNS → Topics | `handson-data-quality-alerts` listed |
| Email sub | Topic → Subscriptions | Status = Confirmed |
| EventBridge | EventBridge → Rules | `handson-glue-job-success` Enabled |
| Lambda | Lambda → Functions | `handson-data-quality-check` Active |
| Lambda env | Lambda → Configuration → Env vars | DATA_LAKE_BUCKET + SNS_TOPIC_ARN |
| CloudWatch | CloudWatch → Log groups | `/aws/lambda/handson-data-quality-check` |
| S3 reports | S3 → bucket → `data-quality/reports/` | JSON files present after run |

---

## 3. CLI Verification (PowerShell)

```powershell
# Verify all AWS resources
Write-Host "=== VERIFICATION ===" -ForegroundColor Cyan

# SNS topic
aws sns list-topics --query "Topics[?contains(TopicArn,'data-quality')]"
# Expected: topic listed

# SNS subscription confirmed
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN `
  --query "Subscriptions[0].SubscriptionArn"
# Expected: arn:... (not PendingConfirmation)

# Lambda active
aws lambda get-function --function-name $LAMBDA_NAME `
  --query "Configuration.{State:State,Memory:MemorySize,Timeout:Timeout}"
# Expected: State=Active, Memory=512, Timeout=300

# Lambda env vars set
aws lambda get-function-configuration --function-name $LAMBDA_NAME `
  --query "Environment.Variables"
# Expected: DATA_LAKE_BUCKET and SNS_TOPIC_ARN present

# EventBridge rule enabled
aws events describe-rule --name "handson-glue-job-success" `
  --query "{State:State,Pattern:EventPattern}"
# Expected: State=ENABLED

# EventBridge target is Lambda
aws events list-targets-by-rule --rule "handson-glue-job-success" `
  --query "Targets[0].Arn"
# Expected: arn:aws:lambda:...handson-data-quality-check
```

---

## 4. Full Local Quality Test

```powershell
Write-Host "=== FULL QUALITY GATE TEST ===" -ForegroundColor Cyan

# STEP 1: dirty data
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
}).to_parquet('/tmp/dirty.parquet', index=False)"

$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
if ($LASTEXITCODE -ne 0) {
  Write-Host "✅ PASS: Dirty data correctly FAILED (exit 1)" -ForegroundColor Green
} else {
  Write-Host "❌ FAIL: Dirty data was not detected" -ForegroundColor Red
}

# STEP 2: clean data
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002','ORD-003'],
    'customer_id':['C1','C2','C3'],
    'product':    ['Widget A','Widget B','Widget C'],
    'amount':     [29.99,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16']
}).to_parquet('/tmp/clean.parquet', index=False)"

python src\validate_orders.py
if ($LASTEXITCODE -eq 0) {
  Write-Host "✅ PASS: Clean data correctly PASSED (exit 0)" -ForegroundColor Green
} else {
  Write-Host "❌ FAIL: Clean data was incorrectly rejected" -ForegroundColor Red
}

Write-Host "=== TEST COMPLETE ===" -ForegroundColor Cyan
```

---

## 5. Expected Successful Outputs

**validate_orders.py — clean data:**
```
==================================================
Data Quality Report — 2024-01-15 14:30:00
==================================================
Status:  ✅ PASSED
Checks:  10/10 passed
Rows:    3

✅ Data quality validation PASSED
```

**validate_orders.py — dirty data:**
```
==================================================
Data Quality Report — 2024-01-15 14:30:01
==================================================
Status:  ❌ FAILED
Checks:  7/10 passed
Rows:    4

Failed checks:
  ❌ expect_column_values_to_not_be_null: {'column': 'order_id'}
  ❌ expect_column_values_to_be_unique: {'column': 'order_id'}
  ❌ expect_column_values_to_be_between: {'column': 'amount', 'min_value': 0.01, 'max_value': 10000.0}

❌ Data quality validation FAILED — pipeline should not proceed
```

---

## 6. Verification Checklist

**Local:**
- [ ] `great-expectations` imports without error
- [ ] Dirty data → exit code = 1, shows 3 failed checks
- [ ] Clean data → exit code = 0, shows "10/10 passed"
- [ ] Null detection: null order_id → `not_null` check FAILS
- [ ] Duplicate detection: duplicate ORD-001 → `unique` check FAILS
- [ ] Negative detection: amount=-5.00 → `between` check FAILS

**AWS:**
- [ ] SNS topic `handson-data-quality-alerts` exists
- [ ] Email subscription Status = Confirmed (not PendingConfirmation)
- [ ] Lambda `handson-data-quality-check` State = Active, Timeout=300s, Memory=512MB
- [ ] Lambda env: `DATA_LAKE_BUCKET` + `SNS_TOPIC_ARN` set
- [ ] EventBridge rule `handson-glue-job-success` State = ENABLED
- [ ] EventBridge target = Lambda ARN
- [ ] Lambda invocation returns validation output
- [ ] CloudWatch log group `/aws/lambda/handson-data-quality-check` exists

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
