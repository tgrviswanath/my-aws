# Verification & Validation — Project 9.9 Redshift Data Warehouse

> Namespace: `handson-namespace` | Workgroup: `handson-workgroup`
> Database: `analytics` | Port: 5439 | IAM Role: `handson-redshift-role`

---

## 1. AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| Namespace | Redshift → Serverless → Namespaces | `handson-namespace` Status = **Available** |
| Workgroup | Redshift → Serverless → Workgroups | `handson-workgroup` Status = **Available** |
| Endpoint | Workgroup → Details tab | URL ends in `.redshift-serverless.amazonaws.com` |
| IAM role | IAM → Roles → `handson-redshift-role` | S3ReadOnly + GlueConsole attached |
| Query Editor | Redshift → Query Editor v2 | Can run `SELECT 1;` |
| Tables | Query Editor → Schema browser | `analytics.fact_orders` + `analytics.dim_date` |
| Row count | `SELECT COUNT(*) FROM analytics.fact_orders` | > 0 after COPY |

📸 Screenshot: Workgroup Status = Available + endpoint URL
📸 Screenshot: Query Editor showing tables + revenue query result
📸 Screenshot: Terminal `load` output showing row count

---

## 2. CLI Verification (PowerShell)

```powershell
Write-Host "=== REDSHIFT VERIFICATION ===" -ForegroundColor Cyan

# Workgroup status
aws redshift-serverless get-workgroup --workgroup-name $WG_NAME `
  --query "workgroup.{Status:status,Endpoint:endpoint.address,Port:endpoint.port}"
# Expected: status=AVAILABLE, Endpoint=...amazonaws.com, Port=5439

# Namespace status
aws redshift-serverless get-namespace --namespace-name $NS_NAME `
  --query "namespace.{Status:status,DB:dbName,Admin:adminUsername}"
# Expected: status=AVAILABLE, DB=analytics, Admin=admin

# Row counts via Data API
$QID = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT 'fact_orders' tbl,COUNT(*) n FROM analytics.fact_orders UNION ALL SELECT 'dim_date',COUNT(*) FROM analytics.dim_date;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
aws redshift-data describe-statement --id $QID `
  --query "{Status:Status,Rows:ResultRows}"
# Expected: Status=FINISHED, Rows=2

aws redshift-data get-statement-result --id $QID `
  --query "Records[*][*].stringValue"
# Expected: [["fact_orders","N"],["dim_date","4018"]]

# Python operations
python code\redshift_operations.py setup
python code\redshift_operations.py load
python code\redshift_operations.py report

Write-Host "=== COMPLETE ===" -ForegroundColor Green
```

---

## 3. End-to-End Health Check

```powershell
Write-Host "=== HEALTH CHECK ===" -ForegroundColor Cyan

# 1. Workgroup available
$ST = aws redshift-serverless get-workgroup `
  --workgroup-name $WG_NAME --query "workgroup.status" --output text
Write-Host "[1] Workgroup: $ST"

# 2. fact_orders has rows
$QID = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT COUNT(*) FROM analytics.fact_orders;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
$CNT = aws redshift-data get-statement-result --id $QID `
  --query "Records[0][0].longValue" --output text
Write-Host "[2] fact_orders rows: $CNT"

# 3. Top product query works
$QID2 = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT product_id, SUM(total_amount) AS rev FROM analytics.fact_orders GROUP BY 1 ORDER BY 2 DESC LIMIT 1;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
$TOP = aws redshift-data get-statement-result --id $QID2 `
  --query "Records[0][*].stringValue" --output text
Write-Host "[3] Top product: $TOP"

# 4. dim_date joined query
$QID3 = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT d.day_name, COUNT(*) FROM analytics.fact_orders o JOIN analytics.dim_date d ON d.full_date=o.order_date GROUP BY 1 ORDER BY 2 DESC LIMIT 3;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
$DAYS = aws redshift-data get-statement-result --id $QID3 `
  --query "Records[*][0].stringValue" --output text
Write-Host "[4] Top order days: $DAYS"

Write-Host "=== HEALTH CHECK COMPLETE ===" -ForegroundColor Green
```

---

## 4. Expected Successful Outputs

**`redshift_operations.py setup`:**
```
Creating schema: analytics  ✓
Creating table: analytics.fact_orders  ✓
Creating table: analytics.dim_date  ✓
Populating dim_date (2020–2030)...  ✓
Setup complete
```

**`redshift_operations.py load`:**
```
Source: s3://handson-data-lake-.../processed/orders/
Running COPY command...
✓ Load complete — 1,000 total rows in fact_orders
VACUUM SORT ONLY  ✓
ANALYZE  ✓
Post-load optimization complete
```

**`redshift_operations.py report`:**
```
Top 10 Products by Revenue
+--------------+-------------+-----------+---------------+-----------+
| PRODUCT_ID   | ORDER_COUNT | UNITS_SOLD | TOTAL_REVENUE | AVG_PRICE |
+--------------+-------------+-----------+---------------+-----------+
| PROD-A001    | 234         | 468       | 6789.00       | 29.00     |
| ...
(10 row(s))

Customer Lifetime Value (Top 20)
+-------------+-------------+----------------+ ...
```

---

## 5. Verification Checklist

- [ ] Namespace `handson-namespace` Status = AVAILABLE
- [ ] Workgroup `handson-workgroup` Status = AVAILABLE, port 5439
- [ ] IAM role `handson-redshift-role`: AmazonS3ReadOnlyAccess + AWSGlueConsoleFullAccess
- [ ] `setup` completes — schema + 2 tables created
- [ ] `dim_date` has ~4018 rows (2020–2030 dates)
- [ ] `load` COPY succeeds — `fact_orders` row count > 0
- [ ] `VACUUM SORT ONLY` runs without error
- [ ] `ANALYZE` runs without error
- [ ] `report` prints 4 formatted query result tables
- [ ] Redshift Data API query returns results
- [ ] Query Editor v2 can connect and run SQL

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
