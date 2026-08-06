# Complete Implementation Guide — Project 9.9: Redshift Data Warehouse
# Amazon Redshift Serverless + COPY from S3 + Analytical SQL

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 3–4 hours
**Cost:** ~$0.36/hr (8 RPU × $0.045/RPU-hr) | **Only charged while running queries**

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
**Production Data Warehouse with Amazon Redshift Serverless — Load, Query, and Analyze**

### Business / Problem Statement

Your data lake (Projects 9.1–9.8) is excellent for data engineers and data scientists.
But business analysts cannot use Athena — they need a BI tool like Tableau, Power BI,
or Amazon QuickSight. These tools require a proper database connection (JDBC/ODBC),
not an S3 query API.

Additionally, your analysts' most common queries are:
- "What was total revenue per product last month?"
- "Which customers have spent > $1,000 lifetime?"
- "What is the daily revenue trend for the last 30 days?"

These queries run in 45 seconds on Athena (it scans CSV/Parquet from S3 fresh each time).
Business analysts run each query 50 times per day. 45s × 50 = 37 minutes wasted daily.
On Redshift, these queries complete in < 1 second.

**Goal:** Load processed S3 Parquet data into Redshift Serverless as a proper warehouse:
- Create columnar tables with DISTKEY and SORTKEY for query optimization
- Bulk-load data using the COPY command (parallel, fast, handles TB-scale)
- Run sub-second analytical SQL queries
- Connect BI tools via standard JDBC/ODBC
- Use Redshift Spectrum to query S3 data without loading (hybrid approach)

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════════════
 INPUT — Processed S3 Parquet (from Projects 9.1–9.6)
═══════════════════════════════════════════════════════════════════════════
Location:  s3://BUCKET/processed/orders/
Format:    Parquet (snappy compressed, partitioned by year/month/day)
Schema:    order_id, customer_id, order_date, product_id,
           quantity, unit_price, total_amount, status, region

═══════════════════════════════════════════════════════════════════════════
 STEP 1 — Setup (redshift_operations.py setup)
═══════════════════════════════════════════════════════════════════════════
Creates:
  Schema:  analytics
  Table 1: analytics.fact_orders
    DISTKEY: customer_id  (co-locate joined rows)
    SORTKEY: order_date, region  (range query optimization)
    Encoding: zstd + az64 (columnar compression)

  Table 2: analytics.dim_date
    DISTSTYLE ALL  (small table — replicate to all nodes)
    SORTKEY: full_date
    Contains: date_key, full_date, year, quarter, month, day_name,
              is_weekend, is_holiday

═══════════════════════════════════════════════════════════════════════════
 STEP 2 — Load (redshift_operations.py load)
═══════════════════════════════════════════════════════════════════════════
Runs:
  COPY analytics.fact_orders
  FROM 's3://BUCKET/processed/orders/'
  IAM_ROLE 'arn:aws:iam::ACCOUNT:role/handson-redshift-role'
  FORMAT AS PARQUET
  COMPUPDATE OFF   (skip compression analysis — already set in DDL)
  STATUPDATE ON    (update statistics for query planner)

  Then: VACUUM SORT ONLY + ANALYZE

Output:
  fact_orders:  N rows loaded (all orders from S3 Parquet)
  Rows in table = number of rows in source Parquet files

═══════════════════════════════════════════════════════════════════════════
 STEP 3 — Query (redshift_operations.py query / report)
═══════════════════════════════════════════════════════════════════════════
4 analytical queries run against fact_orders:

Query 1: Daily Revenue (last 30 days) — joined with dim_date
  Output: order_date, day_name, order_count, revenue, avg_order_value
  Example: 2024-01-15 | Monday | 42 orders | $1,234.56 | $29.39

Query 2: Top 10 Products by Revenue (last 3 months)
  Output: product_id, order_count, units_sold, total_revenue, avg_price
  Example: PROD-A001 | 234 orders | 468 units | $6,789.00 | $29.00

Query 3: Customer LTV — Top 20 repeat customers
  Output: customer_id, total_orders, lifetime_value, avg_order_value,
          first_order_date, last_order_date, customer_age_days
  Example: CUST-007 | 12 orders | $892.50 | $74.38 | 2024-01-05 | 2024-03-22 | 77

Query 4: Revenue by Region (last month)
  Output: region, order_count, unique_customers, total_revenue,
          avg_order_value, cancellations, cancellation_rate_pct
  Example: US-West | 234 | 198 | $6,890.00 | $29.44 | 12 | 5.13%
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain the difference between a data lake (S3+Athena) and a data warehouse (Redshift)
- [ ] Create a Redshift Serverless namespace and workgroup via Console and CLI
- [ ] Understand DISTSTYLE, DISTKEY, and SORTKEY and when to use each
- [ ] Create columnar tables with proper encoding (zstd, az64)
- [ ] Run the COPY command to bulk-load Parquet from S3
- [ ] Understand COMPUPDATE, STATUPDATE, VACUUM, and ANALYZE
- [ ] Write and run multi-table analytical SQL queries on Redshift
- [ ] Connect to Redshift via psycopg2 (Python) and psql (CLI)
- [ ] Use Redshift Data API (query without managing connections)
- [ ] Set up Redshift Spectrum for hybrid S3+warehouse queries
- [ ] Calculate Redshift Serverless cost (RPU-hours)

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│               REDSHIFT SERVERLESS DATA WAREHOUSE                         │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  S3: processed/orders/*.parquet   (input — from Glue ETL/dbt)   │   │
│  └─────────────────────┬────────────────────────────────────────────┘   │
│                        │  COPY command (parallel bulk load via IAM role) │
│                        ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  REDSHIFT SERVERLESS                                             │   │
│  │                                                                  │   │
│  │  Namespace: handson-namespace                                    │   │
│  │    Database: analytics                                           │   │
│  │      analytics.fact_orders                                       │   │
│  │        DISTKEY(customer_id)  SORTKEY(order_date, region)        │   │
│  │        zstd + az64 columnar encoding                            │   │
│  │                                                                  │   │
│  │      analytics.dim_date                                          │   │
│  │        DISTSTYLE ALL  (replicated to all compute nodes)         │   │
│  │        SORTKEY(full_date)                                        │   │
│  │                                                                  │   │
│  │  Workgroup: handson-workgroup                                    │   │
│  │    Base capacity: 8 RPU (auto-scales up to 512 RPU)             │   │
│  │    Port: 5439 | SSL required                                     │   │
│  └─────────────────────┬────────────────────────────────────────────┘   │
│                        │                                                 │
│         ┌──────────────┴──────────────────────────────────┐            │
│         ▼                                                  ▼            │
│  ┌─────────────────────────┐      ┌─────────────────────────────────┐  │
│  │  redshift_operations.py │      │  BI Tools                       │  │
│  │  (Python + psycopg2)    │      │  Amazon QuickSight              │  │
│  │  setup / load / report  │      │  Tableau, Power BI              │  │
│  │  Query results printed  │      │  Connect via JDBC/ODBC:5439     │  │
│  └─────────────────────────┘      └─────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  REDSHIFT SPECTRUM (optional — hybrid queries)                   │   │
│  │  External schema → Glue Catalog → S3 raw data                   │   │
│  │  Query S3 without loading: SELECT * FROM spectrum.orders         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **Amazon Redshift Serverless** | Columnar warehouse — namespace + workgroup | ❌ $0.36/hr for 8 RPU |
| **Amazon S3** | Source data for COPY command | ✅ 5 GB free |
| **AWS IAM** | Role allowing Redshift to read S3 | ✅ Free |
| **AWS Glue Data Catalog** | External schema for Spectrum | ✅ 1M objects free |
| **Amazon VPC** | Redshift deployed in private subnets | ✅ Free |
| **AWS Secrets Manager** | Store Redshift password securely | ❌ $0.40/secret/month |
│  │  Workgroup: handson-workgroup  (8 RPU base, auto-scales)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts Explained

**Data Lake vs Data Warehouse:**
```
Data Lake (S3 + Athena — Projects 9.1–9.8):
  + Any format: CSV, JSON, Parquet
  + Infinite scale, cheap storage
  + Schema-on-read: define schema at query time
  - Query speed: seconds to minutes (scans S3 fresh each time)
  - No JDBC/ODBC: can't connect Tableau directly
  - Better for: data science, ML, raw exploration

Data Warehouse (Redshift — this project):
  + Sub-second queries: data pre-loaded, columnar indexed
  + JDBC/ODBC: Tableau, Power BI, QuickSight connect directly
  + Schema-on-write: typed columns, constraints, compression
  - Costs more: ~$0.36/hr minimum while running
  - Better for: business dashboards, recurring analytics reports
```

**Columnar Storage — why Redshift is fast:**
```
Row storage (PostgreSQL, MySQL):
  Row 1: [ORD-001, CUST-1, 2024-01-15, PROD-A, 2, 14.99, 29.98, shipped, US-West]
  Row 2: [ORD-002, CUST-2, 2024-01-15, PROD-B, 1, 49.99, 49.99, pending, US-East]
  Query: SELECT SUM(total_amount) → must read ALL bytes of every row

Columnar storage (Redshift):
  total_amount column: [29.98, 49.99, 19.99, ...]  ← stored together, compressed
  Query: SELECT SUM(total_amount) → reads ONLY total_amount bytes
  + Better compression (similar values together)
  + 10–100x faster for aggregation queries
```

**DISTKEY — controls data distribution across nodes:**
```
DISTKEY (customer_id):
  All rows with same customer_id → same Redshift compute node
  Benefit: JOIN ON customer_id requires NO cross-node data movement
  Use when: the column is frequently used in JOINs

DISTSTYLE ALL (dim_date):
  Entire table replicated to EVERY node
  Use for: small dimension tables (< 1M rows) that are joined frequently
  Benefit: every node has local copy — no network transfer for JOINs

DISTSTYLE EVEN:
  Rows distributed round-robin (balanced load)
  Use when: no clear join key or table is rarely joined
```

**SORTKEY — controls on-disk ordering:**
```
SORTKEY (order_date, region):
  Rows stored sorted by order_date, then region on each node
  When query has: WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'
  Redshift zone maps know: "block 5 contains dates 2024-01-10 to 2024-01-20"
  → Skip all blocks outside the date range → much faster range queries

Rule: choose SORTKEY based on your most common WHERE clause columns
```

**COPY command — bulk load:**
```
Why COPY instead of INSERT:
  INSERT: one row at a time → 1M rows = 1M round trips → hours
  COPY:   parallel bulk load from S3 → all nodes read simultaneously → minutes

COPY syntax:
  COPY table_name (col1, col2, ...)
  FROM 's3://bucket/prefix/'     -- reads ALL files in prefix
  IAM_ROLE 'arn:...'             -- role with s3:GetObject permission
  FORMAT AS PARQUET              -- Parquet includes schema → auto-mapping
  COMPUPDATE OFF                 -- skip compression analysis (already set in DDL)
  STATUPDATE ON;                 -- update statistics for query planner
```

### Best Practices Followed

- **Redshift Serverless** — no cluster management, pay per RPU-second used
- **DISTKEY = customer_id** — most JOIN queries are customer-centric
- **SORTKEY = order_date, region** — most WHERE clauses filter by date/region
- **zstd + az64 encoding** — best compression for string + numeric columns
- **DISTSTYLE ALL for dim_date** — small table, referenced in every query
- **COPY with PARQUET** — schema from file, fast parallel load
- **VACUUM + ANALYZE after load** — reclaim space, update query statistics
- **SSL required** — `sslmode='require'` in psycopg2 connection
- **IAM role for COPY** — no access keys needed, role-based S3 access

---

## 3. Prerequisites

### 3.1 AWS Account Setup
- Active AWS account
- **Region:** `us-east-1` (N. Virginia)
- VPC with private subnets (Redshift Serverless requirement)
- S3 bucket with `processed/orders/` Parquet data (from Projects 9.1–9.6)

> **⚠️ Cost Warning:** Redshift Serverless costs **$0.36/hr for 8 RPU**.
> A 2-hour lab = ~$0.72. Pause the workgroup when not in use.
> Athena is cheaper for ad-hoc queries — use Redshift only when you need
> sub-second responses or BI tool connectivity.

### 3.2 IAM Permissions Required (for YOUR user)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["redshift-serverless:*", "redshift-data:*", "redshift:*"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole","iam:AttachRolePolicy","iam:PassRole",
                 "iam:GetRole","iam:DeleteRole","iam:DetachRolePolicy"],
      "Resource": "arn:aws:iam::*:role/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["ec2:CreateSecurityGroup","ec2:AuthorizeSecurityGroupIngress",
                 "ec2:DescribeSecurityGroups","ec2:DescribeVpcs","ec2:DescribeSubnets"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET","arn:aws:s3:::YOUR_BUCKET/*"]
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) |
|------|---------|------------------|
| Python | >= 3.9 | `winget install Python.Python.3.11` |
| psycopg2-binary | latest | `pip install psycopg2-binary` |
| boto3 | latest | `pip install boto3` |
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` |
| psql (optional) | latest | Download PostgreSQL client |

### 3.4 Environment Variables (PowerShell)

```powershell
$env:AWS_REGION         = "us-east-1"
$env:ACCOUNT            = aws sts get-caller-identity --query Account --output text
$env:BUCKET             = "handson-data-lake-$env:ACCOUNT"
$env:REDSHIFT_HOST      = ""   # set after workgroup is created
$env:REDSHIFT_PORT      = "5439"
$env:REDSHIFT_DB        = "analytics"
$env:REDSHIFT_USER      = "admin"
$env:REDSHIFT_PASSWORD  = "Admin@1234!"   # change this
$env:IAM_ROLE_ARN       = ""   # set after IAM role is created
$env:S3_BUCKET          = $env:BUCKET
```

### 3.5 Estimated AWS Cost

| Activity | Duration | Cost |
|----------|----------|------|
| Workgroup running (8 RPU) | 1 hour | ~$0.36 |
| 2-hour lab session | 2 hours | ~$0.72 |
| Storage (< 1 GB) | 1 month | ~$0.02 |
| **Typical session** | | **~$0.75** |

> **Pause or delete workgroup immediately after learning** — costs $0.36/hr continuously.

---

## 4. Project Folder Structure

```
project_9.9_redshift/
│
├── GUIDE.md                    ← This comprehensive guide (you are here)
├── README.md                   ← Quick start and key concepts
├── steps.md                    ← CLI/SQL commands reference (PowerShell)
├── steps_awsconsoleui.md       ← Console UI steps (improved template)
├── verify.md                   ← Verification checklist + commands
├── cost_estimate.md            ← RPU pricing + comparison
│
├── code/
│   └── redshift_operations.py  ← Python: setup tables, COPY from S3,
│                                  run analytical queries, print report
│
├── docs/
│   └── architecture.md         ← Columnar storage, DISTKEY/SORTKEY, Spectrum
│
└── terraform/
    └── main.tf                 ← Redshift Serverless namespace + workgroup +
                                   security group + IAM role (reference)
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `code/redshift_operations.py` | 4 commands: `setup` (create tables), `load` (COPY from S3), `query` (run analytical SQL), `report` (formatted output) |
| `docs/architecture.md` | Columnar storage advantage, DISTKEY/SORTKEY explained, Spectrum hybrid queries |
| `terraform/main.tf` | Namespace (`handson-namespace`), workgroup (`handson-workgroup`, 8 RPU), security group (port 5439), IAM role |

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `redshift-serverless:CreateNamespace`, `redshift-serverless:CreateWorkgroup`
- ✅ Services enabled: Amazon Redshift — available in us-east-1
- ✅ VPC with private subnets exists
- ✅ S3 bucket with `processed/orders/` Parquet data

**Step 0.1: Verify Region and VPC**
1. AWS Console → top-right: confirm **us-east-1**
2. Search → **VPC** → verify default VPC + subnets exist
3. **If no VPC:** Use the default VPC (auto-exists in all regions)

**📸 Screenshot P0:** AWS Console showing us-east-1 + VPC console

---

#### Step 1 — Create IAM Role for Redshift S3 Access

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global)

**Step 1.1: Navigate and Verify**
1. Search → **IAM** → Roles → **Create role**
2. **Trusted entity:** AWS service → scroll to **Redshift** → **Redshift - Customizable**
3. Click **Next**

**Step 1.2: Attach Policies**

**Decision Point 1:** S3 access scope
| Option | Access | For This Project |
|--------|--------|-----------------|
| AmazonS3ReadOnlyAccess | All S3 buckets | ✅ Simple for learning |
| Custom policy on specific bucket | Least privilege | ✅ Production best practice |

1. Search and attach: **AmazonS3ReadOnlyAccess**
2. Search and attach: **AWSGlueConsoleFullAccess** (needed for Spectrum)
3. Click **Next**

**Step 1.3: Configure Role Details**

| Field | Value |
|-------|-------|
| Role name | `handson-redshift-role` |
| Description | `Allows Redshift Serverless to read S3 and Glue Catalog` |

4. Click **Create role**
5. Copy the **Role ARN** — needed for COPY command

**📸 Screenshot 1a:** IAM role `handson-redshift-role` with S3 + Glue policies

---

#### Step 2 — Create Redshift Serverless Namespace

**Prerequisites Check:**
- ✅ Required permissions: `redshift-serverless:CreateNamespace`
- ✅ IAM role `handson-redshift-role` created
- ✅ Strong password ready (min 8 chars, upper+lower+number+special)

**Step 2.1: Navigate and Verify**
1. Search → **Amazon Redshift** → left sidebar → **Serverless dashboard**
2. **Expected View:** Redshift Serverless setup page or dashboard
3. Click **Create workgroup** (this creates both namespace and workgroup together)

**Step 2.2: Make Selections — Namespace**

**Decision Point 1:** Namespace purpose
| Option | For This Project |
|--------|-----------------|
| New namespace | ✅ First time setup |
| Existing namespace | ❌ N/A for new deployment |

**Step 2.3: Configure Namespace**

| Field | Value | Explanation |
|-------|-------|-------------|
| Namespace name | `handson-namespace` | Logical container for the database |
| Admin user name | `admin` | Superuser login |
| Admin password | `Admin@1234!` | Must have upper, lower, number, special |
| Database name | `analytics` | Created automatically in namespace |

**Step 2.4: Associate IAM Role**
1. Expand **Default IAM role** section
2. Select `handson-redshift-role`

**📸 Screenshot 2a:** Namespace configuration with `analytics` database and IAM role

---

#### Step 3 — Create Redshift Serverless Workgroup

**Prerequisites Check:**
- ✅ Namespace configuration ready
- ✅ VPC and subnets selected

**Step 3.1: Configure Workgroup**

| Field | Value | Explanation |
|-------|-------|-------------|
| Workgroup name | `handson-workgroup` | Compute layer name |
| Base RPU | **8** | Minimum (cheapest) — $0.36/hr |
| Publicly accessible | **Off** | Keep in VPC (security best practice) |

**Decision Point 1:** RPU capacity
| RPUs | Use Case | Cost/hr | For This Project |
|------|---------|---------|-----------------|
| **8** | Learning, small data | $0.36 | ✅ Minimum for demos |
| 16 | Dev/test | $0.72 | ❌ Overkill |
| 32 | Production light | $1.44 | ❌ Not needed |

**Step 3.2: Configure Network**

1. VPC: select **default VPC** (or your custom VPC)
2. Subnets: select **2–3 private subnets** (different AZs)
3. Security group: click **Create new** or select existing

**If creating new security group:**
- Name: `handson-redshift-sg`
- Inbound rule: Type=Custom TCP, Port=5439, Source=Your VPC CIDR (e.g. `172.31.0.0/16`)

**Step 3.3: Review and Create**
1. Review all settings
2. Click **Create workgroup**
3. **Expected:** Status = **Creating** → **Available** (takes 5–10 minutes)

**Troubleshooting:**
- "Cannot create workgroup — insufficient capacity": Try a different AZ/subnet
- "Password policy violation": Must include uppercase, lowercase, number, special char
- Status stays Creating > 15 min: Check CloudTrail for errors

**📸 Screenshot 3a:** Redshift Serverless workgroup `handson-workgroup` Status = **Available**

**Step 3.4: Get the Endpoint**
1. Click on `handson-workgroup`
2. **Expected View:** Endpoint section showing the host URL
3. Copy: `handson-workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com`
4. Port: `5439`

**📸 Screenshot 3b:** Workgroup details showing endpoint URL

---

#### Step 4 — Run Python Operations Locally

**Step 4.1: Install Dependencies and Set Environment**
```powershell
pip install psycopg2-binary boto3

$env:REDSHIFT_HOST     = "handson-workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com"
$env:REDSHIFT_USER     = "admin"
$env:REDSHIFT_PASSWORD = "Admin@1234!"
$env:REDSHIFT_DB       = "analytics"
$env:S3_BUCKET         = "handson-data-lake-YOUR_ACCOUNT_ID"
$env:IAM_ROLE_ARN      = "arn:aws:iam::YOUR_ACCOUNT:role/handson-redshift-role"
```

**Step 4.2: Create Tables**
```powershell
python code\redshift_operations.py setup
```
**Expected:**
```
Creating schema: analytics  ✓
Creating table: analytics.fact_orders  ✓
Creating table: analytics.dim_date  ✓
dim_date populated  ✓
Setup complete
```

**Step 4.3: Load Data from S3**
```powershell
python code\redshift_operations.py load
```
**Expected:**
```
Source: s3://handson-data-lake-.../processed/orders/
Running COPY command...
✓ Load complete — 1,000 total rows in fact_orders
VACUUM SORT ONLY  ✓
ANALYZE  ✓
```

**Step 4.4: Run Analytics Report**
```powershell
python code\redshift_operations.py report
```
**Expected:** Formatted tables showing daily revenue, top products, customer LTV, regional performance

**📸 Screenshot 4a:** Terminal showing COPY command success + row count
**📸 Screenshot 4b:** Terminal showing analytics report output

---

#### Step 5 — Query Redshift via Query Editor v2

**Step 5.1: Navigate to Query Editor**
1. Redshift console → left sidebar → **Query editor v2**
2. **Expected View:** SQL editor interface
3. Connect: select workgroup `handson-workgroup` → database `analytics` → user `admin`

**Step 5.2: Run Revenue Query**
```sql
SELECT
    product_id,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(total_amount) AS total_revenue
FROM analytics.fact_orders
WHERE status != 'cancelled'
GROUP BY product_id
ORDER BY total_revenue DESC
LIMIT 10;
```
Note the execution time shown — should be < 1 second.

**📸 Screenshot 5a:** Redshift Query Editor v2 showing query results + execution time

---

## 5B. AWS CLI Method

### Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.9_redshift

$REGION     = "us-east-1"
$ACCOUNT    = aws sts get-caller-identity --query Account --output text
$BUCKET     = "handson-data-lake-$ACCOUNT"
$NS_NAME    = "handson-namespace"
$WG_NAME    = "handson-workgroup"
$ROLE_NAME  = "handson-redshift-role"
$DB         = "analytics"
$ADMIN_USER = "admin"
$ADMIN_PASS = "Admin@1234!"   # change this

# Get VPC and subnet info
$VPC_ID = aws ec2 describe-vpcs `
  --query "Vpcs[?IsDefault==\`true\`].VpcId" --output text
$SUBNET_IDS = (aws ec2 describe-subnets `
  --filters "Name=vpc-id,Values=$VPC_ID" `
  --query "Subnets[0:2].SubnetId" --output text) -split "`t"

Write-Host "Account: $ACCOUNT | VPC: $VPC_ID"
Write-Host "Subnets: $($SUBNET_IDS -join ', ')"
```

---

### Phase 1 — Create IAM Role

```powershell
# Trust policy for Redshift
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"redshift.amazonaws.com"},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\redshift-trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\redshift-trust.json" `
  --description "Redshift Serverless S3 and Glue access"

# Attach managed policies
aws iam attach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
aws iam attach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME `
  --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"
```

---

### Phase 2 — Create Security Group

```powershell
$SG_ID = aws ec2 create-security-group `
  --group-name "handson-redshift-sg" `
  --description "Redshift Serverless port 5439" `
  --vpc-id $VPC_ID `
  --query "GroupId" --output text

# Allow Redshift port from VPC CIDR
$VPC_CIDR = aws ec2 describe-vpcs --vpc-ids $VPC_ID `
  --query "Vpcs[0].CidrBlock" --output text
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID `
  --protocol tcp --port 5439 --cidr $VPC_CIDR

Write-Host "Security Group: $SG_ID | Allows port 5439 from $VPC_CIDR"
```

---

### Phase 3 — Create Redshift Serverless Namespace

```powershell
aws redshift-serverless create-namespace `
  --namespace-name $NS_NAME `
  --admin-username $ADMIN_USER `
  --admin-user-password $ADMIN_PASS `
  --db-name $DB `
  --iam-roles $ROLE_ARN `
  --tags "Key=Project,Value=handson"

# Wait for AVAILABLE
Write-Host "Waiting for namespace..."
for ($i=0; $i -lt 20; $i++) {
  $ST = aws redshift-serverless get-namespace `
    --namespace-name $NS_NAME --query "namespace.status" --output text
  Write-Host "Status: $ST"
  if ($ST -eq "AVAILABLE") { break }
  Start-Sleep -Seconds 15
}
```

---

### Phase 4 — Create Redshift Serverless Workgroup

```powershell
aws redshift-serverless create-workgroup `
  --namespace-name $NS_NAME `
  --workgroup-name $WG_NAME `
  --base-capacity 8 `
  --subnet-ids $SUBNET_IDS `
  --security-group-ids $SG_ID `
  --publicly-accessible false `
  --tags "Key=Project,Value=handson"

# Wait for AVAILABLE (5–10 minutes)
Write-Host "Waiting for workgroup (5-10 min)..."
for ($i=0; $i -lt 40; $i++) {
  $ST = aws redshift-serverless get-workgroup `
    --workgroup-name $WG_NAME --query "workgroup.status" --output text
  Write-Host "[$i] Status: $ST"
  if ($ST -eq "AVAILABLE") { break }
  Start-Sleep -Seconds 15
}

# Get endpoint
$ENDPOINT = aws redshift-serverless get-workgroup `
  --workgroup-name $WG_NAME `
  --query "workgroup.endpoint.address" --output text
Write-Host "Endpoint: $ENDPOINT"
```

---

### Phase 5 — Create Tables + Load Data (Python)

```powershell
pip install psycopg2-binary boto3

$env:REDSHIFT_HOST     = $ENDPOINT
$env:REDSHIFT_USER     = $ADMIN_USER
$env:REDSHIFT_PASSWORD = $ADMIN_PASS
$env:REDSHIFT_DB       = $DB
$env:S3_BUCKET         = $BUCKET
$env:IAM_ROLE_ARN      = $ROLE_ARN

# Create schema + fact_orders + dim_date tables
python code\redshift_operations.py setup
# Expected: ✓ Schema ready, ✓ fact_orders ready, ✓ dim_date ready

# Load from S3 via COPY
python code\redshift_operations.py load
# Expected: ✓ Load complete — N rows in fact_orders

# Run all analytical queries
python code\redshift_operations.py report
# Expected: formatted revenue, products, customer LTV, regional tables
```

---

### Phase 6 — Query via Redshift Data API (no connection needed)

```powershell
# Use Data API instead of psycopg2 (no VPC tunnel needed from local)
$QID = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT product_id, COUNT(*) as orders, SUM(total_amount) as revenue FROM analytics.fact_orders GROUP BY product_id ORDER BY revenue DESC LIMIT 5;" `
  --query "Id" --output text

Start-Sleep -Seconds 5

# Check status
aws redshift-data describe-statement --id $QID `
  --query "{Status:Status,RowCount:ResultRows,Duration:Duration}"
# Expected: Status=FINISHED

# Get results
aws redshift-data get-statement-result --id $QID `
  --query "Records[*][0:3][*].stringValue"
# Expected: product rows with revenue values

# Run Customer LTV query
$QID2 = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT customer_id, COUNT(DISTINCT order_id) AS orders, SUM(total_amount) AS ltv FROM analytics.fact_orders WHERE status != 'cancelled' GROUP BY customer_id ORDER BY ltv DESC LIMIT 10;" `
  --query "Id" --output text

Start-Sleep -Seconds 5
aws redshift-data get-statement-result --id $QID2 `
  --query "Records[*][0:3][*].stringValue"
```

---

### Phase 7 — Redshift Spectrum (Query S3 Without Loading)

```powershell
# Run via Data API — create external schema pointing to Glue Catalog
$QID_SPEC = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "CREATE EXTERNAL SCHEMA IF NOT EXISTS spectrum FROM DATA CATALOG DATABASE 'handson_data_lake' IAM_ROLE '$ROLE_ARN' CREATE EXTERNAL DATABASE IF NOT EXISTS;" `
  --query "Id" --output text
Start-Sleep -Seconds 10

# Query S3 Parquet directly from Redshift (no COPY needed)
$QID3 = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT product_id, SUM(total_amount) as s3_revenue FROM spectrum.orders GROUP BY product_id ORDER BY s3_revenue DESC LIMIT 5;" `
  --query "Id" --output text
Start-Sleep -Seconds 15
aws redshift-data get-statement-result --id $QID3 `
  --query "Records[*][0:2][*].stringValue"
# Expected: product revenue from S3 Parquet (no data loaded to Redshift)
```

---

## 6. Code Deep Dive

### `code/redshift_operations.py` — Line by Line

**Connection configuration:**
```python
def get_connection_config() -> dict:
    return {
        "host":     os.environ["REDSHIFT_HOST"],
        "port":     int(os.environ.get("REDSHIFT_PORT", "5439")),
        "dbname":   os.environ.get("REDSHIFT_DB", "dev"),
        "user":     os.environ["REDSHIFT_USER"],
        "password": os.environ["REDSHIFT_PASSWORD"],
        "connect_timeout": 30,
        "sslmode": "require",   # Always SSL for Redshift
    }
```
- `sslmode="require"` — Redshift mandates SSL. Without this, connection is rejected.
- `connect_timeout=30` — fail fast if the endpoint is unreachable (VPC/SG issue).
- All config from env vars — no secrets in code. Safe to commit to Git.

---

**Context manager pattern:**
```python
@contextmanager
def get_connection():
    conn = psycopg2.connect(**config)
    try:
        yield conn
        conn.commit()     # Auto-commit on success
    except Exception:
        conn.rollback()   # Auto-rollback on any error
        raise
    finally:
        conn.close()      # Always close — no connection leaks
```
- `@contextmanager` makes `with get_connection() as conn:` syntax work cleanly.
- Commit/rollback guarantee: DDL (`CREATE TABLE`) and DML (`COPY`) are all atomic.
- `conn.close()` in `finally` — runs even if an exception is raised — prevents connection pool exhaustion.

---

**fact_orders DDL — encoding explained:**
```sql
order_id    VARCHAR(50)  NOT NULL ENCODE zstd,
order_date  DATE         NOT NULL ENCODE az64,
total_amount DECIMAL(12,2) NOT NULL ENCODE az64,
status      VARCHAR(20)  NOT NULL ENCODE zstd,
```
- `ENCODE zstd` — Zstandard compression for string columns. ~3–5x compression ratio.
- `ENCODE az64` — AZ64 for numeric/date columns. Faster than zstd for numbers, better ratio.
- Why set encoding explicitly? If omitted, Redshift uses `RAW` (no compression) until ANALYZE runs. Explicit is always better.

---

**DISTKEY / SORTKEY choice:**
```sql
DISTSTYLE KEY
DISTKEY (customer_id)          -- customer queries are most common
SORTKEY (order_date, region);  -- WHERE order_date BETWEEN ... AND region='US'
```
- `DISTSTYLE KEY` + `DISTKEY(customer_id)`: all rows for a customer go to the same node.
  When you `JOIN fact_orders ON customer_id`, no network transfer needed — data is co-located.
- `SORTKEY(order_date, region)`: rows physically ordered by date, then region.
  Redshift zone maps track min/max per 1MB block → date range queries skip irrelevant blocks.
- Why NOT `DISTKEY(order_id)`? order_id is unique — every row goes to a different node → random distribution, no co-location benefit.

---

**COPY command:**
```python
copy_sql = f"""
COPY analytics.fact_orders (order_id, customer_id, ...)
FROM '{s3_path}'
IAM_ROLE '{iam_role_arn}'
FORMAT AS PARQUET
COMPUPDATE OFF
STATUPDATE ON;
"""
```
- `FROM 's3://bucket/prefix/'` — reads ALL Parquet files in prefix, in parallel.
  Each Redshift node reads a subset of files simultaneously → linear scalability.
- `IAM_ROLE` — role with `s3:GetObject`. No access keys in SQL statements.
- `FORMAT AS PARQUET` — Parquet files include schema. Redshift maps columns by name automatically.
- `COMPUPDATE OFF` — skip automatic compression analysis (we set encoding in DDL). Saves time.
- `STATUPDATE ON` — update table statistics after load. The query planner uses these to pick optimal join/sort strategies.

---

**VACUUM + ANALYZE:**
```python
execute_sql(conn, "VACUUM SORT ONLY analytics.fact_orders;")
execute_sql(conn, "ANALYZE analytics.fact_orders;")
```
- `VACUUM SORT ONLY` — re-sorts rows by SORTKEY after bulk load.
  COPY inserts data in S3 file order, not SORTKEY order. VACUUM fixes this.
  "SORT ONLY" = faster than full VACUUM (skip space reclaim for fresh load).
- `ANALYZE` — collects column statistics (distinct values, histograms).
  Without ANALYZE, query planner may choose a hash join when a merge join is faster.
  Run after every large COPY.

---

**Analytical queries explained:**
```python
"daily_revenue": {
    "sql": """
        SELECT o.order_date, d.day_name, COUNT(DISTINCT o.order_id),
               SUM(o.total_amount), AVG(o.total_amount)
        FROM analytics.fact_orders o
        JOIN analytics.dim_date d ON d.full_date = o.order_date
        WHERE o.order_date >= DATEADD(day, -30, CURRENT_DATE)
          AND o.status != 'cancelled'
        GROUP BY o.order_date, d.day_name
        ORDER BY o.order_date DESC LIMIT 30;
    """
}
```
- `JOIN analytics.dim_date` — dim_date has `DISTSTYLE ALL`, so every node has a local copy. Zero network transfer for this join.
- `DATEADD(day, -30, CURRENT_DATE)` — Redshift SQL function, not standard SQL.
- `WHERE status != 'cancelled'` — applies before GROUP BY, reduces rows processed.
- `COUNT(DISTINCT order_id)` — counts unique orders per day. `DISTINCT` is more expensive than COUNT(*) but more accurate if there are duplicates.

---

**dim_date population:**
```python
populate_sql = """
    INSERT INTO analytics.dim_date
    SELECT ...
    FROM (SELECT DATEADD(day, seq, '2020-01-01') AS d
          FROM (SELECT ROW_NUMBER() OVER () - 1 AS seq
                FROM stl_scan LIMIT 4018))
    WHERE NOT EXISTS (SELECT 1 FROM analytics.dim_date WHERE full_date = d::DATE);
"""
```
- Generates 4,018 dates (2020–2030) using Redshift's internal `stl_scan` system table.
- `NOT EXISTS` check — idempotent. Safe to run multiple times without duplicates.
- Why a date dimension? Enables `JOIN ON order_date = full_date` to get `day_name`, `is_weekend`, `quarter` — avoiding repeated CASE/EXTRACT logic in every query.

### Common Mistakes and Fixes

| Mistake | Error | Fix |
|---------|-------|-----|
| Wrong sslmode | Connection refused | Set `sslmode='require'` |
| COPY without IAM role | `S3ServiceException` | Create role + attach S3ReadOnly |
| DISTKEY on unique column | Poor distribution | Use customer_id or product_id |
| Forget ANALYZE after COPY | Slow queries | Always run `ANALYZE table;` |
| `COMPUPDATE ON` (default) | Slow COPY | Set `COMPUPDATE OFF` when encoding set in DDL |
| Serverless in public subnet | VPC routing error | Use private subnets with NAT gateway |
| Workgroup not AVAILABLE | "workgroup not found" | Check status with `get-workgroup` CLI call |

---

## 7. Verification & Validation

### 7.1 AWS Console Verification

| Check | Navigation | Expected |
|-------|-----------|----------|
| Namespace | Redshift → Serverless → Namespaces | `handson-namespace` Status = Available |
| Workgroup | Redshift → Serverless → Workgroups | `handson-workgroup` Status = Available |
| Endpoint | Workgroup → Details | Endpoint URL shown (port 5439) |
| Query Editor | Redshift → Query Editor v2 | Can run `SELECT 1;` |
| Tables | Query Editor → Schema browser → analytics | `fact_orders`, `dim_date` visible |
| Row count | `SELECT COUNT(*) FROM analytics.fact_orders` | > 0 after COPY |
| IAM role | IAM → Roles → `handson-redshift-role` | S3ReadOnly + GlueConsole attached |

### 7.2 CLI Verification

```powershell
Write-Host "=== REDSHIFT VERIFICATION ===" -ForegroundColor Cyan

# 1. Workgroup status
aws redshift-serverless get-workgroup --workgroup-name $WG_NAME `
  --query "workgroup.{Status:status,Endpoint:endpoint.address,Port:endpoint.port}"
# Expected: status=AVAILABLE, port=5439

# 2. Namespace status
aws redshift-serverless get-namespace --namespace-name $NS_NAME `
  --query "namespace.{Status:status,DB:dbName,Admin:adminUsername}"
# Expected: status=AVAILABLE, DB=analytics

# 3. Row count via Data API
$QID = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT COUNT(*) as rows, SUM(total_amount) as revenue FROM analytics.fact_orders;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
aws redshift-data get-statement-result --id $QID `
  --query "Records[0][*].longValue"
# Expected: [row_count, total_revenue_cents]

# 4. dim_date populated
$QID2 = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT COUNT(*) FROM analytics.dim_date;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
aws redshift-data get-statement-result --id $QID2 `
  --query "Records[0][0].longValue"
# Expected: ~4018 (2020-01-01 to 2030-12-31)

Write-Host "=== COMPLETE ===" -ForegroundColor Green
```

### 7.3 Verification Checklist

- [ ] Namespace `handson-namespace` Status = AVAILABLE
- [ ] Workgroup `handson-workgroup` Status = AVAILABLE
- [ ] Endpoint URL populated (format: `...redshift-serverless.amazonaws.com`)
- [ ] IAM role `handson-redshift-role` has S3ReadOnly + GlueConsole policies
- [ ] `redshift_operations.py setup` completes without errors
- [ ] `analytics.fact_orders` table exists with DISTKEY/SORTKEY
- [ ] `analytics.dim_date` table exists with ~4018 rows
- [ ] `redshift_operations.py load` COPY succeeds, rows > 0
- [ ] `redshift_operations.py report` prints 4 query result tables
- [ ] Redshift Data API query returns results (no VPN/psql needed)

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During Operations

**During workgroup creation (5–10 minutes):**
- Redshift provisions compute nodes inside your VPC
- Security group rules applied — only port 5439 from VPC CIDR allowed
- IAM role association gives Redshift S3 read permission

**During COPY command:**
- Each Redshift node reads a subset of S3 files in parallel
- For 1,000 rows (tiny dataset): completes in ~3 seconds
- For 1 TB of Parquet: would complete in ~5–10 minutes (vs hours with INSERT)
- Watch `STL_LOAD_COMMITS` system table to see per-file load history

**During analytical queries:**
- First query after idle: may take 2–3 seconds (cache warm-up)
- Subsequent queries: typically < 500ms for aggregations on < 10M rows
- Queries with SORTKEY WHERE clause: significantly faster than without

### 8.2 Billing Observations

```
Redshift Serverless billing model:
  Charge: per RPU-second while queries are running
  1 RPU-second = $0.045/3600 = $0.0000125

  8 RPU base capacity:
  - Idle (no queries): $0/hour (scales to 0 automatically)
  - Running queries:   8 RPU × $0.045/RPU-hr = $0.36/hour

  10-minute lab session:
  - setup (30s):  8 × 0.0083h × $0.045 = $0.003
  - COPY (60s):   8 × 0.0167h × $0.045 = $0.006
  - queries (2m): 8 × 0.0333h × $0.045 = $0.012
  Total: ~$0.02 for this demo
```

### 8.3 Data Lake vs Data Warehouse — When to Use Each

| Factor | Use Athena (Data Lake) | Use Redshift (Warehouse) |
|--------|----------------------|------------------------|
| Query frequency | < 10/day | 100s/day |
| Query speed needed | Seconds OK | Sub-second required |
| BI tool connection | Not needed | Tableau/QuickSight |
| Data freshness | Query S3 directly | Load fresh data via COPY |
| Cost at low volume | Cheaper ($0.000001/query) | Expensive ($0.36/hr) |
| Cost at high volume | Expensive (TB scans) | Fixed cluster cost |
| Schema flexibility | Schema-on-read | Schema-on-write |

### 8.4 Redshift Serverless vs Provisioned Cluster

| Factor | Serverless | Provisioned |
|--------|-----------|-------------|
| Setup time | 5–10 min | 10–15 min |
| Management | None | Node type, count |
| Scaling | Auto | Manual resizing |
| Cost | Per RPU-second | Per node-hour always-on |
| Min cost | $0 (idle) | ~$180/mo (dc2.large) |
| Best for | Variable workloads, learning | Steady-state production |

---

## 9. Screenshots Guidance

| # | What to Capture | When |
|---|----------------|------|
| SS-01 | AWS Console with us-east-1 + VPC confirmed | Phase 0 |
| SS-02 | IAM role `handson-redshift-role` with 2 policies | Step 1 |
| SS-03 | Redshift Serverless namespace creation form | Step 2 |
| SS-04 | Workgroup creation form with 8 RPU, private subnets | Step 3 |
| SS-05 | Workgroup Status = **Available** (green) | Step 3.3 |
| SS-06 | Workgroup details showing endpoint URL | Step 3.4 |
| SS-07 | Terminal: `setup` output — 4 checks ✓ | Step 4.2 |
| SS-08 | Terminal: `load` output — COPY complete + row count | Step 4.3 |
| SS-09 | Terminal: `report` output — revenue tables | Step 4.4 |
| SS-10 | Redshift Query Editor v2 — query result + execution time | Step 5.2 |
| SS-11 | Redshift Query Editor — schema browser showing tables | Step 5.1 |
| SS-12 | CLI: Data API query result (top products) | Phase 6 |

**Total: 12 screenshots**

---

## 10. Cleanup Steps

> **Important:** Redshift Serverless charges $0.36/hr while active. Delete after learning.

### 10.1 AWS Console Cleanup

1. **Workgroup:** Redshift → Serverless → Workgroups → `handson-workgroup` → **Delete**
   - Must delete workgroup BEFORE namespace
2. **Namespace:** Redshift → Serverless → Namespaces → `handson-namespace` → **Delete**
   - Confirm deletion (this deletes the database + all tables)
3. **Security group:** VPC → Security Groups → `handson-redshift-sg` → **Delete**
4. **IAM role:** IAM → Roles → `handson-redshift-role` → **Delete**

### 10.2 CLI Cleanup (PowerShell)

```powershell
# 1. Delete workgroup first (namespace cannot be deleted while workgroup exists)
aws redshift-serverless delete-workgroup --workgroup-name $WG_NAME
Write-Host "Deleting workgroup (2-3 min)..."
for ($i=0; $i -lt 20; $i++) {
  $ST = aws redshift-serverless get-workgroup `
    --workgroup-name $WG_NAME --query "workgroup.status" --output text 2>&1
  if ($ST -match "ResourceNotFoundException") { Write-Host "✅ Workgroup deleted"; break }
  Write-Host "Status: $ST"
  Start-Sleep -Seconds 15
}

# 2. Delete namespace
aws redshift-serverless delete-namespace --namespace-name $NS_NAME
Write-Host "Deleting namespace..."
Start-Sleep -Seconds 30

# 3. Delete security group
aws ec2 delete-security-group --group-id $SG_ID
Write-Host "✅ Security group deleted"

# 4. Delete IAM role (detach policies first)
aws iam detach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
aws iam detach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ IAM role deleted"

Write-Host "✅ All resources cleaned up"
```

### 10.3 Verify Cleanup

```powershell
aws redshift-serverless list-workgroups `
  --query "workgroups[?workgroupName=='$WG_NAME']"
# Expected: []

aws redshift-serverless list-namespaces `
  --query "namespaces[?namespaceName=='$NS_NAME']"
# Expected: []

Write-Host "✅ Cleanup verified — $0.00/hr going forward"
```

---

## Quick Reference Card

```
SETUP:
  pip install psycopg2-binary boto3
  $env:REDSHIFT_HOST = "workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com"
  $env:REDSHIFT_USER = "admin"  |  $env:REDSHIFT_PASSWORD = "Admin@1234!"
  $env:REDSHIFT_DB = "analytics"  |  $env:S3_BUCKET = "handson-data-lake-ACCOUNT"
  $env:IAM_ROLE_ARN = "arn:aws:iam::ACCOUNT:role/handson-redshift-role"

RUN:
  python code\redshift_operations.py setup   # create tables
  python code\redshift_operations.py load    # COPY from S3
  python code\redshift_operations.py report  # print analytics

DATA API (no connection setup):
  aws redshift-data execute-statement \
    --workgroup-name handson-workgroup --database analytics \
    --sql "SELECT COUNT(*) FROM analytics.fact_orders;"

SPECTRUM (query S3 without loading):
  CREATE EXTERNAL SCHEMA spectrum FROM DATA CATALOG DATABASE 'handson_data_lake'
  IAM_ROLE 'arn:...' CREATE EXTERNAL DATABASE IF NOT EXISTS;
  SELECT * FROM spectrum.orders LIMIT 10;

KEY SQL:
  COPY table FROM 's3://bucket/prefix/' IAM_ROLE 'arn:...' FORMAT AS PARQUET;
  VACUUM SORT ONLY analytics.fact_orders;
  ANALYZE analytics.fact_orders;

CLEANUP (saves $0.36/hr):
  aws redshift-serverless delete-workgroup --workgroup-name handson-workgroup
  aws redshift-serverless delete-namespace --namespace-name handson-namespace
  aws iam delete-role --role-name handson-redshift-role

COST: $0.36/hr for 8 RPU | Scale to 0 when idle (Serverless)
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.9_redshift*

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
