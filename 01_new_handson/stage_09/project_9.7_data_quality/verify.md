# Verification & Validation — Project 9.7 Data Quality Validation

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Glue DataBrew | Glue DataBrew → Datasets | Dataset profiled (if DataBrew used) |
| S3 Quarantine | S3 → data lake bucket → quarantine/ | Bad records moved here on failure |
| S3 Data Docs | S3 → data lake bucket → data-docs/ | Great Expectations HTML report |
| CloudWatch Alarm | CloudWatch → Alarms | Data quality alarm configured |
| Lambda (if automated) | Lambda → Functions | Quality check Lambda exists |

📸 Screenshot: `validate_orders.py` output showing PASSED checks  
📸 Screenshot: Great Expectations data docs HTML report  
📸 Screenshot: Failed validation output showing which checks failed and why

---

## 2. CLI Verification

```bash
# 2.1 Run validation on clean data (should PASS)
python3 -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001', 'ORD-002', 'ORD-003'],
    'amount':     [29.99, 49.99, 19.99],
    'product':    ['Widget A', 'Widget B', 'Widget A'],
    'order_date': ['2024-01-15', '2024-01-15', '2024-01-16']
})
df.to_parquet('/tmp/clean_orders.parquet', index=False)
print('Clean test data created')
"
python src/validate_orders.py --input /tmp/clean_orders.parquet
# Expected: all checks PASSED

# 2.2 Run validation on dirty data (should FAIL specific checks)
python3 -c "
import pandas as pd
df = pd.DataFrame({
    'order_id':   ['ORD-001', 'ORD-002', None, 'ORD-001'],
    'amount':     [29.99, -5.00, 49.99, 19.99],
    'product':    ['Widget A', 'Widget B', 'Unknown', 'Widget C'],
    'order_date': ['2024-01-15', '2024-01-15', '2024-01-16', '2024-01-16']
})
df.to_parquet('/tmp/dirty_orders.parquet', index=False)
print('Dirty test data created')
"
python src/validate_orders.py --input /tmp/dirty_orders.parquet
# Expected: FAILED checks:
#   - order_id not null: FAILED (1 null)
#   - order_id unique: FAILED (duplicate ORD-001)
#   - amount > 0: FAILED (negative value -5.00)

# 2.3 Verify quarantine zone receives bad records
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
aws s3 ls s3://$BUCKET/quarantine/ --recursive | head -5
# Expected: quarantine files present after failed validation

# 2.4 Check data docs generated
aws s3 ls s3://$BUCKET/data-docs/ --recursive | head -5
# Expected: index.html and validation result HTML files

# 2.5 Verify row count check
python3 -c "
import pandas as pd
df = pd.read_parquet('/tmp/clean_orders.parquet')
assert len(df) > 0, 'Row count check failed'
print(f'✅ Row count check: {len(df)} rows')
assert df['order_id'].notna().all(), 'Null order_id found'
print('✅ Not null check: order_id')
assert df['order_id'].is_unique, 'Duplicate order_id found'
print('✅ Unique check: order_id')
assert (df['amount'] > 0).all(), 'Non-positive amount found'
print('✅ Range check: amount > 0')
print('All checks passed ✅')
"
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_s3_bucket_object.quarantine_prefix (or lifecycle rule)
# aws_lambda_function.data_quality (if automated)
# aws_cloudwatch_metric_alarm.data_quality_failures
# aws_sns_topic.data_quality_alerts

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Full Validation Pipeline

```bash
# Step 1: Create sample data with known issues
python3 -c "
import pandas as pd
# Mix of good and bad records
df = pd.DataFrame({
    'order_id':   ['ORD-001', 'ORD-002', None,      'ORD-001', 'ORD-004'],
    'amount':     [29.99,     49.99,     19.99,      -5.00,     99.99],
    'product':    ['Widget A','Widget B','Widget A', 'Widget C','Widget A'],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16','2024-01-17']
})
df.to_parquet('/tmp/mixed_orders.parquet', index=False)
print(f'Created {len(df)} rows (3 good, 2 bad)')
"

# Step 2: Run validation
python src/validate_orders.py --input /tmp/mixed_orders.parquet

# Step 3: Verify output
echo "=== Validation Summary ==="
echo "Expected failures:"
echo "  - order_id not null: 1 null value"
echo "  - order_id unique: 1 duplicate (ORD-001)"
echo "  - amount > 0: 1 negative value (-5.00)"
```

---

## 5. Expected Successful Outputs

**validate_orders.py on clean data:**
```
=== Data Quality Validation Report ===
✅ Row count > 0:          PASSED (3 rows)
✅ order_id not null:      PASSED (100%)
✅ order_id unique:        PASSED (100%)
✅ amount > 0:             PASSED (100%)
✅ order_date valid:       PASSED (100%)
✅ product in known list:  PASSED (100%)

6/6 checks passed — Data quality: EXCELLENT ✅
```

**validate_orders.py on dirty data:**
```
=== Data Quality Validation Report ===
✅ Row count > 0:          PASSED (4 rows)
❌ order_id not null:      FAILED (75% — 1 null found)
❌ order_id unique:        FAILED (75% — duplicate: ORD-001)
❌ amount > 0:             FAILED (75% — negative: -5.00)
✅ order_date valid:       PASSED (100%)
⚠️  product in known list: WARNING (75% — 'Unknown' not in list)

3/6 checks passed — Data quality: POOR ❌
Bad records moved to quarantine/
```

---

## 6. Verification Checklist

- [ ] `validate_orders.py` runs without import errors
- [ ] Clean data: all 6 checks PASSED
- [ ] Dirty data: null check FAILED (detects null order_id)
- [ ] Dirty data: unique check FAILED (detects duplicate order_id)
- [ ] Dirty data: range check FAILED (detects negative amount)
- [ ] Bad records moved to S3 quarantine/ prefix
- [ ] Great Expectations data docs HTML generated
- [ ] Validation results logged (CloudWatch or file)
- [ ] `terraform plan` shows no changes
