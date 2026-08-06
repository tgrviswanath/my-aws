# Complete Implementation Guide — Project 9.6: dbt Transformation Pipeline
# dbt Core + Amazon Athena + AWS Glue Data Catalog

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 2–3 hours
**Cost:** ~$0.02/month | **dbt Core is 100% free and open source**

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
**SQL Transformation Pipeline with dbt Core on Amazon Athena**

### Business / Problem Statement

Your data lake has raw orders in S3, crawled by Glue, queryable via Athena.
But analysts who open Athena see raw, messy data:
- Column names like `AMT` instead of `order_amount_usd`
- Status values are `'PENDING'`, `'pending'`, `'Pending'` — all meaning the same thing
- No business logic applied — analysts write the same CASE WHEN tier logic in every query
- No tests — nobody knows if `order_id` is actually unique
- No documentation — what does column `qty` mean?

**dbt (data build tool)** is the industry-standard solution:
- Transform raw data into clean, tested, documented analytical tables using **SQL only**
- Every transformation is a `.sql` file tracked in Git — version controlled
- Tests run automatically after every build — data quality guaranteed
- Documentation auto-generated from code — stakeholders always have up-to-date docs
- Used by Airbnb, GitLab, Shopify, and thousands of data teams

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════════
 INPUT — Source Data (already in Glue Data Catalog)
═══════════════════════════════════════════════════════════════════════
Source:   Glue Database: handson_data_lake
Table:    orders  (from S3 raw/orders/ — crawled by Glue)
Location: s3://handson-data-lake-ACCOUNT/raw/orders/
Schema:
  order_id    STRING   raw, may have nulls
  customer_id STRING   raw
  product     STRING   mixed case, may have leading/trailing spaces
  status      STRING   inconsistent case: PENDING / pending / Pending
  amount      STRING   stored as string in raw CSV
  quantity    STRING   stored as string in raw CSV
  order_date  STRING   stored as string in raw CSV

═══════════════════════════════════════════════════════════════════════
 LAYER 1 — Staging  (models/staging/stg_orders.sql)
═══════════════════════════════════════════════════════════════════════
Materialization: VIEW (no storage — computed on every query)
Output table:    handson_data_lake.stg_orders

Transformations applied:
  ✓ order_id, customer_id       — kept as-is (identifiers)
  ✓ upper(trim(product))        → product_name (normalised)
  ✓ lower(trim(status))         → order_status (normalised, 'unknown' if null)
  ✓ cast(amount as double)      → order_amount_usd
  ✓ cast(quantity as integer)   → quantity
  ✓ cast(order_date as date)    → order_date (proper Date type)
  ✓ year(order_date)            → order_year (int)
  ✓ month(order_date)           → order_month (int)
  ✓ current_timestamp           → _loaded_at (metadata)
  ✓ WHERE order_id IS NOT NULL AND amount > 0  (filter invalid rows)

═══════════════════════════════════════════════════════════════════════
 LAYER 2 — Marts  (models/marts/fct_orders.sql)
═══════════════════════════════════════════════════════════════════════
Materialization: INCREMENTAL TABLE (merge on order_id)
Output table:    handson_data_lake.fct_orders
Strategy:        merge (upsert — INSERT new, UPDATE changed)

Built on top of stg_orders. Additional business logic:
  ✓ order_amount_usd / quantity  → unit_price_usd
  ✓ CASE WHEN amount >= 100 THEN 'high_value'
         WHEN amount >= 50  THEN 'medium_value'
         ELSE 'low_value'   → order_tier (business segmentation)
  ✓ current_timestamp            → _dbt_updated_at

Incremental filter (only new rows on re-run):
  WHERE order_date > (SELECT MAX(order_date) FROM fct_orders)

═══════════════════════════════════════════════════════════════════════
 TESTS — schema.yml (runs after every dbt run)
═══════════════════════════════════════════════════════════════════════
fct_orders tests:
  ✓ order_id:          not_null + unique
  ✓ customer_id:       not_null
  ✓ order_amount_usd:  not_null + expression >= 0
  ✓ order_status:      accepted_values ['pending','processing','shipped',
                                        'delivered','cancelled','unknown']
  ✓ order_tier:        accepted_values ['high_value','medium_value','low_value']

═══════════════════════════════════════════════════════════════════════
 FINAL OUTPUT — Available in Athena
═══════════════════════════════════════════════════════════════════════
stg_orders  — VIEW in handson_data_lake
fct_orders  — TABLE in handson_data_lake, Parquet in S3

Example fct_orders row:
  order_id="ORD-001", customer_id="CUST-101",
  product_name="WIDGET A", order_status="delivered",
  order_date=2024-01-15, order_year=2024, order_month=1,
  order_amount_usd=45.23, quantity=2, unit_price_usd=22.615,
  order_tier="low_value", _dbt_updated_at=2024-01-15T10:30:00Z
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain ELT vs ETL and where dbt fits
- [ ] Install dbt Core and the Athena adapter
- [ ] Configure `~/.dbt/profiles.yml` for Athena
- [ ] Understand `source()` and `ref()` functions
- [ ] Write a staging model with data cleaning transformations
- [ ] Write a mart model with business logic and incremental strategy
- [ ] Run `dbt debug`, `dbt run`, `dbt test`
- [ ] Write schema.yml tests (not_null, unique, accepted_values)
- [ ] Generate and serve dbt documentation locally
- [ ] Query dbt-created tables in Athena
- [ ] Understand all four materialization types

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     dbt TRANSFORMATION PIPELINE                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SOURCE: Glue Data Catalog                                       │   │
│  │  Database: handson_data_lake  |  Table: orders                  │   │
│  │  Location: s3://BUCKET/raw/orders/  (raw CSV, messy)            │   │
│  └──────────────────────┬──────────────────────────────────────────┘   │
│                         │  SELECT * FROM {{ source('raw','orders') }}   │
│                         ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STAGING LAYER: stg_orders  (models/staging/stg_orders.sql)     │   │
│  │  Materialization: VIEW                                           │   │
│  │  Clean + standardize: cast types, normalize case, filter nulls  │   │
│  │  No business logic — 1:1 with source                            │   │
│  └──────────────────────┬──────────────────────────────────────────┘   │
│                         │  SELECT * FROM {{ ref('stg_orders') }}        │
│                         ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  MART LAYER: fct_orders  (models/marts/fct_orders.sql)          │   │
│  │  Materialization: INCREMENTAL (merge on order_id)               │   │
│  │  Business logic: unit_price, order_tier segmentation            │   │
│  │  Only processes new rows on each run                            │   │
│  └──────────────────────┬──────────────────────────────────────────┘   │
│                         │                                                │
│         ┌───────────────┴──────────────────┐                           │
│         ▼                                  ▼                           │
│  ┌────────────────────┐  ┌───────────────────────────────────────────┐ │
│  │  TESTS (schema.yml)│  │  DOCUMENTATION (dbt docs generate)        │ │
│  │  not_null: order_id│  │  Auto-generated from schema.yml +         │ │
│  │  unique: order_id  │  │  model descriptions                       │ │
│  │  accepted_values:  │  │  Lineage graph: raw→stg→fct               │ │
│  │    order_status    │  │  dbt docs serve → http://localhost:8080   │ │
│  │    order_tier      │  └───────────────────────────────────────────┘ │
│  └────────────────────┘                                                 │
│                         │                                                │
│                         ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ATHENA QUERY ENGINE                                             │   │
│  │  Database: handson_data_lake                                     │   │
│  │  SELECT order_tier, SUM(order_amount_usd)                       │   │
│  │  FROM fct_orders GROUP BY order_tier                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **Amazon Athena** | SQL engine — executes dbt models | ❌ $5/TB scanned |
| **AWS Glue Data Catalog** | Metadata store — dbt reads/writes table definitions | ✅ 1M objects free |
| **Amazon S3** | Stores Athena results, dbt staging files, Parquet output | ✅ 5 GB free |
| **dbt Core** | Runs entirely locally — no AWS service needed | ✅ 100% Free |

### Key Concepts Explained

**ELT vs ETL — where dbt fits:**
```
ETL (old way):
  Extract → Transform (in a separate tool) → Load into warehouse
  Problem: transformation logic in Java/Python, hard to test and document

ELT (modern way — dbt):
  Extract → Load (raw data into S3/warehouse) → Transform IN THE WAREHOUSE
  Load raw data first, then use SQL (dbt) to transform it
  Benefit: SQL is readable, Git-trackable, testable, documentable

dbt handles the "T" in ELT:
  Raw S3 data (already loaded) → dbt SQL models → Clean analytical tables
```

**Model — the core unit of dbt:**
```sql
-- Every .sql file in models/ is a model
-- A model is a SELECT statement — dbt wraps it in CREATE TABLE/VIEW
-- You write: SELECT ...
-- dbt runs: CREATE TABLE schema.model_name AS SELECT ...
```

**`source()` vs `ref()`:**
```sql
-- source(): references raw tables outside dbt (in Glue Catalog)
SELECT * FROM {{ source('raw', 'orders') }}
-- Resolves to: SELECT * FROM handson_data_lake.orders

-- ref(): references another dbt model (builds the DAG)
SELECT * FROM {{ ref('stg_orders') }}
-- Resolves to: SELECT * FROM handson_data_lake.stg_orders
-- AND: dbt knows stg_orders must run before this model
```

**Materialization types:**
```
view       → CREATE OR REPLACE VIEW (no storage, recomputed each query)
table      → DROP TABLE + CREATE TABLE AS SELECT (full rebuild every run)
incremental→ INSERT new + UPDATE changed rows (fastest for large tables)
ephemeral  → inlined as CTE, never stored (intermediate calculations)

This project uses:
  stg_orders  → view     (small, cheap, always fresh)
  fct_orders  → incremental (large, only process new orders)
```

**Incremental strategy (merge):**
```sql
-- First run (no table yet): creates table with ALL rows
-- Subsequent runs: only processes rows WHERE order_date > MAX(order_date)

{% if is_incremental() %}
where order_date > (select max(order_date) from {{ this }})
{% endif %}

-- merge strategy: INSERT rows that don't exist, UPDATE rows that changed
-- unique_key='order_id': the key used to match existing rows
```

**dbt Tests:**
```yaml
columns:
  - name: order_id
    tests:
      - not_null    # SELECT count(*) FROM fct_orders WHERE order_id IS NULL
      - unique      # SELECT order_id FROM fct_orders GROUP BY 1 HAVING count(*) > 1

# Tests are SQL queries that should return 0 rows
# If they return > 0 rows → test FAILS
```

### Best Practices Followed

- **Staging 1:1 with source** — `stg_orders` mirrors raw table, no business logic
- **`ref()` over hardcoded names** — ensures correct execution order, portable
- **`source()` for raw tables** — makes data lineage visible from external sources
- **Incremental on fact tables** — only process new/changed rows, 100x faster at scale
- **`unique_key` on incremental** — prevents duplicate rows on re-runs
- **`is_incremental()` guard** — `stg_orders` filter only applies on subsequent runs
- **schema.yml tests on every column** — data quality guaranteed after every build
- **`coalesce(status, 'unknown')`** — explicit handling of nulls in dimensions
- **Lowercase all string dimensions** — `lower(trim(status))` for consistent grouping

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia)
- Glue database `handson_data_lake` with table `orders` already created
  (from Project 9.1 — Glue Crawler ran on `raw/orders/`)
- Athena workgroup with S3 output location configured
- S3 bucket for Athena query results

### 3.2 IAM Permissions Required (for YOUR user)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution", "athena:GetQueryExecution",
        "athena:GetQueryResults", "athena:StopQueryExecution",
        "athena:ListWorkGroups", "athena:GetWorkGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable",
        "glue:GetTables", "glue:GetPartition", "glue:GetPartitions",
        "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
        "glue:CreatePartition", "glue:BatchCreatePartition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::YOUR_DATA_LAKE_BUCKET", "arn:aws:s3:::YOUR_DATA_LAKE_BUCKET/*",
        "arn:aws:s3:::YOUR_STAGING_BUCKET",   "arn:aws:s3:::YOUR_STAGING_BUCKET/*"
      ]
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) | Purpose |
|------|---------|------------------|---------|
| Python | >= 3.9 | `winget install Python.Python.3.11` | dbt runtime |
| pip | latest | bundled with Python | Package manager |
| dbt Core + Athena adapter | 1.7.x | `pip install dbt-athena-community` | Run dbt models |
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` | Query verification |
| Git | latest | `winget install Git.Git` | Version control |
| VS Code | latest | `winget install Microsoft.VisualStudioCode` | SQL/YAML editing |

### 3.4 Environment Variables (PowerShell)

```powershell
$env:AWS_REGION     = "us-east-1"
$env:ACCOUNT        = aws sts get-caller-identity --query Account --output text
$env:DATA_BUCKET    = "handson-data-lake-$env:ACCOUNT"
$env:STAGING_BUCKET = "handson-dbt-staging-$env:ACCOUNT"

# Verify credentials
aws sts get-caller-identity
# Expected: Account, UserId, Arn
```

### 3.5 Estimated AWS Cost

| Activity | Cost |
|----------|------|
| dbt Core installation | $0 (open source) |
| Single `dbt run` on 1,000-row dataset | ~$0.000005 |
| Single `dbt run` on 1 GB dataset | ~$0.005 |
| Monthly (10 runs/day × 1 GB) | ~$1.50 |
| S3 storage for dbt artifacts + results | ~$0.01 |
| **Typical learning session total** | **~$0.01–$0.05** |

> **dbt Core is 100% free and open source. The only AWS costs are Athena query charges.**
> Athena charges $5/TB scanned. 1,000 rows ≈ 200 KB ≈ $0.000001 per query.

---

## 4. Project Folder Structure

```
project_9.6_dbt/
│
├── GUIDE.md                     ← This comprehensive guide (you are here)
├── README.md                    ← Quick start and lessons learned
├── steps.md                     ← CLI commands reference (PowerShell)
├── steps_awsconsoleui.md        ← Console UI steps (improved template)
├── verify.md                    ← Verification checklist + commands
├── cost_estimate.md             ← Athena cost breakdown
│
├── dbt_project/                 ← The dbt project directory
│   └── models/
│       ├── staging/
│       │   └── stg_orders.sql   ← Layer 1: clean raw data → VIEW
│       └── marts/
│           ├── fct_orders.sql   ← Layer 2: business logic → INCREMENTAL TABLE
│           └── schema.yml       ← Tests + documentation for fct_orders
│
├── docs/
│   └── architecture.md          ← Model lineage, materialization types
│
└── terraform/
    └── main.tf                  ← Athena workgroup + S3 staging bucket (reference)
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `dbt_project/models/staging/stg_orders.sql` | Staging model: reads from `source('raw','orders')`, cleans and casts types, materialized as VIEW |
| `dbt_project/models/marts/fct_orders.sql` | Fact table: reads from `ref('stg_orders')`, adds business logic, incremental merge strategy |
| `dbt_project/models/marts/schema.yml` | Tests and descriptions for fct_orders columns |
| `docs/architecture.md` | Lineage diagram, materialization types, test types |
| `terraform/main.tf` | Athena workgroup (`handson-dbt`) + S3 staging bucket + IAM policy |

### Missing Files (need to create before running)

| File | Path | Purpose |
|------|------|---------|
| `dbt_project.yml` | `dbt_project/dbt_project.yml` | dbt project config (name, version, paths) |
| `~/.dbt/profiles.yml` | User home directory | Connection to Athena (NOT in project folder) |
| `dbt_project/models/staging/schema.yml` | models/staging/ | Source definition + staging tests |
| `dbt_project/packages.yml` | dbt_project/ | dbt-utils package dependency |

All of these are created in the implementation steps below.

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> dbt itself runs **locally** from your terminal — there is no AWS Console for dbt.
> The Console steps cover the AWS infrastructure dbt needs:
> 1. Verify Glue source table exists
> 2. Set up Athena workgroup + S3 output location
> 3. Verify dbt output tables in Athena after running

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `athena:StartQueryExecution`, `glue:GetTable`, `s3:PutObject`
- ✅ Services enabled: Athena, Glue, S3 — available in us-east-1
- ✅ Region: us-east-1 selected in AWS Console

**Step 0.1: Verify Glue Source Table**
1. Search → **AWS Glue** → left sidebar → **Tables**
2. **Expected View:** `orders` table in database `handson_data_lake`
3. **If Not Found:** Run the Glue Crawler from Project 9.1 first

**📸 Screenshot P0:** Glue Tables showing `orders` in `handson_data_lake`

---

#### Step 1 — Set Up Athena Workgroup and S3 Output

**Prerequisites Check:**
- ✅ Required permissions: `athena:CreateWorkGroup`, `s3:CreateBucket`
- ✅ Services enabled: Amazon Athena, S3
- ✅ Region: us-east-1

**Step 1.1: Navigate to Athena**
1. Search bar → **Athena** → click it
2. **Expected View:** Athena Query Editor

**Step 1.2: Configure Query Result Location (First Time)**

**Decision Point 1:** Output location setup
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Use default bucket | Quick start | ❌ No control over naming |
| **Custom S3 path** | Organised, cost-trackable | ✅ Use this |

1. Click **Settings** (top-right) → **Manage**
2. Query result location: `s3://handson-data-lake-YOUR_ACCOUNT_ID/athena-results/dbt/`
3. Click **Save**

**📸 Screenshot 1a:** Athena Settings showing S3 output location configured

**Step 1.3: Create Dedicated Workgroup for dbt**
1. In Athena → click **Workgroups** (left sidebar) → **Create workgroup**
2. Fill in:

| Field | Value | Explanation |
|-------|-------|-------------|
| Workgroup name | `handson-dbt` | Matches terraform/main.tf |
| Description | `dbt transformation queries` | |
| Query result location | `s3://handson-dbt-staging-ACCOUNT/dbt/` | Separate from ad-hoc results |
| Bytes scanned limit | `1073741824` (1 GB) | Cost control per query |
| Enforce workgroup config | ✅ Enable | Override per-query settings |

3. Click **Create workgroup**

**Step 1.4: Validate**
**Expected Outcome:** Workgroup `handson-dbt` listed as Active

**📸 Screenshot 1b:** Workgroup `handson-dbt` created and Active

---

#### Step 2 — Create S3 Staging Bucket for dbt

**Prerequisites Check:**
- ✅ Required permissions: `s3:CreateBucket`, `s3:PutBucketLifecycleConfiguration`

**Step 2.1: Navigate to S3**
1. Search → **S3** → **Create bucket**

**Step 2.2: Configure Bucket**

| Field | Value |
|-------|-------|
| Bucket name | `handson-dbt-staging-YOUR_ACCOUNT_ID` |
| Region | us-east-1 |
| Block public access | ✅ All 4 options |
| Versioning | Disabled (query results are temporary) |

**Step 2.3: Add Lifecycle Policy (Cost Control)**
1. Click on bucket → **Management** tab → **Create lifecycle rule**
2. Rule name: `expire-dbt-results`
3. Prefix: `dbt/`
4. Action: ✅ Expire current versions → `7` days
5. Click **Create rule**

This auto-deletes dbt query results after 7 days — keeps storage costs near $0.

**📸 Screenshot 2a:** S3 bucket `handson-dbt-staging-ACCOUNT` with lifecycle rule

---

#### Step 3 — Verify dbt Output in Athena (After Running dbt)

> Complete the CLI steps (Section 5B) first. Then return here to verify via Console.

**Step 3.1: Open Athena Query Editor**
1. Athena → Query Editor
2. Left panel: Database → select `handson_data_lake`
3. **Expected View:** Tables list shows `orders`, `stg_orders`, `fct_orders`

**📸 Screenshot 3a:** Athena table list showing stg_orders and fct_orders after dbt run

**Step 3.2: Query stg_orders (VIEW)**
```sql
SELECT * FROM handson_data_lake.stg_orders LIMIT 5;
```
**Expected:** Rows with clean data — proper types, lowercase order_status, product_name in UPPER CASE

**Step 3.3: Query fct_orders (TABLE)**
```sql
SELECT order_tier, COUNT(*) as orders, SUM(order_amount_usd) as revenue
FROM handson_data_lake.fct_orders
GROUP BY order_tier
ORDER BY revenue DESC;
```
**Expected:**
```
order_tier   | orders | revenue
high_value   | 23     | 3450.20
medium_value | 45     | 2870.50
low_value    | 122    | 1890.30
```

**📸 Screenshot 3b:** Athena showing fct_orders query results by order_tier

---

## 5B. AWS CLI Method

> All dbt commands run in PowerShell. AWS CLI used for verification only.
> Run from the project root:
> `D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt`

---

### Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$DATA_BUCKET    = "handson-data-lake-$ACCOUNT"
$STAGING_BUCKET = "handson-dbt-staging-$ACCOUNT"
$DBT_DIR        = "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt\dbt_project"

Write-Host "Account: $ACCOUNT"
Write-Host "Data bucket: $DATA_BUCKET"
```

---

### Phase 1 — Install dbt

```powershell
# Install dbt Core with Athena adapter
pip install dbt-athena-community==1.7.1

# Verify installation
dbt --version
# Expected:
# Core:
#   - installed: 1.7.x
#   - latest:    1.7.x
# Plugins:
#   - athena: 1.7.x

# Create AWS S3 staging bucket (if not already created)
aws s3api create-bucket --bucket $STAGING_BUCKET --region $REGION
aws s3api put-public-access-block `
  --bucket $STAGING_BUCKET `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

Write-Host "✅ dbt installed and S3 staging bucket created"
```

---

### Phase 2 — Configure dbt Profiles

dbt needs `~/.dbt/profiles.yml` to connect to Athena.

```powershell
# Create .dbt directory in user home
New-Item -ItemType Directory -Path "$env:USERPROFILE\.dbt" -Force

# Write profiles.yml
@"
handson:
  target: dev
  outputs:
    dev:
      type: athena
      s3_staging_dir: s3://$STAGING_BUCKET/dbt/
      region_name: $REGION
      database: awsdatacatalog
      schema: handson_data_lake
      work_group: handson-dbt
      threads: 4
"@ | Out-File -FilePath "$env:USERPROFILE\.dbt\profiles.yml" -Encoding utf8

Write-Host "✅ profiles.yml written to $env:USERPROFILE\.dbt\profiles.yml"

# Verify file contents
Get-Content "$env:USERPROFILE\.dbt\profiles.yml"
```

**profiles.yml field explanation:**
| Field | Value | Explanation |
|-------|-------|-------------|
| `type: athena` | athena | dbt adapter to use |
| `s3_staging_dir` | S3 path | Where Athena writes query results |
| `database` | awsdatacatalog | Athena catalog name (always this for standard Athena) |
| `schema` | handson_data_lake | Glue database where dbt creates tables |
| `work_group` | handson-dbt | Athena workgroup for cost tracking |
| `threads` | 4 | Parallel model execution count |

---

### Phase 3 — Create Missing dbt Project Files

The project has SQL models but needs config files to run.

```powershell
Set-Location $DBT_DIR

# Step 3.1 — Create dbt_project.yml
@'
name: 'handson'
version: '1.0.0'
config-version: 2

profile: 'handson'

model-paths: ["models"]
test-paths:  ["tests"]
macro-paths: ["macros"]

target-path: "target"
clean-targets: ["target", "dbt_packages"]

models:
  handson:
    staging:
      +materialized: view
      +schema: handson_data_lake
    marts:
      +materialized: table
      +schema: handson_data_lake
'@ | Out-File -FilePath "dbt_project.yml" -Encoding utf8

# Step 3.2 — Create staging schema.yml (source definition)
New-Item -ItemType Directory -Path "models\staging" -Force
@'
version: 2

sources:
  - name: raw
    database: awsdatacatalog
    schema: handson_data_lake
    tables:
      - name: orders
        description: "Raw orders data from S3 — crawled by Glue"
        columns:
          - name: order_id
            description: "Unique order identifier"
          - name: customer_id
            description: "Customer identifier"
          - name: product
            description: "Product name (raw, may have inconsistent case)"
          - name: status
            description: "Order status (raw, may have inconsistent case)"
          - name: amount
            description: "Order amount (stored as string in raw CSV)"
          - name: quantity
            description: "Quantity ordered (stored as string)"
          - name: order_date
            description: "Order date (stored as string in YYYY-MM-DD format)"

models:
  - name: stg_orders
    description: "Cleaned and standardized orders — 1:1 with source"
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: customer_id
        tests:
          - not_null
      - name: order_amount_usd
        tests:
          - not_null
      - name: order_status
        tests:
          - accepted_values:
              values: ['pending','processing','shipped','delivered','cancelled','unknown']
'@ | Out-File -FilePath "models\staging\schema.yml" -Encoding utf8

# Step 3.3 — Create packages.yml (dbt-utils for expression_is_true test)
@'
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
'@ | Out-File -FilePath "packages.yml" -Encoding utf8

Write-Host "✅ Project files created"
```

---

### Phase 4 — Test Connection

```powershell
Set-Location $DBT_DIR

# Install dbt packages (dbt-utils)
dbt deps
# Expected:
# Installing dbt-labs/dbt_utils
# Installed from version 1.1.1

# Test connection to Athena
dbt debug
# Expected output (all checks pass):
# Connection:
#   profiles.yml file [OK found and valid]
#   dbt_project.yml file [OK found and valid]
#   git remote [optional]
#   Connection test: [OK connection ok]
```

**Troubleshooting `dbt debug`:**
| Error | Fix |
|-------|-----|
| `profile 'handson' not found` | Check profiles.yml name matches dbt_project.yml profile field |
| `Connection test: ERROR` | Check AWS credentials: `aws sts get-caller-identity` |
| `Schema 'handson_data_lake' not found` | Create Glue database first (Project 9.1) |
| `s3_staging_dir bucket does not exist` | Create staging bucket (Phase 1) |

---

### Phase 5 — Run dbt Models

```powershell
Set-Location $DBT_DIR

# Run ALL models (staging + marts)
dbt run

# Expected output:
# Running with dbt=1.7.x
# Found 2 models, 7 tests, 0 sources, 0 exposures, 0 metrics
#
# 14:23:01  Concurrency: 4 threads (target='dev')
#
# 1 of 2 START sql view model handson_data_lake.stg_orders ......... [RUN]
# 1 of 2 OK created sql view model handson_data_lake.stg_orders .... [OK in 2.34s]
# 2 of 2 START sql incremental model handson_data_lake.fct_orders .. [RUN]
# 2 of 2 OK created sql incremental model handson_data_lake.fct_orders [OK in 4.12s]
#
# Finished running 2 models in 0:00:09.
# Completed successfully
# Done. PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=2

# Run only staging models
dbt run --select staging

# Run only marts
dbt run --select marts

# Run specific model
dbt run --select fct_orders

# Full refresh (rebuild from scratch — ignores incremental filter)
dbt run --full-refresh
```

---

### Phase 6 — Run dbt Tests

```powershell
# Run ALL tests
dbt test

# Expected output:
# 1 of 7 START test not_null_fct_orders_order_id ............. [RUN]
# 1 of 7 PASS not_null_fct_orders_order_id ................... [PASS in 1.23s]
# 2 of 7 PASS unique_fct_orders_order_id ..................... [PASS in 1.45s]
# 3 of 7 PASS not_null_fct_orders_customer_id ................ [PASS in 1.12s]
# 4 of 7 PASS not_null_fct_orders_order_amount_usd ........... [PASS in 1.08s]
# 5 of 7 PASS dbt_utils_expression_is_true_fct_orders_... .... [PASS in 1.34s]
# 6 of 7 PASS accepted_values_fct_orders_order_status ....... [PASS in 1.56s]
# 7 of 7 PASS accepted_values_fct_orders_order_tier ......... [PASS in 1.23s]
#
# Finished running 7 tests in 0:00:09.
# Completed successfully
# Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7

# Test specific model
dbt test --select fct_orders

# Test staging only
dbt test --select staging

# What happens when a test fails:
# FAIL 1 accepted_values_fct_orders_order_status
# Failure in test accepted_values_fct_orders_order_status
# Got 3 results, configured to fail if != 0
# select order_status from fct_orders where order_status not in (...)
```

---

### Phase 7 — Generate and Serve Documentation

```powershell
# Generate documentation artifacts (manifest.json, catalog.json)
dbt docs generate
# Expected:
# Building catalog
# Catalog written to target/catalog.json

# Serve documentation locally
dbt docs serve --port 8080
# Expected: Browser opens at http://localhost:8080
# Shows: lineage graph, model descriptions, column details, test results
# Press Ctrl+C to stop the server
```

**What to explore in dbt docs:**
- **Lineage graph**: Visual map of source → stg_orders → fct_orders
- **Model pages**: Description, columns, tests for each model
- **Source**: shows the raw `orders` table from Glue
- **Test results**: which tests passed/failed on the last run

**📸 Screenshot:** dbt docs lineage graph showing full model chain

---

### Phase 8 — Query dbt Models in Athena (CLI)

```powershell
# Query stg_orders (VIEW)
$Q1_ID = aws athena start-query-execution `
  --query-string "SELECT * FROM handson_data_lake.stg_orders LIMIT 5" `
  --work-group "handson-dbt" `
  --query-execution-context "Database=handson_data_lake" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/results/" `
  --query "QueryExecutionId" --output text

aws athena wait query-execution-complete --query-execution-id $Q1_ID
aws athena get-query-results --query-execution-id $Q1_ID `
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
# Expected: Clean rows with proper types, lowercase order_status

# Query fct_orders by order_tier
$Q2_ID = aws athena start-query-execution `
  --query-string "SELECT order_tier, COUNT(*) as orders, ROUND(SUM(order_amount_usd),2) as revenue FROM handson_data_lake.fct_orders GROUP BY order_tier ORDER BY revenue DESC" `
  --work-group "handson-dbt" `
  --query-execution-context "Database=handson_data_lake" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/results/" `
  --query "QueryExecutionId" --output text

aws athena wait query-execution-complete --query-execution-id $Q2_ID
aws athena get-query-results --query-execution-id $Q2_ID `
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
# Expected: high_value/medium_value/low_value rows with counts and revenue

# Verify incremental model: run again and check only NEW rows processed
dbt run --select fct_orders
# On second run: only processes rows newer than MAX(order_date) in table
# Much faster than first run
```

---

## 6. Code Deep Dive

### `models/staging/stg_orders.sql` — Line by Line

```sql
{{ config(materialized='view') }}
```
- `{{ config() }}` — Jinja configuration block. Sets model-level options.
- `materialized='view'` — dbt creates `CREATE OR REPLACE VIEW stg_orders AS SELECT ...`
- No data stored. Every query to `stg_orders` re-runs the SQL live.
- Why view for staging? Staging is cheap SQL, no business logic, always fresh.

---

```sql
with source as (
    select * from {{ source('raw', 'orders') }}
),
```
- `with source as (...)` — standard dbt CTE pattern. Gives clean names to base tables.
- `{{ source('raw', 'orders') }}` — Jinja function. Arguments:
  - `'raw'` = source name (defined in `staging/schema.yml`)
  - `'orders'` = table name in that source
- Resolves to: `awsdatacatalog.handson_data_lake.orders`
- Why `source()` not hardcoded? dbt tracks lineage. The docs show "raw.orders → stg_orders".

---

```sql
    upper(trim(product))                    as product_name,
    lower(trim(coalesce(status, 'unknown'))) as order_status,
```
- `upper(trim(product))` — normalizes: `"  widget a  "` → `"WIDGET A"`
  Consistent casing lets analysts GROUP BY product_name reliably.
- `lower(trim(coalesce(status, 'unknown')))` — three functions chained:
  1. `coalesce(status, 'unknown')` — replaces NULL with `'unknown'` (explicit null handling)
  2. `trim(...)` — removes `"  pending  "` → `"pending"` (whitespace stripping)
  3. `lower(...)` — normalizes `"PENDING"` → `"pending"` (case normalization)

---

```sql
    cast(amount as double)                  as order_amount_usd,
    cast(quantity as integer)               as quantity,
    cast(order_date as date)                as order_date,
```
- Raw CSV in S3 → Glue infers all columns as STRING. Cast to proper types.
- `as double` for money — 64-bit precision, avoids float rounding errors.
- `as date` — enables `year()`, `month()`, date arithmetic in downstream models.
- Renaming: `amount` → `order_amount_usd` — makes currency explicit.

---

```sql
    where
        order_id is not null
        and amount is not null
        and amount > 0
```
- Filters invalid rows in staging (not in business logic).
- `amount > 0` — removes zero-value orders and negative amounts (data errors).
- Does NOT filter by status or product — that's business logic for the mart layer.

---

### `models/marts/fct_orders.sql` — Line by Line

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns'
    )
}}
```
- `materialized='incremental'` — first run creates table, subsequent runs only process new rows.
- `unique_key='order_id'` — the column used to match existing rows for UPDATE.
- `incremental_strategy='merge'` — does an UPSERT:
  - If `order_id` already exists in table → UPDATE that row
  - If `order_id` is new → INSERT new row
- `on_schema_change='sync_all_columns'` — if you add a column to the model,
  dbt automatically adds it to the table on next run (instead of failing).

---

```sql
with orders as (
    select * from {{ ref('stg_orders') }}

    {% if is_incremental() %}
    where order_date > (select max(order_date) from {{ this }})
    {% endif %}
),
```
- `{{ ref('stg_orders') }}` — references the staging model.
  dbt resolves to: `handson_data_lake.stg_orders` AND adds `stg_orders` as a dependency.
  Execution order guaranteed: stg_orders runs BEFORE fct_orders.
- `{% if is_incremental() %}` — Jinja conditional.
  - First run: `is_incremental()` = False → reads ALL rows from stg_orders
  - Subsequent runs: `is_incremental()` = True → reads ONLY rows newer than MAX(order_date)
- `{{ this }}` — refers to the current model table (`handson_data_lake.fct_orders`)
  Used in subquery to find the latest date already in the table.

---

```sql
        order_amount_usd / nullif(quantity, 0) as unit_price_usd,
```
- `nullif(quantity, 0)` — returns NULL if quantity=0 (prevents division by zero).
- Without this: `amount / 0` = error in Athena (AnalysisException).
- Result: if quantity=0 → `unit_price_usd` = NULL (safe, queryable).

---

```sql
        case
            when order_amount_usd >= 100 then 'high_value'
            when order_amount_usd >= 50  then 'medium_value'
            else 'low_value'
        end as order_tier,
```
- Business logic lives in the mart layer (not staging).
- Thresholds: >= $100 = high_value, >= $50 = medium_value, < $50 = low_value.
- This CASE is the same logic every analyst would write in every report.
  Defining it once in dbt ensures all reports use the same definition.

---

### `models/marts/schema.yml` — Tests Explained

```yaml
- name: order_id
  tests:
    - not_null     # SELECT * FROM fct_orders WHERE order_id IS NULL  → 0 rows expected
    - unique       # SELECT order_id FROM fct_orders GROUP BY 1 HAVING count(*) > 1  → 0 rows
```
- Each test is a SQL query dbt generates and runs in Athena.
- "Pass" = the query returns 0 rows.
- "Fail" = query returns > 0 rows → dbt test FAILS with the count.

```yaml
      - dbt_utils.expression_is_true:
          expression: ">= 0"
```
- From the `dbt-utils` package (installed via packages.yml).
- Generates: `SELECT * FROM fct_orders WHERE NOT (order_amount_usd >= 0)`
- Fails if any negative amounts exist.

```yaml
      - accepted_values:
          values: ['pending','processing','shipped','delivered','cancelled','unknown']
```
- Generates: `SELECT order_status FROM fct_orders WHERE order_status NOT IN (...)`
- Fails if any new/unexpected status value appears (e.g., `'PROCESSING'` — wrong case).

### Common Mistakes and Fixes

| Mistake | Error | Fix |
|---------|-------|-----|
| Profile name mismatch | `profile 'X' not found` | `dbt_project.yml profile:` must match profiles.yml key |
| `source()` name wrong | `Source 'X' not found` | Source name in `schema.yml` must match `source('X', ...)` |
| No `s3_staging_dir` bucket | S3 write error | Create staging bucket before `dbt run` |
| `is_incremental()` not guarded | Runs full table scan on each run | Always wrap WHERE in `{% if is_incremental() %}` |
| `unique_key` not set | Duplicate rows on re-runs | Set `unique_key` to natural key |
| Missing `dbt deps` | `Package not found` | Run `dbt deps` before first `dbt run` |
| Wrong `schema` in profiles.yml | Tables in wrong database | Must match Glue database name exactly |

---

## 7. Verification & Validation

### 7.1 dbt Command Verification

```powershell
Set-Location $DBT_DIR

# Full verification sequence
Write-Host "=== dbt VERIFICATION ===" -ForegroundColor Cyan

# 1. Connection
dbt debug
# Expected: All checks passed

# 2. Run models
dbt run
# Expected: PASS=2 WARN=0 ERROR=0

# 3. Run tests
dbt test
# Expected: PASS=7 WARN=0 ERROR=0 FAIL=0

# 4. Check manifest
$MANIFEST = Get-Content "target\manifest.json" | ConvertFrom-Json
$MODELS = $MANIFEST.nodes.PSObject.Properties |
  Where-Object { $_.Value.resource_type -eq "model" } |
  Select-Object -ExpandProperty Name
Write-Host "Models: $($MODELS -join ', ')"
# Expected: handson.stg_orders, handson.fct_orders

Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green
```

### 7.2 AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| stg_orders view | Athena → Editor → handson_data_lake | `stg_orders` in tables |
| fct_orders table | Athena → Editor → handson_data_lake | `fct_orders` in tables |
| Query results | Athena → `SELECT * FROM fct_orders LIMIT 5` | Clean rows returned |
| dbt workgroup | Athena → Workgroups | `handson-dbt` Active |
| S3 artifacts | S3 → staging bucket → dbt/ | Query result files present |

### 7.3 Athena CLI Verification

```powershell
# Verify stg_orders view exists
$QID = aws athena start-query-execution `
  --query-string "SHOW TABLES IN handson_data_lake" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/verify/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID
aws athena get-query-results --query-execution-id $QID `
  --query "ResultSet.Rows[*].Data[0].VarCharValue" --output table
# Expected: orders, stg_orders, fct_orders listed

# Count fct_orders rows
$QID2 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM handson_data_lake.fct_orders" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/verify/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID2
aws athena get-query-results --query-execution-id $QID2 `
  --query "ResultSet.Rows[1].Data[0].VarCharValue"
# Expected: > 0
```

### 7.4 Verification Checklist

- [ ] `dbt debug` — all checks passed
- [ ] `dbt deps` — dbt-utils installed
- [ ] `dbt run` — PASS=2 WARN=0 ERROR=0 TOTAL=2
- [ ] `stg_orders` VIEW exists in Athena handson_data_lake
- [ ] `fct_orders` TABLE exists in Athena handson_data_lake
- [ ] `dbt test` — all 7 tests passed
- [ ] `dbt run` second time — only processes new rows (faster)
- [ ] `dbt docs generate` — creates `target/manifest.json` and `target/catalog.json`
- [ ] `dbt docs serve` — browser opens lineage graph at localhost:8080

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During dbt run

**When `dbt run` starts:**
- dbt reads `dbt_project.yml` → finds all models in `models/`
- Builds a DAG: `stg_orders` has no dbt dependencies → runs first.
  `fct_orders` depends on `stg_orders` → runs second.
- With `threads: 4`: models with no dependencies run in parallel.
  `stg_orders` and any other models at the same level run simultaneously.

**First run of `fct_orders` (incremental):**
- `is_incremental()` = False → reads ALL rows from `stg_orders`
- Creates the table from scratch: `CREATE TABLE handson_data_lake.fct_orders AS SELECT ...`
- Watch the SQL in `target/compiled/handson/models/marts/fct_orders.sql`

**Second run of `fct_orders` (incremental):**
- `is_incremental()` = True → adds WHERE clause:
  `WHERE order_date > (SELECT MAX(order_date) FROM handson_data_lake.fct_orders)`
- If no new orders since last run: processes 0 rows (very fast)
- If 100 new orders: processes only those 100 (not all 1,000+ existing)

### 8.2 Compiled SQL — What dbt Actually Runs

dbt compiles Jinja templates to pure SQL before running:

```powershell
# View the compiled SQL (what Athena actually receives)
Get-Content "target\compiled\handson\models\marts\fct_orders.sql"

# For incremental run, you'll see the WHERE clause expanded:
# WHERE order_date > (SELECT MAX(order_date) FROM handson_data_lake.fct_orders)

# For full refresh: no WHERE clause
```

### 8.3 dbt Test Internals

```powershell
# See what SQL a test generates
Get-Content "target\compiled\handson\models\marts\schema.yml\unique_fct_orders_order_id.sql"

# unique test expands to:
# SELECT order_id, count(*) as n
# FROM handson_data_lake.fct_orders
# GROUP BY order_id
# HAVING count(*) > 1

# If any rows returned → TEST FAILS
# dbt reports: "Got N results, configured to fail if != 0"
```

### 8.4 Billing Observations

- **dbt Core itself** = $0 always
- **Athena**: each `dbt run` = 2 queries (~stg_orders is a view, so fct_orders scan = once)
- For 1,000 rows (~200 KB): cost ≈ `0.0002 GB × $5/TB` = `$0.000001` per run
- **S3 staging results**: each query writes a small result file (~KB)
  Lifecycle policy (7 days) keeps this near $0
- **Real cost driver**: if you run `dbt run --full-refresh` on a 100 GB table daily
  = `100 GB × 2 queries × $5/TB = $1.00/day`

### 8.5 dbt in the Bigger Picture

```
Project 9.1: Data Lake (S3 + Glue Catalog)  ← raw data source
Project 9.2: Glue ETL                        ← loads to processed/
Project 9.3: Kinesis Streaming               ← real-time aggregates
Project 9.4: Spark on EMR                    ← heavy transformations
Project 9.5: Airflow                         ← orchestrates the pipeline
Project 9.6: dbt (this project)              ← SQL transformations + tests + docs

dbt transforms data ALREADY IN S3/Athena.
It does not move data — it creates views/tables using Athena SQL.
Airflow (9.5) triggers `dbt run` as a pipeline task.
```

---

## 9. Screenshots Guidance

| # | What to Capture | When |
|---|----------------|------|
| SS-01 | Glue Tables showing `orders` in handson_data_lake | Phase 0 |
| SS-02 | Athena Settings with S3 output location | Step 1.2 |
| SS-03 | Athena Workgroup `handson-dbt` created | Step 1.3 |
| SS-04 | S3 staging bucket with lifecycle rule | Step 2.3 |
| SS-05 | `dbt --version` output | Phase 1 |
| SS-06 | `~/.dbt/profiles.yml` content | Phase 2 |
| SS-07 | `dbt debug` — all checks passed | Phase 4 |
| SS-08 | `dbt deps` — packages installed | Phase 4 |
| SS-09 | `dbt run` first run — PASS=2 | Phase 5 |
| SS-10 | `dbt run` second run — faster (incremental) | Phase 5 |
| SS-11 | `dbt test` — all 7 tests PASS | Phase 6 |
| SS-12 | `dbt docs serve` lineage graph in browser | Phase 7 |
| SS-13 | Athena table list showing stg_orders + fct_orders | Step 3.1 |
| SS-14 | Athena query on fct_orders showing order_tier results | Step 3.3 |
| SS-15 | Compiled fct_orders SQL (incremental WHERE clause) | Section 8.2 |

**Total: 15 screenshots for complete documentation**

---

## 10. Cleanup Steps

> dbt Core runs locally — nothing to delete from AWS except Athena/S3 resources.

### 10.1 Remove dbt Output Tables from Athena

```powershell
# Drop dbt-created tables/views from Glue
$Q1 = aws athena start-query-execution `
  --query-string "DROP VIEW IF EXISTS handson_data_lake.stg_orders" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/cleanup/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q1

$Q2 = aws athena start-query-execution `
  --query-string "DROP TABLE IF EXISTS handson_data_lake.fct_orders" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/cleanup/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q2

Write-Host "✅ dbt tables removed from Athena"
```

### 10.2 Delete S3 Staging Bucket

```powershell
# Empty and delete staging bucket
aws s3 rm "s3://$STAGING_BUCKET" --recursive
aws s3api delete-bucket --bucket $STAGING_BUCKET
Write-Host "✅ Staging bucket deleted"
```

### 10.3 Delete Athena Workgroup

```powershell
# Delete workgroup (force=true also deletes query history)
aws athena delete-work-group --work-group "handson-dbt" --recursive-delete-option
Write-Host "✅ Athena workgroup deleted"
```

### 10.4 Clean Local dbt Artifacts

```powershell
Set-Location $DBT_DIR

# Remove compiled SQL, run results, docs
Remove-Item -Recurse -Force "target\" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dbt_packages\" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "logs\" -ErrorAction SilentlyContinue

Write-Host "✅ Local dbt artifacts removed"
```

### 10.5 Console Cleanup (if manual setup)

1. Athena → **Workgroups** → `handson-dbt` → **Delete**
2. S3 → `handson-dbt-staging-ACCOUNT` → **Empty** → **Delete bucket**
3. Glue → **Tables** → select `stg_orders`, `fct_orders` → **Delete**

### 10.6 Verify Cleanup

```powershell
# Confirm tables gone
$QV = aws athena start-query-execution `
  --query-string "SHOW TABLES IN handson_data_lake" `
  --result-configuration "OutputLocation=s3://$DATA_BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QV
aws athena get-query-results --query-execution-id $QV `
  --query "ResultSet.Rows[*].Data[0].VarCharValue" --output table
# Expected: stg_orders and fct_orders NOT listed

# Confirm staging bucket deleted
aws s3api head-bucket --bucket $STAGING_BUCKET 2>&1
# Expected: error (no such bucket)

Write-Host "✅ Cleanup verified"
```

---

## Quick Reference Card

```
INSTALL:
  pip install dbt-athena-community==1.7.1
  dbt deps

CONFIGURE:
  ~/.dbt/profiles.yml  (connection to Athena)
  dbt_project/dbt_project.yml  (project config)

TEST CONNECTION:
  dbt debug

RUN MODELS:
  dbt run                  # all models
  dbt run --select staging # staging only
  dbt run --select fct_orders --full-refresh  # force full rebuild

TEST DATA:
  dbt test                 # all tests
  dbt test --select fct_orders

DOCS:
  dbt docs generate
  dbt docs serve --port 8080

QUERY IN ATHENA:
  SELECT * FROM handson_data_lake.stg_orders LIMIT 5;
  SELECT order_tier, COUNT(*), SUM(order_amount_usd)
  FROM handson_data_lake.fct_orders GROUP BY 1;

CLEANUP:
  DROP VIEW handson_data_lake.stg_orders;
  DROP TABLE handson_data_lake.fct_orders;
  aws s3 rm s3://STAGING_BUCKET --recursive
  aws athena delete-work-group --work-group handson-dbt --recursive-delete-option

COST: ~$0.01/session | dbt Core is FREE
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt*
