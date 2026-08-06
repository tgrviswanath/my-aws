# Verification & Validation — Project 9.6 dbt Transformation Pipeline

> dbt models: stg_orders (VIEW) + fct_orders (TABLE)
> Database: handson_data_lake | Workgroup: handson-dbt

---

## 1. AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| Glue source table | Glue → Tables → handson_data_lake | `orders` table present |
| stg_orders view | Athena → Editor → handson_data_lake | `stg_orders` in tables list |
| fct_orders table | Athena → Editor → handson_data_lake | `fct_orders` in tables list |
| dbt workgroup | Athena → Workgroups | `handson-dbt` Active |
| S3 staging bucket | S3 → `handson-dbt-staging-ACCOUNT` | Bucket exists |
| S3 dbt results | S3 → staging bucket → dbt/ | Query result files present after run |

📸 Screenshot: Athena table list showing stg_orders and fct_orders
📸 Screenshot: `dbt run` terminal output — PASS=2
📸 Screenshot: `dbt test` terminal output — all PASS
📸 Screenshot: dbt docs lineage graph
📸 Screenshot: Athena fct_orders query returning order_tier results

---

## 2. dbt Command Verification

```powershell
Set-Location $DBT_DIR

# Full verification sequence
Write-Host "=== dbt VERIFICATION ===" -ForegroundColor Cyan

# 1. Connection test
dbt debug
# Expected: All checks passed
# profiles.yml file [OK found and valid]
# dbt_project.yml file [OK found and valid]
# Connection test: [OK connection ok]

# 2. Install packages
dbt deps
# Expected: Installing dbt-labs/dbt_utils 1.1.1 — OK

# 3. Run models
dbt run
# Expected:
# 1 of 2 OK created sql view model handson_data_lake.stg_orders  [OK]
# 2 of 2 OK created sql incremental model handson_data_lake.fct_orders [OK]
# Done. PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=2

# 4. Run tests
dbt test
# Expected:
# 1 of 7 PASS not_null_fct_orders_order_id
# 2 of 7 PASS unique_fct_orders_order_id
# 3 of 7 PASS not_null_fct_orders_customer_id
# 4 of 7 PASS not_null_fct_orders_order_amount_usd
# 5 of 7 PASS dbt_utils_expression_is_true_fct_orders_order_amount_usd__0
# 6 of 7 PASS accepted_values_fct_orders_order_status__pending__processing__shipped__delivered__cancelled__unknown
# 7 of 7 PASS accepted_values_fct_orders_order_tier__high_value__medium_value__low_value
# Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7

# 5. Check manifest
$M = Get-Content "target\manifest.json" | ConvertFrom-Json
$MODELS = $M.nodes.PSObject.Properties |
  Where-Object { $_.Value.resource_type -eq "model" } |
  ForEach-Object { $_.Value.name }
Write-Host "Models in manifest: $($MODELS -join ', ')"
# Expected: stg_orders, fct_orders

# 6. Verify incremental (second run faster)
Measure-Command { dbt run --select fct_orders }
# Expected: faster than first run (fewer rows processed)

Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

---

## 3. Athena CLI Verification

```powershell
# List tables in database
$QID = aws athena start-query-execution `
  --query-string "SHOW TABLES IN handson_data_lake" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/verify/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID
aws athena get-query-results --query-execution-id $QID `
  --query "ResultSet.Rows[*].Data[0].VarCharValue" --output table
# Expected: orders, stg_orders, fct_orders

# Count fct_orders rows
$QID2 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM handson_data_lake.fct_orders" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/verify/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID2
$COUNT = aws athena get-query-results --query-execution-id $QID2 `
  --query "ResultSet.Rows[1].Data[0].VarCharValue" --output text
Write-Host "fct_orders row count: $COUNT"
# Expected: > 0

# Verify order_tier distribution
$QID3 = aws athena start-query-execution `
  --query-string "SELECT order_tier, COUNT(*) as n FROM handson_data_lake.fct_orders GROUP BY 1 ORDER BY n DESC" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/verify/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID3
aws athena get-query-results --query-execution-id $QID3 `
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
# Expected: high_value, medium_value, low_value rows
```

---

## 4. dbt Artifacts Verification

```powershell
Set-Location $DBT_DIR

# Confirm manifest exists after run
Test-Path "target\manifest.json"   # Expected: True
Test-Path "target\run_results.json" # Expected: True

# Check compiled SQL
Get-Content "target\compiled\handson\models\staging\stg_orders.sql"
# Expected: SQL SELECT with WHERE order_id IS NOT NULL AND amount > 0

Get-Content "target\compiled\handson\models\marts\fct_orders.sql"
# Expected: incremental SELECT with WHERE order_date > (SELECT MAX...)

# After dbt docs generate:
Test-Path "target\catalog.json"    # Expected: True
```

---

## 5. Expected Successful Outputs

**`dbt run`:**
```
Done. PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=2
Completed successfully
```

**`dbt test`:**
```
Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7
Completed successfully
```

**Athena fct_orders sample:**
```
| order_tier   | orders | revenue  |
|--------------|--------|----------|
| high_value   | 23     | 3450.20  |
| medium_value | 45     | 2870.50  |
| low_value    | 122    | 1890.30  |
```

---

## 6. Verification Checklist

- [ ] `dbt debug` — all checks passed (profiles.yml + dbt_project.yml + connection)
- [ ] `dbt deps` — dbt-utils 1.1.1 installed
- [ ] `dbt run` — PASS=2, stg_orders (VIEW) + fct_orders (TABLE) created
- [ ] `stg_orders` VIEW exists in Athena handson_data_lake
- [ ] `fct_orders` TABLE exists in Athena handson_data_lake
- [ ] `fct_orders` has rows (COUNT(*) > 0)
- [ ] `dbt test` — PASS=7, all quality checks green
- [ ] `dbt run` second time — faster (incremental processes only new rows)
- [ ] `dbt docs generate` — target/catalog.json created
- [ ] `dbt docs serve` — lineage graph visible at localhost:8080
- [ ] `order_tier` column has only: high_value, medium_value, low_value

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
