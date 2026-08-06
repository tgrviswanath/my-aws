# Project 9.8 — Schema Evolution & Partitioning
# Console UI Steps (Improved Template Format)
# Registry: handson-registry | Schema: orders-schema | Table: orders_partitioned

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateRegistry`, `glue:CreateSchema`, `s3:PutObject`
- ✅ Services enabled: AWS Glue, S3, Athena — all in us-east-1
- ✅ Region: us-east-1 selected
- ✅ Python deps: `pip install boto3 pyarrow pandas s3fs`

**Step 0.1: Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → **US East (N. Virginia) us-east-1**

**📸 Screenshot P0:** Console with us-east-1 selected

---

### STEP 1 — Create Glue Schema Registry

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateRegistry`
- ✅ Services enabled: AWS Glue (Schema Registry)
- ✅ Region availability: Schema Registry in us-east-1

**Step 1.1: Navigate and Verify**
1. Search bar → **AWS Glue** → click it
2. Left sidebar → scroll down to **Schema Registry** section → click **Registries**
3. **Expected View:** Registries list (empty if first time)
4. Click **Add registry**

**📸 Screenshot 1a:** Glue → Schema Registry → Registries (empty list)

**Step 1.2: Make Selections**

**Decision Point 1:** Registry scope
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| One registry per team | Organized, searchable | ✅ `handson-registry` |
| One registry per schema type | Fine-grained | ❌ Overkill for learning |

**Step 1.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Registry name | `handson-registry` | Matches terraform/main.tf |
| Description | `Schema registry for handson data streams` | Clear purpose |
| Tags | Project=handson | Cost tracking |

**Step 1.4: Validate Result**
1. Click **Add registry**
2. **Expected Outcome:** `handson-registry` Status = **Available**

**Troubleshooting:**
- "Registry name already exists": Delete existing or use different name
- "Access denied": IAM user needs `glue:CreateRegistry`

**📸 Screenshot 1b:** Registry `handson-registry` Status = Available

---

### STEP 2 — Create Schema v1 (Initial Schema)

**Prerequisites Check:**
- ✅ Registry `handson-registry` Available
- ✅ Required permissions: `glue:CreateSchema`

**Step 2.1: Navigate and Verify**
1. Click on `handson-registry`
2. **Expected View:** Schemas list (empty)
3. Click **Add schema**

**Step 2.2: Make Selections — Data Format**

**Decision Point 1:** Schema format
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **AVRO** | Event streaming, strict typing | ✅ Industry standard |
| JSON | Flexible, simpler | ❌ Less strict |
| Protobuf | High performance binary | ❌ Complex tooling |

1. Select **AVRO**

**Decision Point 2:** Compatibility mode
| Mode | Effect | For This Project |
|------|--------|-----------------|
| **BACKWARD** | New schema reads old data safely | ✅ Old consumers unaffected |
| FORWARD | Old schema reads new data | ❌ More restrictive |
| NONE | No validation | ❌ Dangerous |

2. Select **BACKWARD**

**Step 2.3: Configure Schema Details**

| Field | Value |
|-------|-------|
| Schema name | `orders-schema` |
| Data format | AVRO |
| Compatibility | BACKWARD |
| Description | `Orders event schema v1 — initial 4 fields` |

**Step 2.4: Enter v1 Schema Definition**

Paste into the schema definition box:

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "handson.orders",
  "fields": [
    {"name": "order_id",    "type": "string"},
    {"name": "customer_id", "type": "string"},
    {"name": "amount",      "type": "double"},
    {"name": "order_date",  "type": "string"}
  ]
}
```

**Step 2.5: Validate Result**
1. Click **Create schema and version**
2. **Expected Outcome:** `orders-schema` Version 1 = **Available**

**📸 Screenshot 2a:** Schema `orders-schema` v1 Available with 4 fields

---

### STEP 3 — Register v2 Schema (Evolution — Add Nullable Fields)

**Prerequisites Check:**
- ✅ Schema `orders-schema` v1 exists and Available
- ✅ Understanding: BACKWARD compat = new fields must be nullable with defaults

**Step 3.1: Navigate and Verify**
1. Click on `orders-schema`
2. **Expected View:** Versions list — Version 1 AVAILABLE
3. Click **Register new version** or **Add version**

**📸 Screenshot 3a:** Schema versions list showing v1

**Step 3.2: Make Selections**

**Decision Point 1:** Field type for new fields
| Type | Breaking? | For This Project |
|------|-----------|-----------------|
| `"type": "string"` | ✅ BREAKING — no default | ❌ Old consumers crash |
| `"type": ["null","string"],"default":null` | ❌ Safe | ✅ Old consumers get null |

1. **Must use** union type `["null","string"]` for all new fields

**Step 3.3: Enter v2 Schema Definition**

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "handson.orders",
  "fields": [
    {"name": "order_id",     "type": "string"},
    {"name": "customer_id",  "type": "string"},
    {"name": "amount",       "type": "double"},
    {"name": "order_date",   "type": "string"},
    {"name": "product",      "type": ["null", "string"], "default": null},
    {"name": "discount_pct", "type": ["null", "double"], "default": null}
  ]
}
```

Why `["null", "string"]` for the two new fields:
- `null` listed FIRST — required for Avro BACKWARD compatibility
- `"default": null` — old producers don't set this field, defaults to null
- Old consumers reading v2 data: see null for new fields (safe, expected)

**Step 3.4: Validate Result**
1. Click **Register version**
2. **Expected Outcome:**
   - Compatibility check: **PASSED** (green message)
   - Version 2 Status = **Available**
   - Schema now shows 2 versions

**Troubleshooting:**
- "Schema not backward compatible": New field missing `"default":null` or not using union type
- "Invalid JSON": Check for missing commas/brackets in the schema definition

**📸 Screenshot 3b:** Schema `orders-schema` showing v1 AND v2 both Available

---

### STEP 4 — Run Python Demo (Local — No Cost)

**Step 4.1: Run Demo Script**
```powershell
$env:DATA_LAKE_BUCKET = "handson-data-lake-YOUR_ACCOUNT_ID"
python src\schema_evolution_demo.py
```

**Expected Output:**
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
  ORD-002    NaN           NaN
  ORD-004  Widget A        0.0
Done! Check S3 for the Parquet files.
```

**What to observe:**
- v1 rows (ORD-001 to ORD-003) show `NaN` for `product` and `discount_pct`
- v2 rows (ORD-004, ORD-005) have actual values
- Both sets of rows are readable together — no errors

**📸 Screenshot 4a:** Terminal showing merged read with NaN for v1 rows

---

### STEP 5 — Verify S3 Partition Structure

**Step 5.1: Navigate to S3 Files**
1. Search → **S3** → your data lake bucket
2. Navigate to `schema-demo/year=2024/month=01/`
3. **Expected View:** Two files:
   - `v1_orders.parquet`
   - `v2_orders.parquet`

**📸 Screenshot 5a:** S3 showing v1 and v2 Parquet in Hive partition path

---

### STEP 6 — Create Glue Table with Partition Projection

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateDatabase`, `glue:CreateTable`
- ✅ S3 data with partitioned structure exists

**Step 6.1: Create Database**
1. Glue → **Databases** → **Add database**
2. Database name: `handson_schema_demo`
3. Location: `s3://YOUR_BUCKET/processed/orders/`
4. Click **Create database**

**Step 6.2: Create Table**
1. Glue → **Tables** → **Add table** → **Add table manually**

| Field | Value |
|-------|-------|
| Table name | `orders_partitioned` |
| Database | `handson_schema_demo` |
| Table type | EXTERNAL_TABLE |
| Data store | S3 |
| S3 location | `s3://YOUR_BUCKET/processed/orders/` |
| Data format | Parquet |

**Step 6.3: Define Data Columns**

| Name | Type |
|------|------|
| order_id | string |
| customer_id | string |
| amount | double |
| order_date | date |
| product | string |

**Step 6.4: Define Partition Keys**

| Name | Type |
|------|------|
| year | int |
| month | int |
| day | int |

**Step 6.5: Add Partition Projection Properties**

After creating the table, click **Edit table** → **Table properties** → **Add property**:

| Key | Value |
|-----|-------|
| `projection.enabled` | `true` |
| `projection.year.type` | `integer` |
| `projection.year.range` | `2023,2030` |
| `projection.month.type` | `integer` |
| `projection.month.range` | `1,12` |
| `projection.month.digits` | `2` |
| `projection.day.type` | `integer` |
| `projection.day.range` | `1,31` |
| `projection.day.digits` | `2` |
| `storage.location.template` | `s3://BUCKET/processed/orders/year=${year}/month=${month}/day=${day}` |

Click **Apply** / **Save**

**Step 6.6: Validate Result**
**Expected Outcome:** Table has all 10 partition projection properties saved.

**📸 Screenshot 6a:** Glue table `orders_partitioned` with partition projection properties

---

### STEP 7 — Test Partition Pruning in Athena

**Step 7.1: Open Athena**
1. Search → **Athena** → **Query editor**
2. Database: `handson_schema_demo`
3. Workgroup: select yours (or `primary`)

**Step 7.2: Query WITH Partition Filter**
```sql
SELECT COUNT(*), ROUND(SUM(amount), 2) AS total
FROM orders_partitioned
WHERE year = 2024 AND month = 1;
```
After query: note **Data scanned** shown below results.

**Step 7.3: Query WITHOUT Partition Filter**
```sql
SELECT COUNT(*), ROUND(SUM(amount), 2) AS total
FROM orders_partitioned;
```
After query: note **Data scanned** — should be higher than Step 7.2.

**Step 7.4: Validate Result**
**Expected Outcome:** Query with filter scans less data than without filter.
With small demo data the difference may be small, but at scale it's dramatic (97–99%).

**📸 Screenshot 7a:** Athena — WITH filter, lower DataScanned shown
**📸 Screenshot 7b:** Athena — WITHOUT filter, higher DataScanned shown

---

### Console UI Summary

| Step | Action | Resource |
|------|--------|---------|
| Step 1 | Create Registry | `handson-registry` Available |
| Step 2 | Create v1 Schema | `orders-schema` v1 Available |
| Step 3 | Register v2 Schema | `orders-schema` v2 Available (BACKWARD compat) |
| Step 4 | Run Python demo | v1+v2 Parquet in S3, merged read with NaN |
| Step 5 | Verify S3 files | Hive-style partition path confirmed |
| Step 6 | Create Glue table | `orders_partitioned` with partition projection |
| Step 7 | Test Athena | Partition pruning saves data scanned |

### Screenshot Summary

| # | Description | Step |
|---|-------------|------|
| P0 | Console with us-east-1 | Phase 0 |
| 1a | Glue Registries empty list | Step 1.1 |
| 1b | Registry `handson-registry` Available | Step 1.4 |
| 2a | Schema v1 Available with 4 fields | Step 2.5 |
| 3a | Schema versions — v1 listed | Step 3.1 |
| 3b | Schema v1 + v2 both Available | Step 3.4 |
| 4a | Terminal: merged read with NaN for v1 rows | Step 4.1 |
| 5a | S3 Hive partition path with both files | Step 5.1 |
| 6a | Glue table with partition projection properties | Step 6.5 |
| 7a | Athena WITH filter — low DataScanned | Step 7.2 |
| 7b | Athena WITHOUT filter — higher DataScanned | Step 7.3 |

**Total: 11 screenshots for complete documentation**
