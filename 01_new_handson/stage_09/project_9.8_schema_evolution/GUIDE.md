# Complete Implementation Guide — Project 9.8: Schema Evolution & Partitioning
# AWS Glue Schema Registry + Parquet + Athena Partition Projection

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 2–3 hours
**Cost:** ~$0.03/month | **Glue Schema Registry: 10M schema versions free**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Concepts](#2-architecture--concepts)
3. [Prerequisites](#3-prerequisites)
4. [Project Folder Structure](#4-project-folder-structure)
5. [Hands-on Implementation](#5-hands-on-implementation)
   - [A. AWS Management Console Method](#5a-aws-management-console-method)
   - [B. AWS CLI Method](#5b-aws-cli-method)
6. [Code Deep Dive](#6-code-deep-dive)
7. [Verification & Validation](#7-verification--validation)
8. [Observations & Learning Notes](#8-observations--learning-notes)
9. [Screenshots Guidance](#9-screenshots-guidance)
10. [Cleanup Steps](#10-cleanup-steps)

---

## 1. Project Overview

### Project Title
**Schema Evolution, Partitioning Strategy, and Parquet Optimization on AWS**

### Business / Problem Statement

Your data pipeline has been running for 6 months. Now three real-world problems appear:

**Problem 1 — Schema Change:** The product team adds a `discount_pct` field to orders.
Your Parquet files already have 6 months of v1 data (no `discount_pct`). New files
will have it. When Athena queries both old and new files together, it crashes with
a schema mismatch error. How do you evolve the schema without reprocessing all historical data?

**Problem 2 — Slow Queries:** Your Athena query `SELECT * FROM orders WHERE order_date = '2024-01-15'`
scans 2 TB and takes 4 minutes. It costs $10 per query. Your analyst runs it 50 times per day.
The data doesn't change — why is it so slow and expensive?

**Problem 3 — Small Files:** Kinesis Firehose dumps hundreds of tiny 1 KB files every minute.
Athena opens each file individually. With 50,000 files, each query spends most of its time
on file-open overhead rather than actually reading data.

**Solutions this project teaches:**
- Schema evolution with Parquet (add columns safely)
- Glue Schema Registry (enforce schemas, version-track changes)
- Hive-style partitioning (year/month/day) for 100–10,000x query speedup
- Partition projection (Athena auto-discovers partitions, no manual `MSCK REPAIR TABLE`)
- File compaction (merge 50,000 small files into 50 large ones)

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════════════
 DEMO 1 — Schema Evolution (src/schema_evolution_demo.py)
═══════════════════════════════════════════════════════════════════════════

INPUT v1 (3 rows — original schema):
  order_id    STRING   "ORD-001", "ORD-002", "ORD-003"
  customer_id STRING   "C1", "C2", "C3"
  amount      FLOAT64  29.99, 49.99, 19.99
  order_date  DATE     2024-01-15, 2024-01-15, 2024-01-16

  → Writes to: s3://BUCKET/schema-demo/year=2024/month=01/v1_orders.parquet

INPUT v2 (2 rows — evolved schema, new nullable columns):
  order_id     STRING   "ORD-004", "ORD-005"
  customer_id  STRING   "C4", "C5"
  amount       FLOAT64  39.99, 59.99
  order_date   DATE     2024-01-17, 2024-01-17
  product      STRING   "Widget A", "Widget B"      ← NEW column
  discount_pct FLOAT64  0.0, 10.0                   ← NEW column

  → Writes to: s3://BUCKET/schema-demo/year=2024/month=01/v2_orders.parquet

OUTPUT — Merged read (both files together):
  Parquet auto-merges schemas. v1 rows get NaN for product/discount_pct.
  All 5 rows readable with the full v2 schema:

  order_id  customer_id  amount  order_date   product   discount_pct
  ORD-001   C1           29.99   2024-01-15   NaN       NaN          ← v1 row
  ORD-002   C2           49.99   2024-01-15   NaN       NaN          ← v1 row
  ORD-003   C3           19.99   2024-01-16   NaN       NaN          ← v1 row
  ORD-004   C4           39.99   2024-01-17   Widget A  0.0          ← v2 row
  ORD-005   C5           59.99   2024-01-17   Widget B  10.0         ← v2 row

═══════════════════════════════════════════════════════════════════════════
 DEMO 2 — Glue Schema Registry (CLI commands)
═══════════════════════════════════════════════════════════════════════════

INPUT: Schema definitions (AVRO format JSON strings)

v1 schema (initial):
  fields: order_id (string), customer_id (string), amount (double), order_date (string)

v2 schema (evolved — backward compatible):
  same as v1 PLUS: customer_id now optional with null default (["null","string"])

OUTPUT:
  Registry: handson-registry (Status = AVAILABLE)
  Schema:   orders-schema    (Compatibility = BACKWARD)
  Version 1: AVAILABLE (initial schema)
  Version 2: AVAILABLE (evolved — adds nullable field)

═══════════════════════════════════════════════════════════════════════════
 DEMO 3 — Partition Projection (Glue table with Athena)
═══════════════════════════════════════════════════════════════════════════

INPUT: S3 data with Hive-style partitions:
  s3://BUCKET/processed/orders/year=2024/month=01/day=15/part-00000.parquet
  s3://BUCKET/processed/orders/year=2024/month=01/day=16/part-00000.parquet
  s3://BUCKET/processed/orders/year=2024/month=02/day=01/part-00000.parquet

Glue table config (from terraform/main.tf):
  projection.enabled = true
  projection.year.range  = 2023,2030
  projection.month.range = 1,12
  projection.day.range   = 1,31

OUTPUT:
  Athena query: SELECT * FROM orders_partitioned WHERE year=2024 AND month=1
  → Scans ONLY year=2024/month=01/ partitions (not the full table)
  → Result: DataScanned = 1.2 MB (not 45 MB)
  → Cost: $0.000006 (not $0.000225)
  → Speed: 0.8 seconds (not 8 seconds)
  → NO manual MSCK REPAIR TABLE needed — partition projection handles it
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain what schema evolution is and why it's needed
- [ ] Safely add new nullable columns to Parquet files without breaking readers
- [ ] Understand why Parquet supports schema merging automatically
- [ ] Create a Glue Schema Registry and register schema versions
- [ ] Explain BACKWARD vs FORWARD vs FULL compatibility
- [ ] Register a v2 schema that is backward compatible with v1
- [ ] Design a Hive-style partition strategy for orders data
- [ ] Explain partition pruning and why it reduces query cost by 100–10,000x
- [ ] Configure partition projection on a Glue table (no MSCK REPAIR needed)
- [ ] Understand the small files problem and compaction solution
- [ ] Run the demo script and observe merged schema behavior

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│              SCHEMA EVOLUTION & PARTITIONING ARCHITECTURE               │
│                                                                         │
│  SCHEMA REGISTRY (enforce + version schemas)                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Glue Schema Registry: handson-registry                         │   │
│  │  Schema: orders-schema  |  Format: AVRO  |  Compat: BACKWARD   │   │
│  │                                                                  │   │
│  │  v1: {order_id, customer_id, amount, order_date}                │   │
│  │  v2: {order_id, customer_id, amount, order_date, product,       │   │
│  │        discount_pct}  ← 2 new nullable fields added safely      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  S3 STORAGE (Hive-style partitions)                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  s3://BUCKET/processed/orders/                                  │   │
│  │    year=2024/                                                    │   │
│  │      month=01/                                                   │   │
│  │        day=15/  part-00000.snappy.parquet  ← v1 schema          │   │
│  │        day=16/  part-00000.snappy.parquet  ← v1 schema          │   │
│  │      month=02/                                                   │   │
│  │        day=01/  part-00000.snappy.parquet  ← v2 schema          │   │
│  │                  (product + discount_pct columns added)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  GLUE CATALOG (Partition Projection)                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Table: handson_schema_demo.orders_partitioned                  │   │
│  │  projection.enabled = true                                       │   │
│  │  projection.year.range  = 2023,2030                             │   │
│  │  projection.month.range = 1,12                                  │   │
│  │  projection.day.range   = 1,31                                  │   │
│  │                                                                  │   │
│  │  Effect: Athena auto-knows all valid year/month/day combos      │   │
│  │  No manual: MSCK REPAIR TABLE orders                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ATHENA QUERIES (with partition pruning)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  WITH partition filter:    DataScanned = 1.2 MB  ← FAST/CHEAP  │   │
│  │    SELECT * FROM orders WHERE year=2024 AND month=1             │   │
│  │                                                                  │   │
│  │  WITHOUT partition filter: DataScanned = 45 MB   ← SLOW/COSTLY │   │
│  │    SELECT * FROM orders                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **AWS Glue Schema Registry** | Version and validate schemas (Avro/JSON/Protobuf) | ✅ 10M schema versions free |
| **Amazon S3** | Stores Parquet files with Hive-style partitions | ✅ 5 GB free |
| **AWS Glue Data Catalog** | Table definitions + partition projection config | ✅ 1M objects free |
| **Amazon Athena** | Queries partitioned Parquet data | ❌ $5/TB scanned |
│  │        day=15/  part-00000.snappy.parquet  ← v1 schema          │   │
│  │        day=16/  part-00000.snappy.parquet  ← v1 schema          │   │
│  │      month=02/                                                   │   │
│  │        day=01/  part-00000.snappy.parquet  ← v2 schema          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  GLUE CATALOG + ATHENA (Partition Projection)                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  projection.enabled=true | year range 2023-2030                 │   │
│  │  Athena auto-discovers partitions — no MSCK REPAIR needed       │   │
│  │  Query with filter: DataScanned=1.2 MB  ← 97% savings          │   │
│  │  Query without filter: DataScanned=45 MB                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts Explained

**Schema Evolution — the rules:**
```
SAFE (BACKWARD compatible — existing consumers keep working):
  ✅ Add a new NULLABLE field with a default value
  ✅ Delete a field that had a default value

UNSAFE (BREAKING — existing consumers will crash):
  ❌ Rename a field   (ORD_ID → order_id)
  ❌ Change field type (string → integer)
  ❌ Add a REQUIRED field with no default

Why nullable? A v1 consumer reading a v2 file sees the new field as null
(it uses the default). No code changes needed for old consumers.
Old v1 files read by v2 code also return null for the new field. Safe.
```

**Parquet Schema Merging:**
```
v1_orders.parquet schema: [order_id, customer_id, amount, order_date]
v2_orders.parquet schema: [order_id, customer_id, amount, order_date, product, discount_pct]

When you read BOTH files together:
  PyArrow union of schemas = [order_id, customer_id, amount, order_date, product, discount_pct]
  v1 rows: product=NaN, discount_pct=NaN  (missing columns filled with null)
  v2 rows: all 6 columns populated

This works because Parquet stores column names, not just positions.
It's safe to have different files with different column sets in the same dataset.
```

**Partition Pruning — the core concept:**
```
Without partitions (flat storage):
  s3://bucket/orders/2024-01-15-part-001.parquet
  s3://bucket/orders/2024-01-16-part-001.parquet
  ... (365 files per year)

  Query: SELECT * FROM orders WHERE order_date='2024-01-15'
  Athena: must read ALL files to find matching rows → slow + expensive

With Hive-style partitions:
  s3://bucket/orders/year=2024/month=01/day=15/part-001.parquet
  s3://bucket/orders/year=2024/month=01/day=16/part-001.parquet

  Query: SELECT * FROM orders WHERE year=2024 AND month=1 AND day=15
  Athena: reads ONLY year=2024/month=01/day=15/ → 99% less data scanned
```

**MSCK REPAIR TABLE vs Partition Projection:**
```
Traditional workflow (tedious):
  1. Add new partition to S3: s3://bucket/orders/year=2024/month=03/day=01/
  2. Run: MSCK REPAIR TABLE orders;   ← must run manually every day!
  3. Now Athena can query the new partition

Partition projection (this project — automatic):
  1. Add new partition to S3
  2. Done. Athena automatically knows about it
  3. No manual step needed ever

How? The table config tells Athena all valid partition values:
  year: 2023–2030, month: 1–12, day: 1–31
  Athena generates all combinations and checks S3 for them automatically
```

**Small Files Problem:**
```
Kinesis Firehose default: flushes every 60 seconds
24 hours × 60 flushes/hour = 1,440 files per day
At 10 KB each = 14.4 MB total but 1,440 S3 API calls per Athena query

Compaction solution:
  1,440 × 10 KB files → 1 × 14.4 MB file
  Athena: 1 S3 API call (not 1,440) → 1,000x faster query start

Target file size: 128 MB – 1 GB per Parquet file
```

**Glue Schema Registry — Compatibility Modes:**
| Mode | Can Add | Can Remove | Can Change Type |
|------|---------|-----------|----------------|
| **BACKWARD** | ✅ nullable | ✅ with default | ❌ |
| FORWARD | ❌ | ❌ | ❌ |
| FULL | ✅ nullable | ✅ both ways | ❌ |
| NONE | anything | anything | anything (risky) |

### Best Practices Followed

- **BACKWARD compatibility** — existing consumers never break
- **Nullable new fields** — safe for both old and new readers
- **Hive-style partitions** — `year=YYYY/month=MM/day=DD` standard
- **Partition projection** — eliminates `MSCK REPAIR TABLE` manual step
- **128 MB+ target file size** — avoids small files problem
- **Snappy compression** — good balance of speed/size for Parquet
- **Never rename columns** — add new ones with better names alongside old ones

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia)
- S3 bucket with Parquet data (from Projects 9.1–9.2)
- Glue Data Catalog with `handson_data_lake` database

### 3.2 IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:CreateRegistry","glue:DeleteRegistry","glue:GetRegistry","glue:ListRegistries",
        "glue:CreateSchema","glue:DeleteSchema","glue:GetSchema","glue:ListSchemas",
        "glue:RegisterSchemaVersion","glue:ListSchemaVersions","glue:GetSchemaVersion",
        "glue:CreateDatabase","glue:CreateTable","glue:GetTable","glue:DeleteTable",
        "glue:GetDatabase","glue:DeleteDatabase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket","s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET","arn:aws:s3:::YOUR_BUCKET/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["athena:StartQueryExecution","athena:GetQueryExecution",
                 "athena:GetQueryResults","athena:ListWorkGroups"],
      "Resource": "*"
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) |
|------|---------|------------------|
| Python | >= 3.9 | `winget install Python.Python.3.11` |
| boto3 | latest | `pip install boto3` |
| pyarrow | latest | `pip install pyarrow` |
| pandas | latest | `pip install pandas` |
| s3fs | latest | `pip install s3fs` |
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |

### 3.4 Environment Variables (PowerShell)

```powershell
$env:AWS_REGION       = "us-east-1"
$env:ACCOUNT          = aws sts get-caller-identity --query Account --output text
$env:DATA_LAKE_BUCKET = "handson-data-lake-$env:ACCOUNT"
$env:GLUE_REGISTRY    = "handson-registry"
$env:GLUE_SCHEMA      = "orders-schema"

aws sts get-caller-identity
```

### 3.5 Estimated AWS Cost

| Resource | Cost |
|----------|------|
| Glue Schema Registry (< 10M versions/month) | **$0** (free tier) |
| S3 Parquet files (< 5 GB) | **$0** (free tier) |
| Glue Data Catalog (< 1M objects) | **$0** (free tier) |
| Athena (demo queries, < 1 GB scanned) | ~$0.005 |
| **Total** | **~$0.01** |

> **Nearly free** — Schema Registry and Glue Catalog are within free tier.
> Athena is the only real cost and is tiny for demo-scale data.

---

## 4. Project Folder Structure

```
project_9.8_schema_evolution/
│
├── GUIDE.md                    ← This comprehensive guide (you are here)
├── README.md                   ← Quick start and key concepts
├── steps.md                    ← CLI commands reference (PowerShell)
├── steps_awsconsoleui.md       ← Console UI steps (improved template)
├── verify.md                   ← Verification checklist + commands
├── cost_estimate.md            ← Cost breakdown with free tier details
│
├── src/
│   └── schema_evolution_demo.py  ← Python demo: writes v1+v2 Parquet to S3,
│                                    reads merged schema, shows partition pruning
│
├── docs/
│   └── architecture.md           ← Schema evolution rules, partition concepts
│
└── terraform/
    └── main.tf                   ← Glue registry + schema + Glue table with
                                     partition projection (reference — not in this guide)
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `src/schema_evolution_demo.py` | Writes v1 (4 cols) and v2 (6 cols) Parquet to S3, reads both together showing merged schema. Shows partition pruning cost comparison. |
| `docs/architecture.md` | Schema evolution compatibility rules, partition strategies, small files problem |
| `terraform/main.tf` | Glue Schema Registry (`handson-registry`) + schema (`orders-schema` v1) + Glue table with partition projection |

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> The Python demo script runs locally. Console steps cover Glue Schema Registry,
> Glue Catalog table with partition projection, and Athena query verification.

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateRegistry`, `glue:CreateSchema`, `s3:PutObject`
- ✅ Services enabled: AWS Glue, S3, Athena — all in us-east-1
- ✅ Region: us-east-1 selected

**Step 0.1: Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**

**Step 0.2: Install Python Dependencies**
```powershell
pip install boto3 pyarrow pandas s3fs
```

**📸 Screenshot P0:** AWS Console with us-east-1 selected

---

#### Step 1 — Create Glue Schema Registry

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateRegistry`
- ✅ Services enabled: AWS Glue (Schema Registry feature)
- ✅ Region availability: Schema Registry available in us-east-1

**Step 1.1: Navigate and Verify**
1. Search bar → **AWS Glue** → click it
2. Left sidebar → scroll down to **Schema Registry** section → click **Registries**
3. **Expected View:** Registries list (empty initially)
4. Click **Add registry** (orange button)

**📸 Screenshot 1a:** Glue Registries list before creation

**Step 1.2: Make Selections — Registry Purpose**

**Decision Point 1:** Registry naming strategy
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Generic name | Simple projects | ❌ Not descriptive |
| **Project-prefixed** | Consistent naming | ✅ `handson-registry` |

**Step 1.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Registry name | `handson-registry` | Matches terraform/main.tf |
| Description | `Schema registry for handson data streams` | Clear purpose |
| Tags | Project=handson | Cost tracking |

**Step 1.4: Create and Validate**
1. Click **Add registry**
2. **Expected Outcome:** Registry listed with Status = **Available**

**Troubleshooting:**
- "Registry already exists": Delete the existing one first or use a different name
- "AccessDenied": IAM user needs `glue:CreateRegistry`

**📸 Screenshot 1b:** Registry `handson-registry` Status = **Available**

---

#### Step 2 — Create Schema (v1) in Registry

**Prerequisites Check:**
- ✅ Registry `handson-registry` Status = Available
- ✅ Required permissions: `glue:CreateSchema`

**Step 2.1: Navigate and Verify**
1. Click on registry name `handson-registry`
2. **Expected View:** Schemas list (empty initially)
3. Click **Add schema** (orange button)

**Step 2.2: Make Selections — Data Format**

**Decision Point 1:** Schema data format
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **AVRO** | Streaming data, Kafka, Kinesis | ✅ Industry standard for event schemas |
| JSON | Flexible, human-readable | ❌ Less strict type system |
| Protobuf | High-performance binary | ❌ More complex tooling |

1. Select **AVRO**

**Step 2.3: Configure Schema Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Schema name | `orders-schema` | Matches terraform/main.tf |
| Data format | AVRO | Chosen above |
| Compatibility | **BACKWARD** | Old consumers can read new data |
| Description | `Orders event schema — BACKWARD compatible` | |

**Decision Point 2:** Compatibility mode
| Mode | Meaning | For This Project |
|------|---------|-----------------|
| **BACKWARD** | New schema can read old data | ✅ Old consumers keep working |
| FORWARD | Old schema can read new data | ❌ Less common |
| FULL | Both directions | ✅ Safest but most restrictive |
| NONE | No validation | ❌ Dangerous in production |

**Step 2.4: Enter v1 Schema Definition**

In the **Schema definition** text box, paste:

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

**Field explanations:**
| Field | Type | Why |
|-------|------|-----|
| `order_id` | string | Primary key — always string in Avro |
| `customer_id` | string | Foreign key |
| `amount` | double | 64-bit precision for money |
| `order_date` | string | YYYY-MM-DD stored as string in Avro |

**Step 2.5: Create and Validate**
1. Click **Create schema and version**
2. **Expected Outcome:** Schema `orders-schema` listed with 1 version, Status = **Available**

**📸 Screenshot 2a:** Schema `orders-schema` v1 created and Available

---

#### Step 3 — Register v2 Schema (Schema Evolution)

**Prerequisites Check:**
- ✅ Schema `orders-schema` v1 exists and is Available
- ✅ Understanding: v2 must be BACKWARD compatible (only add nullable fields)

**Step 3.1: Navigate to Schema**
1. Click on `orders-schema`
2. **Expected View:** Schema versions list showing v1 = AVAILABLE
3. Click **Register new version** (or **Add new version**)

**Step 3.2: Enter v2 Schema Definition**

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

**Why `["null", "string"]` not just `"string"` for new fields:**
- `"string"` = required field — BREAKS old consumers (they have no value for it)
- `["null", "string"]` = union type — either null or string, with default=null
- Old consumers: get null (safe, expected)
- New consumers: get the actual value or null if not provided
- This is the key to BACKWARD compatibility

**Step 3.3: Validate and Register**
1. Click **Register version**
2. **Expected Outcome:**
   - Compatibility check runs automatically
   - v2 shows as AVAILABLE
   - `orders-schema` now shows 2 versions

**Troubleshooting:**
- "Schema not backward compatible": The v2 schema has a breaking change. Check:
  - Did you use `["null","string"]` not `"string"` for new fields?
  - Did you accidentally rename or remove a field?
- "Invalid Avro schema": JSON syntax error — validate at json.schemastore.org

**📸 Screenshot 3a:** Schema `orders-schema` with v1 and v2 both Available

---

#### Step 4 — Run the Python Demo Locally

**Prerequisites Check:**
- ✅ Python dependencies installed: `pip install boto3 pyarrow pandas s3fs`
- ✅ AWS credentials configured
- ✅ S3 data lake bucket exists

**Step 4.1: Set Environment and Run**

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
  ORD-003    NaN           NaN
  ORD-004  Widget A        0.0
  ORD-005  Widget B       10.0

=== Partition Pruning Demo ===
[cost comparison printed]

Done! Check S3 for the Parquet files.
```

**📸 Screenshot 4a:** Terminal showing merged schema output with NaN for v1 rows

---

#### Step 5 — Verify S3 Partition Structure

**Step 5.1: Navigate to S3**
1. Search → **S3** → your data lake bucket
2. Navigate to `schema-demo/year=2024/month=01/`
3. **Expected View:** Two files:
   - `v1_orders.parquet`
   - `v2_orders.parquet`

**📸 Screenshot 5a:** S3 showing v1 and v2 Parquet files in partitioned path

---

#### Step 6 — Create Glue Table with Partition Projection

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateDatabase`, `glue:CreateTable`
- ✅ S3 data exists with `year=YYYY/month=MM/day=DD/` partitions

**Step 6.1: Create Database**
1. Glue → **Databases** → **Add database**
2. Database name: `handson_schema_demo`
3. Click **Create database**

**Step 6.2: Create Table Manually**
1. Glue → **Tables** → **Add table** → **Add table manually**
2. Table name: `orders_partitioned`
3. Database: `handson_schema_demo`
4. S3 location: `s3://YOUR_BUCKET/processed/orders/`

**Step 6.3: Define Columns**

| Column name | Data type |
|-------------|-----------|
| order_id | string |
| customer_id | string |
| amount | double |
| order_date | date |
| product | string |

**Step 6.4: Define Partition Keys**

| Partition key | Data type |
|--------------|-----------|
| year | int |
| month | int |
| day | int |

**Step 6.5: Configure Partition Projection (Table Properties)**

After table creation, click **Edit table** → scroll to **Table properties** → add these key-value pairs:

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
| `storage.location.template` | `s3://YOUR_BUCKET/processed/orders/year=${year}/month=${month}/day=${day}` |

**Step 6.6: Validate**
**Expected Outcome:** Table `orders_partitioned` with partition projection properties saved.
When queried in Athena with `WHERE year=2024 AND month=1`, no `MSCK REPAIR TABLE` needed.

**📸 Screenshot 6a:** Glue table `orders_partitioned` with partition projection properties

---

#### Step 7 — Query in Athena to See Partition Pruning

**Step 7.1: Open Athena**
1. Search → **Athena** → Query editor
2. Database: `handson_schema_demo`

**Step 7.2: Query WITH Partition Filter**
```sql
SELECT COUNT(*), SUM(amount)
FROM orders_partitioned
WHERE year=2024 AND month=1;
```
Note the **Data scanned** value shown after query completes.

**Step 7.3: Query WITHOUT Partition Filter**
```sql
SELECT COUNT(*), SUM(amount)
FROM orders_partitioned;
```
Note the **Data scanned** value — should be significantly higher.

**Expected Observation:**
- With filter: scans only Jan 2024 partition (KB range)
- Without filter: scans all partitions (much more data)

**📸 Screenshot 7a:** Athena showing "Data scanned" for partitioned vs full-table query

---

## 5B. AWS CLI Method

### Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.8_schema_evolution

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$BUCKET    = "handson-data-lake-$ACCOUNT"
$REGISTRY  = "handson-registry"
$SCHEMA    = "orders-schema"
$DB_NAME   = "handson_schema_demo"
$TABLE     = "orders_partitioned"

Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
```

---

### Phase 1 — Run Python Demo (Schema Evolution)

```powershell
pip install boto3 pyarrow pandas s3fs

$env:DATA_LAKE_BUCKET = $BUCKET
python src\schema_evolution_demo.py

# Expected output:
# Writing v1 schema data...   (3 rows, 4 columns)
# Writing v2 schema data...   (2 rows, 6 columns)
# Reading merged schema...    (5 rows total, NaN for v1 new cols)
# Partition Pruning Demo...   (cost comparison)

# Verify files in S3
aws s3 ls "s3://$BUCKET/schema-demo/" --recursive
# Expected:
# schema-demo/year=2024/month=01/v1_orders.parquet
# schema-demo/year=2024/month=01/v2_orders.parquet
```

---

### Phase 2 — Create Glue Schema Registry

```powershell
# Create registry
aws glue create-registry `
  --registry-name $REGISTRY `
  --description "Schema registry for handson data streams"

# Verify
aws glue get-registry `
  --registry-id "RegistryName=$REGISTRY" `
  --query "Status"
# Expected: AVAILABLE

Write-Host "✅ Registry created: $REGISTRY"
```

---

### Phase 3 — Register v1 Schema

```powershell
# v1 schema definition (4 fields)
$V1_SCHEMA = '{"type":"record","name":"Order","namespace":"handson.orders","fields":[{"name":"order_id","type":"string"},{"name":"customer_id","type":"string"},{"name":"amount","type":"double"},{"name":"order_date","type":"string"}]}'

aws glue create-schema `
  --registry-id "RegistryName=$REGISTRY" `
  --schema-name $SCHEMA `
  --data-format AVRO `
  --compatibility BACKWARD `
  --description "Orders event schema v1 — initial schema" `
  --schema-definition $V1_SCHEMA

# Expected output:
# { "SchemaName": "orders-schema", "SchemaStatus": "AVAILABLE",
#   "LatestSchemaVersion": 1, "DataFormat": "AVRO", "Compatibility": "BACKWARD" }

# Verify v1
aws glue get-schema `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "{Name:SchemaName,Status:SchemaStatus,Version:LatestSchemaVersion,Compat:Compatibility}"
# Expected: Version=1, Status=AVAILABLE, Compat=BACKWARD
```

---

### Phase 4 — Register v2 Schema (Evolution)

```powershell
# v2 schema: adds 2 new NULLABLE fields (BACKWARD compatible)
# Key: new fields use ["null","type"] union, not just "type"
$V2_SCHEMA = '{"type":"record","name":"Order","namespace":"handson.orders","fields":[{"name":"order_id","type":"string"},{"name":"customer_id","type":"string"},{"name":"amount","type":"double"},{"name":"order_date","type":"string"},{"name":"product","type":["null","string"],"default":null},{"name":"discount_pct","type":["null","double"],"default":null}]}'

aws glue register-schema-version `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --schema-definition $V2_SCHEMA

# Expected: { "VersionNumber": 2, "Status": "AVAILABLE" }

# List all versions
aws glue list-schema-versions `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "SchemaVersions[*].{Version:VersionNumber,Status:Status}"
# Expected:
# [{"Version": 1, "Status": "AVAILABLE"}, {"Version": 2, "Status": "AVAILABLE"}]
```

---

### Phase 5 — Create Glue Database and Table with Partition Projection

```powershell
# Create Glue database
aws glue create-database `
  --database-input "Name=$DB_NAME,Description=Schema evolution demo database"

# Create Glue table with partition projection
$TABLE_INPUT = @"
{
  "Name": "$TABLE",
  "TableType": "EXTERNAL_TABLE",
  "Parameters": {
    "EXTERNAL": "TRUE",
    "projection.enabled": "true",
    "projection.year.type": "integer",
    "projection.year.range": "2023,2030",
    "projection.month.type": "integer",
    "projection.month.range": "1,12",
    "projection.month.digits": "2",
    "projection.day.type": "integer",
    "projection.day.range": "1,31",
    "projection.day.digits": "2",
    "storage.location.template": "s3://$BUCKET/processed/orders/year=`${year}/month=`${month}/day=`${day}"
  },
  "PartitionKeys": [
    {"Name":"year","Type":"int"},
    {"Name":"month","Type":"int"},
    {"Name":"day","Type":"int"}
  ],
  "StorageDescriptor": {
    "Location": "s3://$BUCKET/processed/orders/",
    "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
    "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
    "SerdeInfo": {
      "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
      "Parameters": {"serialization.format": "1"}
    },
    "Columns": [
      {"Name":"order_id","Type":"string"},
      {"Name":"customer_id","Type":"string"},
      {"Name":"amount","Type":"double"},
      {"Name":"order_date","Type":"date"},
      {"Name":"product","Type":"string"}
    ]
  }
}
"@

$TABLE_INPUT | Out-File "$env:TEMP\table.json" -Encoding utf8
aws glue create-table `
  --database-name $DB_NAME `
  --table-input "file://$env:TEMP\table.json"

Write-Host "✅ Table with partition projection created"

# Verify
aws glue get-table `
  --database-name $DB_NAME `
  --name $TABLE `
  --query "Table.Parameters.{ProjEnabled:'projection.enabled',YearRange:'projection.year.range'}"
# Expected: {"ProjEnabled": "true", "YearRange": "2023,2030"}
```

---

### Phase 6 — Test Partition Pruning in Athena

```powershell
$RESULTS_BUCKET = $BUCKET

# Query WITH partition filter (fast/cheap)
$Q1 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE} WHERE year=2024 AND month=1" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$RESULTS_BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text

aws athena wait query-execution-complete --query-execution-id $Q1

$STATS1 = aws athena get-query-execution --query-execution-id $Q1 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "WITH filter: DataScanned = $([math]::Round($STATS1/1024, 2)) KB"

# Query WITHOUT partition filter (scans all data)
$Q2 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE}" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$RESULTS_BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text

aws athena wait query-execution-complete --query-execution-id $Q2

$STATS2 = aws athena get-query-execution --query-execution-id $Q2 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "WITHOUT filter: DataScanned = $([math]::Round($STATS2/1024, 2)) KB"

$SAVING = [math]::Round((1 - $STATS1/$STATS2) * 100, 1)
Write-Host "Partition pruning saves: $SAVING% of data scanned"
# Expected: 90–99% savings depending on how many partitions exist
```

---

### Phase 7 — File Compaction Demo

```powershell
# Compact many small files into one large optimized Parquet file
python -c "
import s3fs, pyarrow.parquet as pq, pyarrow as pa, os

fs = s3fs.S3FileSystem()
bucket = os.environ.get('DATA_LAKE_BUCKET', 'handson-data-lake')

# Read all files from schema-demo (simulates many small files)
dataset = pq.ParquetDataset(f'{bucket}/schema-demo/', filesystem=fs)
table = dataset.read()
print(f'Total rows: {len(table)}')
print(f'Size before: {table.nbytes/1024:.1f} KB across multiple files')

# Write as one optimized Parquet file
output_path = f'{bucket}/schema-demo-compacted/orders_all.parquet'
pq.write_table(
    table,
    output_path,
    filesystem=fs,
    compression='snappy',
    row_group_size=128 * 1024 * 1024   # 128 MB row groups
)
print(f'Compacted to single file: s3://{output_path}')
"
```

---

## 6. Code Deep Dive

### `src/schema_evolution_demo.py` — Line by Line

```python
schema_v1 = pa.schema([
    pa.field("order_id",    pa.string()),
    pa.field("customer_id", pa.string()),
    pa.field("amount",      pa.float64()),
    pa.field("order_date",  pa.date32()),
])
```
- `pa.schema([...])` — explicit schema definition. Controls column names and types.
- `pa.float64()` — double precision float for amounts. `pa.float32()` would lose precision.
- `pa.date32()` — stores dates as 32-bit integers (days since epoch). Compact + sortable.
- Why define schema explicitly? If omitted, PyArrow infers from data. Safer to be explicit
  so downstream readers know exactly what to expect.

---

```python
schema_v2 = pa.schema([
    pa.field("order_id",     pa.string()),
    pa.field("customer_id",  pa.string()),
    pa.field("amount",       pa.float64()),
    pa.field("order_date",   pa.date32()),
    pa.field("product",      pa.string()),      # NEW — nullable
    pa.field("discount_pct", pa.float64()),     # NEW — nullable
])
```
- v2 extends v1 by adding two new fields at the END of the schema.
- Why at the end? Parquet stores columns by name not position.
  But appending is convention — easier for humans to track changes.
- Why these types? `pa.string()` for product name, `pa.float64()` for percentage.
- In production: mark new fields as `pa.field("product", pa.large_string(), nullable=True)`
  to make the nullable intent explicit.

---

```python
buf = io.BytesIO()
pq.write_table(table, buf, compression="snappy")
buf.seek(0)
s3.put_object(Bucket=S3_BUCKET, Key="schema-demo/.../v1_orders.parquet", Body=buf.getvalue())
```
- `io.BytesIO()` — in-memory buffer. Writes Parquet bytes to RAM, not a file.
- `pq.write_table(table, buf, compression="snappy")` — Snappy compression:
  fast compress/decompress, ~40% smaller than uncompressed. Good balance for Athena.
- `buf.seek(0)` — rewind buffer to start before reading it.
- `s3.put_object(...)` — single API call uploads the whole file. Fast for small files.
  For files > 100 MB: use `s3.upload_fileobj()` (multipart upload automatically).

---

```python
dataset = pq.ParquetDataset(
    f"{S3_BUCKET}/schema-demo/year=2024/month=01/",
    filesystem=fs,
    schema=None,   # auto-merge schemas
)
df = dataset.read_pandas().to_pandas()
```
- `pq.ParquetDataset(path, filesystem=s3fs)` — reads ALL Parquet files in the path.
  Discovers `v1_orders.parquet` and `v2_orders.parquet`.
- `schema=None` — auto-detects and MERGES schemas from all files.
  Result: union schema with all columns from all files.
- Missing columns filled with `null` / `NaN` for files that don't have them.
- This is the core of schema evolution — no code changes needed for v1 readers.

---

```python
def demonstrate_partition_pruning():
    print("""
Without partitioning:
  SELECT * FROM orders WHERE order_date = '2024-01-15'
  → Scans ALL data (e.g. 1 TB) → Cost: $5.00

With year/month/day partitioning:
  SELECT * FROM orders WHERE year=2024 AND month=01 AND day=15
  → Scans only that day (e.g. 100 MB) → Cost: $0.0005
  → 10,000x cheaper!
    """)
```
- This is a print-only demo function showing the concept.
- The actual cost savings come from the Athena workload in Phase 6.

### Common Mistakes and Fixes

| Mistake | Effect | Fix |
|---------|--------|-----|
| New required field (no default) | BREAKS v1 consumers | Use `["null","type"]` with `"default": null` |
| Rename a field | Old data unreadable | Add new field alongside old one |
| Partition by high-cardinality column | Too many partitions (millions) | Use low-cardinality: year/month/day |
| Partition by user_id | S3 LIST timeout | Use business date instead |
| Forget `storage.location.template` in projection | Athena returns empty results | Add template pointing to correct S3 path |
| `MSCK REPAIR TABLE` on projected table | Error/no-op | Projection doesn't need repair |
| Small files (< 1 MB each) | Slow Athena queries | Compact to 128 MB–1 GB files |
| `compression="gzip"` for interactive | Slow decompression | Use `snappy` for Athena |

---

## 7. Verification & Validation

### 7.1 Local Demo Verification

```powershell
$env:DATA_LAKE_BUCKET = $BUCKET
python src\schema_evolution_demo.py

# Expected:
# Writing v1 schema data...
# Writing v2 schema data...
# Reading merged schema...
#   Merged columns: ['order_id', 'customer_id', 'amount', 'order_date', 'product', 'discount_pct']
#   Total rows: 5
#   v1 rows show NaN for product and discount_pct
```

### 7.2 AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| Registry | Glue → Schema Registry → Registries | `handson-registry` Available |
| Schema v1 | Registry → `orders-schema` | Version 1 Available |
| Schema v2 | Registry → `orders-schema` | Version 2 Available |
| S3 files | S3 → bucket → `schema-demo/year=2024/month=01/` | v1 and v2 Parquet files |
| Glue database | Glue → Databases | `handson_schema_demo` listed |
| Glue table | Glue → Tables → `orders_partitioned` | partition projection properties set |
| Athena query | Athena → with `WHERE year=2024 AND month=1` | Less data scanned than without filter |

### 7.3 CLI Verification Script

```powershell
Write-Host "=== SCHEMA EVOLUTION VERIFICATION ===" -ForegroundColor Cyan

# Registry
aws glue get-registry `
  --registry-id "RegistryName=$REGISTRY" `
  --query "{Name:RegistryName,Status:Status}"
# Expected: Status=AVAILABLE

# Schema versions
aws glue list-schema-versions `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "SchemaVersions[*].{V:VersionNumber,S:Status}"
# Expected: [{"V":1,"S":"AVAILABLE"},{"V":2,"S":"AVAILABLE"}]

# Verify v2 has new fields
$V2 = aws glue get-schema-version `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --schema-version-number "VersionNumber=2" `
  --query "SchemaDefinition" --output text
Write-Host "v2 has product field: $(if ($V2 -match 'product') {'YES ✅'} else {'NO ❌'})"
Write-Host "v2 has discount_pct field: $(if ($V2 -match 'discount_pct') {'YES ✅'} else {'NO ❌'})"

# S3 files
aws s3 ls "s3://$BUCKET/schema-demo/" --recursive
# Expected: v1_orders.parquet and v2_orders.parquet

# Glue table partition projection
aws glue get-table --database-name $DB_NAME --name $TABLE `
  --query "Table.Parameters.{'proj.enabled':'projection.enabled','year.range':'projection.year.range'}"
# Expected: {"proj.enabled": "true", "year.range": "2023,2030"}

Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

### 7.4 Verification Checklist

- [ ] `python src/schema_evolution_demo.py` runs without errors
- [ ] 5 rows returned in merged read (3 v1 + 2 v2)
- [ ] v1 rows show NaN for `product` and `discount_pct`
- [ ] v2 rows show actual values for `product` and `discount_pct`
- [ ] Glue registry `handson-registry` Status = AVAILABLE
- [ ] Schema `orders-schema` has v1 and v2, both AVAILABLE
- [ ] v2 compatibility = BACKWARD
- [ ] v2 new fields use union type `["null","string"]`
- [ ] S3 has `v1_orders.parquet` and `v2_orders.parquet`
- [ ] Glue table `orders_partitioned` has `projection.enabled=true`
- [ ] Athena query with partition filter scans less data than without

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During the Demo

**When `write_v1_schema()` runs:**
- Creates a 3-row, 4-column Parquet file in S3
- Schema stored IN the Parquet file header — every Parquet file knows its own schema

**When `write_v2_schema()` runs:**
- Creates a 2-row, 6-column Parquet file in the SAME S3 prefix
- Different schema from v1 — 2 extra columns

**When `read_merged_schema()` runs:**
- PyArrow reads BOTH files and merges their schemas
- Result: 5 rows, 6 columns. v1 rows have NaN for missing columns.
- This is Parquet's "schema evolution" built-in. No special configuration.
- Contrast with CSV: all files must have identical columns or errors occur.

### 8.2 Partition Pruning Internals

```
Athena execution with partition filter WHERE year=2024 AND month=1:

1. Athena reads table metadata from Glue Catalog
2. Sees partition projection config: year=2023-2030, month=1-12
3. Evaluates WHERE clause against partition keys
4. Identifies: only s3://bucket/year=2024/month=01/ needed
5. Lists files ONLY in that prefix
6. Reads ONLY those files
7. Returns results

Without partition filter:
1-3. Same
4. All years AND months needed → LIST entire bucket
5. Every file must be read
```

### 8.3 Billing Observations

- **Schema Registry**: FREE for first 10M schema versions per month.
  For 2 versions, cost = $0.
- **Glue Catalog**: FREE for first 1M objects. Table + 2 schemas = $0.
- **S3**: Two tiny Parquet files (< 1 KB each) → essentially $0.
- **Athena**: Only cost that's non-zero — $5/TB scanned.
  For demo data (KB-range), cost < $0.001 per query.

### 8.4 Schema Evolution Best Practices

```
DO:
  ✅ Add nullable fields with default values
  ✅ Version schemas in Glue Schema Registry
  ✅ Use BACKWARD compatibility for streaming schemas
  ✅ Document each schema version with description

DON'T:
  ❌ Rename existing fields (renames break readers)
  ❌ Change field type (int→string breaks math operations)
  ❌ Remove required fields (breaks consumers that expect them)
  ❌ Add required fields without defaults (breaks old producers)

When you MUST rename:
  Step 1: Add new field with new name (v2)
  Step 2: Populate both old and new field in producers (v2)
  Step 3: Update all consumers to use new field name (v3)
  Step 4: Deprecate and remove old field (v4)
  Timeline: 4 versions, typically 4 weeks
```

---

## 9. Screenshots Guidance

| # | What to Capture | When |
|---|----------------|------|
| SS-01 | Glue Schema Registry — Registries list (before creation) | Before Step 1 |
| SS-02 | Registry `handson-registry` Status = Available | Step 1.4 |
| SS-03 | Schema `orders-schema` v1 — Available | Step 2.5 |
| SS-04 | Schema v2 registration form with union type fields | Step 3.2 |
| SS-05 | Schema `orders-schema` showing v1 + v2 both Available | Step 3.3 |
| SS-06 | Terminal: merged read output showing NaN for v1 rows | Step 4.1 |
| SS-07 | S3: `schema-demo/year=2024/month=01/` with both Parquet files | Step 5.1 |
| SS-08 | Glue table `orders_partitioned` partition projection properties | Step 6.6 |
| SS-09 | Athena: query WITH partition filter — Data scanned (low) | Step 7.2 |
| SS-10 | Athena: query WITHOUT filter — Data scanned (higher) | Step 7.3 |

**Total: 10 screenshots**

---

## 10. Cleanup Steps

### 10.1 AWS Console Cleanup

1. **Glue Schema versions:** Glue → Schema Registry → `handson-registry` → `orders-schema` → delete v2, then v1, then schema
2. **Glue Registry:** Glue → Schema Registry → `handson-registry` → **Delete**
3. **Glue table:** Glue → Tables → `orders_partitioned` → **Delete**
4. **Glue database:** Glue → Databases → `handson_schema_demo` → **Delete**
5. **S3 demo files:** S3 → bucket → `schema-demo/` → **Delete** (select all, delete)

### 10.2 CLI Cleanup (PowerShell)

```powershell
# 1. Delete Glue table
aws glue delete-table --database-name $DB_NAME --name $TABLE

# 2. Delete Glue database
aws glue delete-database --name $DB_NAME

# 3. Delete schema (must delete versions first)
$VERSIONS = aws glue list-schema-versions `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "SchemaVersions[*].SchemaVersionId" --output text
foreach ($v in $VERSIONS -split "`t") {
  aws glue delete-schema-versions `
    --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
    --versions $v 2>$null
}
aws glue delete-schema `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA"

# 4. Delete registry
aws glue delete-registry --registry-id "RegistryName=$REGISTRY"

# 5. Delete S3 demo files
aws s3 rm "s3://$BUCKET/schema-demo/" --recursive
aws s3 rm "s3://$BUCKET/schema-demo-compacted/" --recursive

Write-Host "✅ All resources cleaned up"
```

### 10.3 Verify Cleanup

```powershell
aws glue list-registries --query "Registries[?RegistryName=='$REGISTRY']"
# Expected: [] (empty)

aws s3 ls "s3://$BUCKET/schema-demo/" 2>&1
# Expected: nothing listed

Write-Host "✅ Cleanup verified — $0.00/month going forward"
```

---

## Quick Reference Card

```
PYTHON DEMO (runs locally):
  pip install boto3 pyarrow pandas s3fs
  $env:DATA_LAKE_BUCKET = "handson-data-lake-ACCOUNT"
  python src\schema_evolution_demo.py

SCHEMA REGISTRY:
  Create:  aws glue create-registry --registry-name handson-registry
  v1:      aws glue create-schema --registry-id RegistryName=handson-registry ...
  v2:      aws glue register-schema-version --schema-id RegistryName=...,SchemaName=...
  List:    aws glue list-schema-versions --schema-id RegistryName=...,SchemaName=...

PARTITION PROJECTION (Glue table config):
  projection.enabled=true
  projection.year.type=integer  projection.year.range=2023,2030
  projection.month.type=integer projection.month.range=1,12
  projection.day.type=integer   projection.day.range=1,31
  storage.location.template=s3://BUCKET/orders/year=${year}/month=${month}/day=${day}

SCHEMA EVOLUTION RULES:
  ✅ Add nullable field: {"name":"product","type":["null","string"],"default":null}
  ❌ Rename field
  ❌ Change type
  ❌ Add required field

PARTITION QUERY (use partition filter for 99% cost savings):
  SELECT * FROM table WHERE year=2024 AND month=1 AND day=15

CLEANUP:
  aws glue delete-schema --schema-id RegistryName=handson-registry,SchemaName=orders-schema
  aws glue delete-registry --registry-id RegistryName=handson-registry
  aws s3 rm s3://BUCKET/schema-demo/ --recursive

COST: ~$0.01/session | Schema Registry free tier = 10M versions/month
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.8_schema_evolution*
