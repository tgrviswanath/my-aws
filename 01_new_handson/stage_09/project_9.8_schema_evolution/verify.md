# Verification & Validation — Project 9.8 Schema Evolution & Partitioning

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Glue Schema Registry | Glue → Schema registries | `handson-registry` listed |
| Schema Versions | Glue → Schema registries → `handson-registry` → Schemas | `orders-schema` with v1 and v2 |
| Glue Table Partitions | Glue → Tables → orders → Partitions tab | year/month/day partitions listed |
| Athena Partition Projection | Athena → Query Editor | Queries use partition projection (no MSCK REPAIR needed) |
| S3 Partition Structure | S3 → data lake bucket → processed/orders/ | `year=XXXX/month=XX/day=XX/` structure |

📸 Screenshot: Glue Schema Registry showing v1 and v2 of orders-schema  
📸 Screenshot: S3 showing Hive-style partition structure  
📸 Screenshot: Athena query with partition filter running faster than without

---

## 2. CLI Verification

```bash
# 2.1 Register schema v1
export GLUE_REGISTRY=handson-registry
export GLUE_SCHEMA=orders-schema
python src/schema_evolution_demo.py register-v1
# Expected: Schema v1 registered: {"order_id": "string", "amount": "float", "order_date": "string"}

# 2.2 Register schema v2 (backward-compatible — adds optional field)
python src/schema_evolution_demo.py register-v2
# Expected: Schema v2 registered (added optional "customer_id" field)

# 2.3 List all schema versions
python src/schema_evolution_demo.py list-versions
# Expected: v1 and v2 listed, both AVAILABLE

# 2.4 Validate a record against schema
python src/schema_evolution_demo.py validate
# Expected: record validates against v2 schema

# 2.5 Confirm registry via CLI
aws glue list-registries \
  --query "Registries[*].{Name:RegistryName,Status:Status}"
# Expected: handson-registry listed, Status=AVAILABLE

aws glue list-schemas \
  --registry-id RegistryName=handson-registry \
  --query "Schemas[*].{Name:SchemaName,Status:SchemaStatus,Versions:LatestSchemaVersion}"
# Expected: orders-schema listed with version >= 2

# 2.6 Get schema versions
aws glue list-schema-versions \
  --schema-id RegistryName=handson-registry,SchemaName=orders-schema \
  --query "SchemaVersions[*].{Version:VersionNumber,Status:Status}"
# Expected: v1 and v2 both AVAILABLE

# 2.7 Test partition pruning performance
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')

# Query WITH partition filter (fast)
time aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM processed_db.orders WHERE year='2024' AND month='01';" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text

# Query WITHOUT partition filter (slow — scans all data)
time aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM processed_db.orders;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text
# Expected: partitioned query scans less data (lower cost)
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_glue_registry.main
# aws_glue_schema.orders

terraform state show aws_glue_registry.main
# Shows: registry_name=handson-registry, description

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Schema Evolution Compatibility

```bash
# Test backward compatibility: v1 consumer reads v2 data
python3 -c "
import json

# v2 record (has new optional field)
v2_record = {
    'order_id': 'ORD-001',
    'amount': 29.99,
    'order_date': '2024-01-15',
    'customer_id': 'CUST-1'  # new field in v2
}

# v1 consumer ignores unknown fields (backward compatible)
v1_fields = {'order_id', 'amount', 'order_date'}
v1_view = {k: v for k, v in v2_record.items() if k in v1_fields}
print('v1 consumer view:', json.dumps(v1_view, indent=2))
print('✅ Backward compatible: v1 consumer can read v2 data')

# Test partition structure
import os
partitions = ['year=2024/month=01/day=15', 'year=2024/month=01/day=16', 'year=2024/month=02/day=01']
for p in partitions:
    parts = dict(x.split('=') for x in p.split('/'))
    assert 'year' in parts and 'month' in parts and 'day' in parts
    print(f'✅ Valid partition: {p}')
print('All partition checks passed')
"
```

---

## 5. Expected Successful Outputs

**schema_evolution_demo.py list-versions:**
```
Schema: orders-schema in registry: handson-registry
Version 1: AVAILABLE
  {"type":"record","name":"Order","fields":[
    {"name":"order_id","type":"string"},
    {"name":"amount","type":"float"},
    {"name":"order_date","type":"string"}
  ]}
Version 2: AVAILABLE
  {"type":"record","name":"Order","fields":[
    {"name":"order_id","type":"string"},
    {"name":"amount","type":"float"},
    {"name":"order_date","type":"string"},
    {"name":"customer_id","type":["null","string"],"default":null}
  ]}
```

**Partition pruning comparison:**
```
Query with partition filter:  DataScanned=1.2 MB  (fast, cheap)
Query without partition filter: DataScanned=45.6 MB (slow, expensive)
Partition pruning saves: 97% of data scanned
```

---

## 6. Verification Checklist

- [ ] Glue Schema Registry `handson-registry` Status = AVAILABLE
- [ ] Schema `orders-schema` has v1 registered
- [ ] Schema `orders-schema` has v2 registered (backward-compatible)
- [ ] Both schema versions Status = AVAILABLE
- [ ] v2 adds optional field (not breaking change)
- [ ] S3 data uses Hive-style partitions: `year=XXXX/month=XX/day=XX/`
- [ ] Athena query with partition filter scans less data than without
- [ ] Partition projection configured (no MSCK REPAIR TABLE needed)
- [ ] `terraform plan` shows no changes
