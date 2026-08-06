# Verification & Validation — Project 9.8 Schema Evolution & Partitioning

> Registry: `handson-registry` | Schema: `orders-schema` | DB: `handson_schema_demo`
> Table: `orders_partitioned` | S3 path: `schema-demo/year=2024/month=01/`

---

## 1. AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| Registry | Glue → Schema Registry → Registries | `handson-registry` Status = **Available** |
| Schema v1 | Registry → `orders-schema` → Versions | Version 1 **Available** |
| Schema v2 | Registry → `orders-schema` → Versions | Version 2 **Available** |
| v2 fields | Version 2 → View definition | `product` and `discount_pct` with null union type |
| S3 files | S3 → bucket → `schema-demo/year=2024/month=01/` | `v1_orders.parquet` + `v2_orders.parquet` |
| Glue database | Glue → Databases | `handson_schema_demo` listed |
| Glue table | Glue → Tables → `orders_partitioned` | partition projection properties visible |
| Athena query | Athena with `WHERE year=2024 AND month=1` | Less data scanned vs without filter |

📸 Screenshot: Glue Schema Registry showing v1 and v2 both Available
📸 Screenshot: S3 Hive-style partition path with both Parquet files
📸 Screenshot: Terminal showing merged read with NaN for v1 rows
📸 Screenshot: Athena query comparison — WITH vs WITHOUT partition filter

---

## 2. CLI Verification (PowerShell)

```powershell
Write-Host "=== SCHEMA EVOLUTION VERIFICATION ===" -ForegroundColor Cyan

# Registry
aws glue get-registry --registry-id "RegistryName=$REGISTRY" `
  --query "{Name:RegistryName,Status:Status}"
# Expected: Status=AVAILABLE

# Schema + versions
aws glue get-schema `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "{Versions:LatestSchemaVersion,Compat:Compatibility,Status:SchemaStatus}"
# Expected: Versions=2, Compat=BACKWARD, Status=AVAILABLE

aws glue list-schema-versions `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "SchemaVersions[*].{V:VersionNumber,S:Status}"
# Expected: [{"V":1,"S":"AVAILABLE"},{"V":2,"S":"AVAILABLE"}]

# Verify v2 has new nullable fields
$V2_DEF = aws glue get-schema-version `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --schema-version-number "VersionNumber=2" `
  --query "SchemaDefinition" --output text
Write-Host "v2 has product: $(if ($V2_DEF -match 'product') {'✅'} else {'❌'})"
Write-Host "v2 has discount_pct: $(if ($V2_DEF -match 'discount_pct') {'✅'} else {'❌'})"
Write-Host "v2 uses null union: $(if ($V2_DEF -match '\"null\"') {'✅'} else {'❌'})"

# S3 files
aws s3 ls "s3://$BUCKET/schema-demo/year=2024/month=01/"
# Expected: v1_orders.parquet and v2_orders.parquet listed

# Glue table
aws glue get-table --database-name $DB_NAME --name $TABLE `
  --query "Table.Parameters.{'proj.enabled':'projection.enabled','yr.range':'projection.year.range'}"
# Expected: {"proj.enabled": "true", "yr.range": "2023,2030"}

# Python demo
$env:DATA_LAKE_BUCKET = $BUCKET
python src\validate_orders.py 2>$null
python src\schema_evolution_demo.py
# Expected: 5 rows total, v1 rows show NaN

Write-Host "=== COMPLETE ===" -ForegroundColor Green
```

---

## 3. Schema Compatibility Test

```powershell
# Manually verify v2 is BACKWARD compatible with v1
python -c "
import json

v1_schema_fields = {'order_id','customer_id','amount','order_date'}
v2_schema_def = json.loads('''
{\"type\":\"record\",\"name\":\"Order\",\"fields\":[
  {\"name\":\"order_id\",\"type\":\"string\"},
  {\"name\":\"customer_id\",\"type\":\"string\"},
  {\"name\":\"amount\",\"type\":\"double\"},
  {\"name\":\"order_date\",\"type\":\"string\"},
  {\"name\":\"product\",\"type\":[\"null\",\"string\"],\"default\":null},
  {\"name\":\"discount_pct\",\"type\":[\"null\",\"double\"],\"default\":null}
]}''')

# BACKWARD compat check: v1 consumer can read v2 data
# All new fields must have defaults
for f in v2_schema_def['fields']:
    if f['name'] not in v1_schema_fields:
        assert 'default' in f, f'Field {f[\"name\"]} has no default!'
        assert isinstance(f['type'], list) and 'null' in f['type'], \
               f'Field {f[\"name\"]} is not nullable!'
        print(f'  ✅ New field {f[\"name\"]}: nullable with default={f[\"default\"]}')

print('✅ Schema v2 is BACKWARD compatible with v1')
"
```

---

## 4. Partition Pruning Performance Test

```powershell
# Compare Athena data scanned with vs without partition filter
Write-Host "=== PARTITION PRUNING PERFORMANCE TEST ===" -ForegroundColor Cyan

# First add some sample data to S3 for realistic comparison
python -c "
import pandas as pd, pyarrow as pa, pyarrow.parquet as pq, s3fs, os
fs = s3fs.S3FileSystem()
bucket = os.environ.get('DATA_LAKE_BUCKET','')
for year in [2024]:
  for month in [1,2,3]:
    for day in [1,15]:
      df = pd.DataFrame({'order_id':[f'ORD-{year}{month:02d}{day:02d}'],'customer_id':['C1'],'amount':[29.99],'order_date':[f'{year}-{month:02d}-{day:02d}'],'product':['Widget A']})
      path = f'{bucket}/processed/orders/year={year}/month={month:02d}/day={day:02d}/part-00001.parquet'
      pq.write_table(pa.Table.from_pandas(df), path, filesystem=fs)
print('Sample data written to 6 partitions')
"

# Now compare
$Q1 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE} WHERE year=2024 AND month=1" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q1
$S1 = aws athena get-query-execution --query-execution-id $Q1 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "WITH year=2024 AND month=1: $S1 bytes scanned"

$Q2 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE}" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q2
$S2 = aws athena get-query-execution --query-execution-id $Q2 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "WITHOUT filter: $S2 bytes scanned"

if ([long]$S2 -gt 0) {
  $pct = [math]::Round((1 - [long]$S1/[long]$S2) * 100, 1)
  Write-Host "✅ Partition pruning saves: $pct% of data scanned"
}
```

---

## 5. Expected Successful Outputs

**Schema demo terminal:**
```
Writing v1 schema data...
  v1 schema: ['order_id', 'customer_id', 'amount', 'order_date']
Writing v2 schema data (new columns added)...
  v2 schema: ['order_id', 'customer_id', 'amount', 'order_date', 'product', 'discount_pct']
Reading merged schema (v1 + v2 files)...
  Merged columns: ['order_id', 'customer_id', 'amount', 'order_date', 'product', 'discount_pct']
  Total rows: 5
  v1 rows have NaN for new columns:
  order_id product  discount_pct
  ORD-001    NaN           NaN
  ORD-004  Widget A        0.0
Done! Check S3 for the Parquet files.
```

**Schema Registry CLI:**
```
[{"V": 1, "S": "AVAILABLE"}, {"V": 2, "S": "AVAILABLE"}]
```

**Partition pruning:**
```
WITH year=2024 AND month=1: 1,234 bytes scanned
WITHOUT filter:             24,680 bytes scanned
Savings: 95.0%
```

---

## 6. Verification Checklist

- [ ] `python src/schema_evolution_demo.py` runs without errors
- [ ] Output shows 5 rows with merged schema (3 v1 + 2 v2)
- [ ] v1 rows have `NaN` for `product` and `discount_pct`
- [ ] v2 rows have actual values for `product` and `discount_pct`
- [ ] S3 has `schema-demo/year=2024/month=01/v1_orders.parquet`
- [ ] S3 has `schema-demo/year=2024/month=01/v2_orders.parquet`
- [ ] Glue registry `handson-registry` Status = AVAILABLE
- [ ] Schema `orders-schema` has v1 Available
- [ ] Schema `orders-schema` has v2 Available (BACKWARD compatible)
- [ ] v2 definition uses `["null","string"]` for new fields
- [ ] v2 new fields have `"default": null`
- [ ] Glue table `orders_partitioned` has `projection.enabled=true`
- [ ] Athena query WITH partition filter scans less data than without

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
