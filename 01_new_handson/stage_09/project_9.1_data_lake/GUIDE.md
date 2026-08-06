# Complete Implementation Guide — Project 9.1: Data Lake Architecture on AWS

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 3–4 hours

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Concepts](#2-architecture--concepts)
3. [Prerequisites](#3-prerequisites)
4. [Project Folder Structure](#4-project-folder-structure)
5. [Hands-on Implementation](#5-hands-on-implementation)
   - [A. AWS Console Method](#5a-aws-management-console-method)
   - [B. AWS CLI Method](#5b-aws-cli-method)
   - [C. Terraform Method](#5c-terraform-method)
6. [Code Deep Dive](#6-code-deep-dive)
7. [Verification & Validation](#7-verification--validation)
8. [Observations & Learning Notes](#8-observations--learning-notes)
9. [Screenshots Guidance](#9-screenshots-guidance)
10. [Cleanup Steps](#10-cleanup-steps)

---

## 1. Project Overview

### Project Title
**Building a Production Data Lake on AWS with S3, Glue, Athena, and Lake Formation**

### Business / Problem Statement

Imagine you work at an e-commerce company. Every day, millions of orders, clicks,
and customer events are generated. The data sits in separate databases, files, and
systems — nobody can answer the question "What were our top 10 products last month?"
without waiting days for an analyst to manually pull reports.

A **data lake** solves this by:
- Centralising all raw data in one place (S3)
- Making it queryable with SQL (Athena) — no ETL needed to start
- Organising it into zones (raw → processed → curated) as it gets refined
- Controlling who can see what (Lake Formation)

This is not a toy project. Netflix, Airbnb, and Uber all run data lakes on S3 with
this exact pattern.

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain what a data lake is and how it differs from a data warehouse
- [ ] Create an S3 bucket with a multi-zone (raw/processed/curated/archive) structure
- [ ] Configure S3 lifecycle policies for automatic data tiering
- [ ] Use AWS Glue Crawlers to automatically discover schema from files
- [ ] Query CSV and Parquet data with Athena SQL — no server needed
- [ ] Register a data lake with Lake Formation for access control
- [ ] Understand why Parquet is 10x cheaper to query than CSV in Athena
- [ ] Deploy the entire data lake with Terraform (IaC)

---

## 2. Architecture & Concepts

### Core AWS Services Involved

| Service | Role | Free Tier? |
|---------|------|-----------|
| **Amazon S3** | Storage for all data zones | ✅ 5 GB free |
| **AWS Glue Data Catalog** | Metadata store (schema, table definitions) | ✅ 1M objects free |
| **AWS Glue Crawler** | Auto-discovers schema from S3 files | ❌ $0.44/DPU-hour |
| **Amazon Athena** | Serverless SQL engine over S3 | ❌ $5/TB scanned |
| **AWS Lake Formation** | Fine-grained access control | ✅ Free |
| **AWS IAM** | Roles and permissions | ✅ Free |

### Service Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAKE ARCHITECTURE                        │
│                                                                  │
│  ┌──────────┐    ┌─────────────────────────────────────────┐   │
│  │  Data    │    │              Amazon S3                   │   │
│  │ Sources  │───▶│  raw/   processed/   curated/  archive/ │   │
│  │          │    │  (CSV)   (Parquet)   (Parquet)  (Glacier)│   │
│  └──────────┘    └────────────────┬────────────────────────┘   │
│                                   │                              │
│                          ┌────────▼────────┐                    │
│                          │  AWS Glue        │                    │
│                          │  Crawler         │                    │
│                          │  (schema scan)   │                    │
│                          └────────┬────────┘                    │
│                                   │                              │
│                          ┌────────▼────────┐                    │
│                          │  Glue Data       │                    │
│                          │  Catalog         │                    │
│                          │  (metadata)      │                    │
│                          └────────┬────────┘                    │
│                    ┌──────────────┴──────────────┐              │
│                    │                             │              │
│           ┌────────▼────────┐          ┌─────────▼───────┐     │
│           │  Amazon Athena  │          │  Lake Formation  │     │
│           │  (SQL queries)  │          │  (access control)│     │
│           └─────────────────┘          └─────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### High-Level Architecture Explanation

**Step 1 — Data Landing (S3 Raw Zone)**
Data arrives from source systems (applications, databases, IoT devices) and lands
in the `raw/` zone of S3 exactly as-is. Never modify raw data. It is your source
of truth and audit trail.

**Step 2 — Schema Discovery (Glue Crawler)**
AWS Glue Crawler scans S3 files, detects column names and data types, and writes
that metadata to the Glue Data Catalog. After crawling, you have a "table" you can
query — even though the data is still just files in S3.

**Step 3 — Metadata Store (Glue Data Catalog)**
The Glue Data Catalog is like a database of databases. It stores table definitions
(column names, types, partition keys) and points to where the actual data lives in S3.
Athena, Glue ETL jobs, and EMR all read from the same Catalog.

**Step 4 — Querying (Athena)**
Athena is a serverless SQL engine. You write SQL, it reads the Catalog to find where
the data is, scans only the relevant S3 files, and returns results. You pay per TB
scanned — so partitioning and Parquet format are critical for cost control.

**Step 5 — Access Control (Lake Formation)**
Lake Formation sits on top of S3 and the Catalog to enforce who can see which databases,
tables, columns, or even rows. You register your S3 bucket with Lake Formation and then
grant permissions through its UI instead of complex IAM policies.

### S3 Zone Strategy (Best Practice)

```
s3://handson-data-lake-123456789/
├── raw/                          ← Landing zone: original files, never modified
│   └── orders/
│       └── year=2024/month=01/day=15/
│           └── orders.csv
├── processed/                    ← Cleaned data: Parquet format, partitioned
│   └── orders/
│       └── year=2024/month=01/
│           └── orders.parquet
├── curated/                      ← Business-ready: aggregated, enriched
│   └── daily_revenue/
│       └── year=2024/month=01/
│           └── daily_revenue.parquet
└── archive/                      ← Historical: moved to S3 Glacier after 90 days
    └── orders_2023/
```

### Best Practices Followed

- **Immutable raw zone** — never overwrite or delete raw files
- **Parquet format** in processed/curated zones — columnar, compressed, 10x cheaper
- **Hive-style partitioning** — `year=YYYY/month=MM/day=DD` enables partition pruning
- **Encryption at rest** — AES-256 server-side encryption on S3
- **Versioning** — S3 versioning protects against accidental deletes
- **Lifecycle policies** — auto-tier to Glacier after 90 days (cost saving)
- **1 GB Athena scan limit** — prevents accidental expensive queries

---

## 3. Prerequisites

### AWS Account Setup
- Active AWS account (Free Tier is sufficient for this project)
- Region: **us-east-1 (N. Virginia)** — used throughout this guide
- Billing alert set at $5 (recommended for learners)

### IAM Permissions Required

Your IAM user/role needs these permissions. If you are using an admin account for
learning, you already have these. For production, use the least-privilege policy below.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataLake",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket", "s3:DeleteBucket", "s3:GetBucketPolicy",
        "s3:PutBucketPolicy", "s3:GetBucketVersioning", "s3:PutBucketVersioning",
        "s3:PutLifecycleConfiguration", "s3:GetLifecycleConfiguration",
        "s3:PutEncryptionConfiguration", "s3:GetEncryptionConfiguration",
        "s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"
      ],
      "Resource": ["arn:aws:s3:::handson-data-lake-*", "arn:aws:s3:::handson-data-lake-*/*",
                   "arn:aws:s3:::handson-athena-*",    "arn:aws:s3:::handson-athena-*/*"]
    },
    {
      "Sid": "GlueFullAccess",
      "Effect": "Allow",
      "Action": ["glue:*"],
      "Resource": "*"
    },
    {
      "Sid": "AthenaFullAccess",
      "Effect": "Allow",
      "Action": ["athena:*"],
      "Resource": "*"
    },
    {
      "Sid": "LakeFormation",
      "Effect": "Allow",
      "Action": ["lakeformation:*"],
      "Resource": "*"
    },
    {
      "Sid": "IAMForGlue",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:PassRole",
                 "iam:GetRole", "iam:DeleteRole", "iam:DetachRolePolicy"],
      "Resource": "arn:aws:iam::*:role/handson-glue-*"
    }
  ]
}
```

### Local Machine Requirements

| Tool | Version | Purpose | Install Command |
|------|---------|---------|----------------|
| AWS CLI | v2.x | Deploy and manage AWS resources | See below |
| Terraform | >= 1.5.0 | Infrastructure as Code | See below |
| Python | >= 3.9 | Run helper scripts | `python3 --version` |
| pip | latest | Install Python packages | `pip3 --version` |
| Git | >= 2.x | Version control | `git --version` |
| VS Code | latest | Code editor (optional but recommended) | code.visualstudio.com |

### Install AWS CLI v2

```bash
# macOS
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Linux (x86_64)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Windows — download from:
# https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify
aws --version
# Expected: aws-cli/2.x.x Python/3.x.x
```

### Install Terraform

```bash
# macOS (Homebrew)
brew tap hashicorp/tap && brew install hashicorp/tap/terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | \
  sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Windows — download from: https://developer.hashicorp.com/terraform/downloads

# Verify
terraform version
# Expected: Terraform v1.x.x
```

### Install Python Dependencies

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake
pip3 install boto3 pandas pyarrow
```

### Configure AWS CLI

```bash
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region name: us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
# Expected output:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

### Environment Variables Setup

```bash
# Set these in your shell (add to ~/.bashrc or ~/.zshrc for persistence)
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export DATA_LAKE_BUCKET="handson-data-lake-${AWS_ACCOUNT_ID}"
export ATHENA_RESULTS_BUCKET="handson-athena-results-${AWS_ACCOUNT_ID}"

# Verify
echo "Account: $AWS_ACCOUNT_ID"
echo "Bucket:  $DATA_LAKE_BUCKET"
```

---

## 4. Project Folder Structure

```
project_9.1_data_lake/
│
├── GUIDE.md                    ← This comprehensive guide (you are here)
├── README.md                   ← Quick overview and architecture summary
├── steps.md                    ← Condensed step-by-step commands
├── verify.md                   ← Verification checklist and CLI checks
├── cost_estimate.md            ← Estimated AWS costs
│
├── terraform/
│   ├── main.tf                 ← All AWS resources (S3, Glue, Athena, IAM)
│   ├── variables.tf            ← Input variables with defaults
│   ├── outputs.tf              ← Output values (bucket name, workgroup, etc.)
│   └── terraform.tfvars        ← Your custom variable values (gitignored)
│
├── code/
│   ├── data_lake_setup.py      ← Python: create zones, register with Lake Formation
│   ├── upload_sample_data.py   ← Python: generate and upload test data to S3
│   ├── run_athena_query.py     ← Python: run Athena queries and print results
│   └── convert_to_parquet.py  ← Python: convert CSV to Parquet (with partitioning)
│
├── data/
│   ├── sample_orders.csv       ← Sample e-commerce orders dataset
│   ├── sample_customers.csv    ← Sample customer data
│   └── sample_products.csv     ← Sample product catalog
│
└── docs/
    ├── architecture.md         ← Detailed architecture notes
    └── data_dictionary.md      ← Column definitions for sample datasets
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `terraform/main.tf` | Single Terraform file with all AWS resources — S3 bucket, Glue crawler, Athena workgroup, IAM role |
| `terraform/variables.tf` | Configurable parameters: region, project name, lifecycle days |
| `terraform/outputs.tf` | Values exported after apply: bucket name, database name, workgroup |
| `code/data_lake_setup.py` | Creates S3 zone prefixes, Glue databases, registers Lake Formation |
| `code/upload_sample_data.py` | Generates fake e-commerce data and uploads partitioned files |
| `code/run_athena_query.py` | Submits SQL to Athena and returns results as a formatted table |
| `data/sample_orders.csv` | 1000-row CSV for testing crawlers and Athena queries |
| `docs/architecture.md` | Deep-dive on data lake patterns and zone strategy |

---

## 5. Hands-on Implementation

---

### 5A. AWS Management Console Method

This method walks through every click in the AWS Console. It's slower than CLI/Terraform
but teaches you what each option means.

---

#### Step A1 — Create the S3 Data Lake Bucket

1. Open the [AWS Console](https://console.aws.amazon.com) and sign in
2. In the search bar at the top, type **S3** and press Enter
3. Click the orange **Create bucket** button (top-right)

**Fill in the form:**

| Field | Value | Why |
|-------|-------|-----|
| Bucket name | `handson-data-lake-YOUR_ACCOUNT_ID` | Must be globally unique — use your 12-digit account ID |
| AWS Region | `US East (N. Virginia) us-east-1` | Closest to Glue/Athena default region |
| Object Ownership | ACLs disabled (recommended) | S3 best practice — use bucket policies instead |
| Block Public Access | ✅ All 4 options checked | Data lake should NEVER be public |
| Bucket Versioning | Enable | Protects against accidental overwrites |
| Default encryption | Amazon S3 managed keys (SSE-S3) | Encrypts all data at rest for free |

4. Click **Create bucket** at the bottom
5. You will see: *"Successfully created bucket handson-data-lake-XXXX"*

**📸 Screenshot here:** S3 bucket created confirmation banner

---

#### Step A2 — Create the Zone Folder Structure

S3 doesn't have real folders — it uses key prefixes. We create "folders" by uploading
placeholder files or just using the console folder creation tool.

1. Click on your new bucket name `handson-data-lake-XXXX`
2. Click **Create folder**
3. Name: `raw` → Click **Create folder**
4. Repeat for: `processed`, `curated`, `archive`, `athena-results`

You should now see 5 folders in your bucket.

**📸 Screenshot here:** S3 bucket showing all 5 zone folders

---

#### Step A3 — Configure S3 Lifecycle Policy

Lifecycle policies automatically move old data to cheaper storage classes.

1. Stay in your bucket, click the **Management** tab
2. Click **Create lifecycle rule**
3. Fill in:

**Rule 1 — Archive old raw data:**
| Field | Value |
|-------|-------|
| Lifecycle rule name | `archive-raw-data` |
| Filter type | Prefix — enter `raw/` |
| Transition to | S3 Glacier Flexible Retrieval |
| Days after object creation | `90` |

4. Click **Create rule**

**Rule 2 — Expire temporary files:**
| Field | Value |
|-------|-------|
| Lifecycle rule name | `expire-temp-data` |
| Filter type | Prefix — enter `temp/` |
| Expire current versions | After `7` days |

5. Click **Create rule**

**📸 Screenshot here:** Lifecycle rules tab showing both rules

---

#### Step A4 — Create Glue IAM Role

AWS Glue needs permission to read from S3 and write to the Data Catalog.

1. Open **IAM** in the console (search bar → IAM)
2. Left sidebar → **Roles** → **Create role**
3. Trusted entity type: **AWS service**
4. Use case: scroll down and select **Glue** → click **Next**
5. Search for and attach these policies:
   - `AWSGlueServiceRole` ← managed policy for all Glue operations
6. Click **Next**
7. Role name: `handson-glue-role`
8. Click **Create role**

Now add the S3 access inline policy:
1. Click on `handson-glue-role`
2. Click **Add permissions** → **Create inline policy**
3. Click **JSON** tab and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::handson-data-lake-YOUR_ACCOUNT_ID",
        "arn:aws:s3:::handson-data-lake-YOUR_ACCOUNT_ID/*"
      ]
    }
  ]
}
```

4. Policy name: `glue-s3-access`
5. Click **Create policy**

**📸 Screenshot here:** IAM role `handson-glue-role` with attached policies

---

#### Step A5 — Create Glue Data Catalog Database

The Glue Database is a namespace that groups related tables.

1. Open **AWS Glue** (search bar → Glue)
2. Left sidebar → **Databases** (under Data Catalog)
3. Click **Add database**
4. Fill in:

| Field | Value |
|-------|-------|
| Name | `handson_data_lake` |
| Location | `s3://handson-data-lake-YOUR_ACCOUNT_ID/processed/` |
| Description | `Main database for handson data lake` |

5. Click **Create database**

Create two more databases for separation of zones:
- `raw_db` → location: `s3://...bucket.../raw/`
- `curated_db` → location: `s3://...bucket.../curated/`

**📸 Screenshot here:** Glue Databases list showing all 3 databases

---

#### Step A6 — Upload Sample Data to S3

Before running the crawler, we need data in S3.

1. On your local machine, create a sample CSV file:

```csv
order_id,customer_id,product_name,amount,order_date
ORD-001,CUST-101,Widget A,29.99,2024-01-15
ORD-002,CUST-102,Widget B,49.99,2024-01-15
ORD-003,CUST-101,Widget C,19.99,2024-01-16
ORD-004,CUST-103,Widget A,29.99,2024-01-16
ORD-005,CUST-104,Widget B,49.99,2024-01-17
```

Save as `orders.csv` on your desktop.

2. Back in S3, navigate to: `handson-data-lake-XXXX` → `raw/`
3. Click **Create folder**: `orders`
4. Inside `orders`, create folder structure: `year=2024` → `month=01` → `day=15`
5. Inside `day=15`, click **Upload** → drag your `orders.csv` → **Upload**

**What happened internally:**
- The S3 key is now: `raw/orders/year=2024/month=01/day=15/orders.csv`
- This Hive-style partition path (`year=2024/month=01/day=15`) is automatically
  recognized by Glue Crawler and Athena as partition columns
- Athena can now skip entire partitions when you add `WHERE year=2024 AND month=01`

**📸 Screenshot here:** S3 showing the uploaded file at the correct partition path

---

#### Step A7 — Create and Run Glue Crawler

The Glue Crawler reads your S3 files and automatically figures out the schema.

1. In AWS Glue → left sidebar → **Crawlers** → **Create crawler**
2. Click through the wizard:

**Step 1 — Set crawler properties:**
| Field | Value |
|-------|-------|
| Name | `handson-raw-crawler` |
| Description | `Discovers schema from raw S3 data` |

**Step 2 — Choose data sources:**
- Data source type: **S3**
- S3 path: `s3://handson-data-lake-YOUR_ACCOUNT_ID/raw/`
- Subsequent crawler runs: **Crawl all sub-folders**

**Step 3 — Configure security:**
- IAM role: `handson-glue-role` (the role we created)

**Step 4 — Set output and scheduling:**
- Target database: `raw_db`
- Table name prefix: leave empty
- Crawler schedule: **On demand** (for learning — run manually)

**Step 5 — Review and create**

3. After creation, click **Run crawler**
4. The crawler status changes: `Starting` → `Running` → `Ready`
5. This takes 1–2 minutes
6. When status = **Ready**, check the "Tables added" count (should be 1)

**What happened internally during the crawl:**
- Glue launched a small Spark job on managed infrastructure
- It read the file headers from `orders.csv` to detect column names
- It detected data types: `order_id` = string, `amount` = double
- It detected the partition keys from the folder structure: `year`, `month`, `day`
- It wrote a table definition to the Glue Data Catalog

**📸 Screenshot here:** Crawler run completed with "Tables added: 1"

---

#### Step A8 — Verify Table in Glue Data Catalog

1. Glue → **Tables** (left sidebar)
2. Select database: `raw_db`
3. You should see a table named `day=15` or `orders`
4. Click on the table to see:
   - Column names and data types
   - Partition keys (year, month, day)
   - S3 location
   - Input format (TextInputFormat for CSV)

**📸 Screenshot here:** Glue table details showing columns and partitions

---

#### Step A9 — Query Data with Athena

Now let's query the data using SQL — no server, no ETL.

1. Open **Amazon Athena** (search bar → Athena)
2. First-time setup: Click **Settings** → **Manage**
3. Query result location: `s3://handson-data-lake-YOUR_ACCOUNT_ID/athena-results/`
4. Click **Save**

5. Back in the **Query editor**:
6. Left panel → Database: select `raw_db`
7. You should see your `orders` table

8. In the query box, type and run:

```sql
-- Query 1: See all data
SELECT * FROM orders LIMIT 10;
```

Click the **Run** button (or press Ctrl+Enter)

Expected result:
```
order_id | customer_id | product_name | amount | order_date | year | month | day
ORD-001  | CUST-101    | Widget A     | 29.99  | 2024-01-15 | 2024 | 01    | 15
...
```

**Cost note:** This query scanned ~200 bytes. At $5/TB, the cost is $0.000001.

9. Try a partition-pruned query:

```sql
-- Query 2: Filter by partition (Athena skips other partitions)
SELECT order_id, product_name, amount
FROM orders
WHERE year = '2024' AND month = '01'
ORDER BY amount DESC;
```

**📸 Screenshot here:** Athena query editor with successful results

---

#### Step A10 — Register with Lake Formation (Optional but Important)

Lake Formation gives you column-level and row-level access control.

1. Open **AWS Lake Formation** (search bar → Lake Formation)
2. First time: you'll see a "Welcome" page → click **Get started**
3. Under **Data lake locations** → **Register location**
4. S3 path: `s3://handson-data-lake-YOUR_ACCOUNT_ID/`
5. IAM role: `handson-glue-role`
6. Click **Register location**

7. Now grant your own IAM user access to the database:
   - Left sidebar → **Data lake permissions** → **Grant**
   - IAM user/role: select your user
   - Database: `raw_db`
   - Permissions: **Select**, **Describe**
   - Click **Grant**

**📸 Screenshot here:** Lake Formation data lake location registered

---

### 5B. AWS CLI Method

This method uses the AWS CLI to create the same resources. Much faster once you know
what each command does. All commands assume `AWS_REGION=us-east-1` is set.

---

#### Step B1 — Set Variables

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUCKET="handson-data-lake-${AWS_ACCOUNT_ID}"
export ATHENA_BUCKET="handson-athena-results-${AWS_ACCOUNT_ID}"
export GLUE_ROLE="handson-glue-role"
export DB_NAME="handson_data_lake"
export CRAWLER_NAME="handson-raw-crawler"

echo "Account:  $AWS_ACCOUNT_ID"
echo "Bucket:   $BUCKET"
```

---

#### Step B2 — Create S3 Buckets

```bash
# Create data lake bucket
aws s3api create-bucket \
  --bucket $BUCKET \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Expected output:
# {
#     "Location": "http://handson-data-lake-123456789012.s3.amazonaws.com/"
# }

# NOTE: For us-east-1 specifically, omit --create-bucket-configuration:
# aws s3api create-bucket --bucket $BUCKET --region us-east-1

# Create Athena results bucket
aws s3api create-bucket \
  --bucket $ATHENA_BUCKET \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable versioning on data lake bucket
aws s3api put-bucket-versioning \
  --bucket $BUCKET \
  --versioning-configuration Status=Enabled

# Verify versioning is on
aws s3api get-bucket-versioning --bucket $BUCKET
# Expected: {"Status": "Enabled"}

# Enable encryption (AES-256)
aws s3api put-bucket-encryption \
  --bucket $BUCKET \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block all public access
aws s3api put-public-access-block \
  --bucket $BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "✅ S3 buckets created and secured"
```

---

#### Step B3 — Create S3 Lifecycle Policy

```bash
# Create lifecycle configuration JSON
cat > /tmp/lifecycle.json << 'EOF'
{
  "Rules": [
    {
      "ID": "archive-raw-data",
      "Status": "Enabled",
      "Filter": { "Prefix": "raw/" },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "ID": "expire-temp-data",
      "Status": "Enabled",
      "Filter": { "Prefix": "temp/" },
      "Expiration": { "Days": 7 }
    }
  ]
}
EOF

# Apply lifecycle configuration
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET \
  --lifecycle-configuration file:///tmp/lifecycle.json

# Verify lifecycle rules
aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET
# Expected: JSON showing 2 rules: archive-raw-data and expire-temp-data
```

---

#### Step B4 — Create IAM Role for Glue

```bash
# Create trust policy document (allows Glue service to assume this role)
cat > /tmp/glue-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name $GLUE_ROLE \
  --assume-role-policy-document file:///tmp/glue-trust.json \
  --description "Allows Glue to access S3 and Data Catalog"

# Expected output:
# {
#     "Role": {
#         "RoleName": "handson-glue-role",
#         "Arn": "arn:aws:iam::123456789012:role/handson-glue-role",
#         "CreateDate": "2024-01-15T10:00:00+00:00"
#     }
# }

# Attach the managed Glue service policy
aws iam attach-role-policy \
  --role-name $GLUE_ROLE \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

# Add inline S3 access policy
cat > /tmp/glue-s3.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*",
        "arn:aws:s3:::${ATHENA_BUCKET}",
        "arn:aws:s3:::${ATHENA_BUCKET}/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name $GLUE_ROLE \
  --policy-name glue-s3-access \
  --policy-document file:///tmp/glue-s3.json

# Verify role exists with correct policies
aws iam get-role --role-name $GLUE_ROLE \
  --query "Role.{Name:RoleName,ARN:Arn,Created:CreateDate}"

aws iam list-attached-role-policies --role-name $GLUE_ROLE \
  --query "AttachedPolicies[*].PolicyName"
# Expected: ["AWSGlueServiceRole"]

echo "✅ IAM role created: $GLUE_ROLE"
```

---

#### Step B5 — Create Glue Databases

```bash
# Create main database
aws glue create-database \
  --database-input '{
    "Name": "handson_data_lake",
    "Description": "Main data lake database",
    "LocationUri": "'"s3://${BUCKET}/processed/"'"
  }'

# Create raw database
aws glue create-database \
  --database-input '{
    "Name": "raw_db",
    "Description": "Raw zone database",
    "LocationUri": "'"s3://${BUCKET}/raw/"'"
  }'

# Create curated database
aws glue create-database \
  --database-input '{
    "Name": "curated_db",
    "Description": "Curated zone database",
    "LocationUri": "'"s3://${BUCKET}/curated/"'"
  }'

# Verify all databases
aws glue get-databases \
  --query "DatabaseList[*].{Name:Name,Location:LocationUri}" \
  --output table

# Expected output:
# -------------------------------------------------------
# |                    GetDatabases                      |
# +--------------------+---------------------------------+
# |  Name              |  Location                       |
# +--------------------+---------------------------------+
# |  handson_data_lake | s3://handson-data-lake-xxx/...  |
# |  raw_db            | s3://handson-data-lake-xxx/raw/ |
# |  curated_db        | s3://handson-data-lake-xxx/...  |
# +--------------------+---------------------------------+

echo "✅ Glue databases created"
```

---

#### Step B6 — Upload Sample Data

```bash
# Create local sample data directory
mkdir -p /tmp/data_lake_sample

# Generate orders CSV
cat > /tmp/data_lake_sample/orders.csv << 'EOF'
order_id,customer_id,product_name,amount,order_date
ORD-001,CUST-101,Widget A,29.99,2024-01-15
ORD-002,CUST-102,Widget B,49.99,2024-01-15
ORD-003,CUST-101,Widget C,19.99,2024-01-16
ORD-004,CUST-103,Widget A,29.99,2024-01-16
ORD-005,CUST-104,Widget B,49.99,2024-01-17
ORD-006,CUST-105,Widget C,19.99,2024-01-17
ORD-007,CUST-101,Widget A,29.99,2024-01-18
ORD-008,CUST-102,Widget B,49.99,2024-01-18
EOF

# Upload to partitioned raw zone
aws s3 cp /tmp/data_lake_sample/orders.csv \
  s3://$BUCKET/raw/orders/year=2024/month=01/day=15/orders.csv

# Expected output: upload: /tmp/.../orders.csv to s3://handson-data-lake-xxx/raw/orders/year=2024/month=01/day=15/orders.csv

# Verify the upload
aws s3 ls s3://$BUCKET/raw/orders/year=2024/month=01/day=15/
# Expected:
# 2024-01-15 10:00:00       280 orders.csv

# Check S3 object metadata
aws s3api head-object \
  --bucket $BUCKET \
  --key raw/orders/year=2024/month=01/day=15/orders.csv \
  --query "{ContentType:ContentType,Size:ContentLength,Encryption:ServerSideEncryption}"
# Expected: {"ContentType": "text/csv", "Size": 280, "Encryption": "AES256"}

echo "✅ Sample data uploaded to s3://$BUCKET/raw/orders/year=2024/month=01/day=15/"
```

---

#### Step B7 — Create and Run Glue Crawler

```bash
GLUE_ROLE_ARN=$(aws iam get-role --role-name $GLUE_ROLE --query "Role.Arn" --output text)

# Create crawler
aws glue create-crawler \
  --name $CRAWLER_NAME \
  --role $GLUE_ROLE_ARN \
  --database-name raw_db \
  --targets '{"S3Targets": [{"Path": "'"s3://${BUCKET}/raw/"'"}]}' \
  --schedule "cron(0 6 * * ? *)" \
  --configuration '{
    "Version": 1.0,
    "CrawlerOutput": {
      "Partitions": {"AddOrUpdateBehavior": "InheritFromTable"}
    }
  }'

# Verify crawler was created
aws glue get-crawler --name $CRAWLER_NAME \
  --query "Crawler.{Name:Name,State:State,Database:DatabaseName,Schedule:Schedule.ScheduleExpression}"
# Expected: State=READY

# Run the crawler manually (don't wait for schedule)
aws glue start-crawler --name $CRAWLER_NAME
echo "Crawler started. Waiting for completion (60-120 seconds)..."

# Poll until crawler is ready
while true; do
  STATE=$(aws glue get-crawler --name $CRAWLER_NAME \
    --query "Crawler.State" --output text)
  echo "$(date +%H:%M:%S) — Crawler state: $STATE"
  if [ "$STATE" = "READY" ]; then
    break
  fi
  sleep 10
done

# Check crawler results
aws glue get-crawler --name $CRAWLER_NAME \
  --query "Crawler.LastCrawl.{Status:Status,TablesCreated:TablesCreated,TablesUpdated:TablesUpdated,ErrorMessage:ErrorMessage}"
# Expected: {"Status": "SUCCEEDED", "TablesCreated": 1, "TablesUpdated": 0}

# List discovered tables
aws glue get-tables --database-name raw_db \
  --query "TableList[*].{Name:Name,Location:StorageDescriptor.Location,Columns:StorageDescriptor.Columns[*].Name}" \
  --output json

echo "✅ Crawler completed. Tables discovered in raw_db"
```

---

#### Step B8 — Create Athena Workgroup

```bash
# Create Athena workgroup with result location and scan limit
aws athena create-work-group \
  --name handson-data-lake \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "'"s3://${ATHENA_BUCKET}/results/"'"
    },
    "BytesScannedCutoffPerQuery": 1073741824,
    "EnforceWorkGroupConfiguration": true
  }' \
  --description "Data lake Athena workgroup"

# Verify workgroup
aws athena get-work-group --work-group handson-data-lake \
  --query "WorkGroup.{Name:Name,State:State,Config:Configuration}"
# Expected: State=ENABLED

echo "✅ Athena workgroup created: handson-data-lake"
```

---

#### Step B9 — Query Data with Athena CLI

```bash
# Run a SELECT query via CLI
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT order_id, product_name, amount FROM orders LIMIT 5;" \
  --query-execution-context "Database=raw_db" \
  --work-group handson-data-lake \
  --query "QueryExecutionId" --output text)

echo "Query started with ID: $QUERY_ID"

# Wait for query to complete
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
echo "Query completed"

# Check if it succeeded
aws athena get-query-execution --query-execution-id $QUERY_ID \
  --query "QueryExecution.{State:Status.State,Bytes:Statistics.DataScannedInBytes,Runtime:Statistics.TotalExecutionTimeInMillis}"
# Expected: {"State": "SUCCEEDED", "Bytes": 280, "Runtime": 1500}

# Get the results
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" \
  --output table
# Expected:
# |  order_id  |  product_name  |  amount  |
# |  ORD-001   |  Widget A      |  29.99   |
# ...

echo "✅ Athena query successful"
```

---

#### Step B10 — Register with Lake Formation

```bash
GLUE_ROLE_ARN=$(aws iam get-role --role-name $GLUE_ROLE --query "Role.Arn" --output text)

# Register S3 bucket as a Lake Formation data lake location
aws lakeformation register-resource \
  --resource-arn arn:aws:s3:::$BUCKET \
  --role-arn $GLUE_ROLE_ARN

# Verify registration
aws lakeformation list-resources \
  --query "ResourceInfoList[*].{Resource:ResourceArn,Role:RoleArn}"
# Expected: S3 bucket ARN listed

# Grant your IAM user SELECT permission on raw_db
YOUR_USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=$YOUR_USER_ARN \
  --resource '{"Database": {"Name": "raw_db"}}' \
  --permissions DESCRIBE ALTER CREATE_TABLE DROP

aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=$YOUR_USER_ARN \
  --resource '{"Table": {"DatabaseName": "raw_db", "TableWildcard": {}}}' \
  --permissions SELECT DESCRIBE

echo "✅ Lake Formation configured"
```

---

### 5C. Terraform Method

Terraform creates all the same resources as the Console and CLI methods, but in a
repeatable, version-controlled, and team-friendly way. One `terraform apply` builds
the entire data lake. One `terraform destroy` tears it all down.

---

#### Terraform Files

First create the supporting files that the existing `main.tf` needs:

**`terraform/variables.tf`**

```hcl
# terraform/variables.tf
# ─────────────────────────────────────────────────────────────────
# All configurable parameters for the data lake.
# Change these in terraform.tfvars — never hardcode values here.
# ─────────────────────────────────────────────────────────────────

variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix used in all resource names"
  type        = string
  default     = "handson"
}

variable "raw_lifecycle_glacier_days" {
  description = "Days after which raw/ objects transition to Glacier"
  type        = number
  default     = 90
}

variable "temp_lifecycle_expire_days" {
  description = "Days after which temp/ objects are permanently deleted"
  type        = number
  default     = 7
}

variable "athena_scan_limit_gb" {
  description = "Maximum GB per Athena query (cost protection)"
  type        = number
  default     = 1
}

variable "crawler_schedule" {
  description = "Cron expression for Glue crawler. Default: daily at 6am UTC"
  type        = string
  default     = "cron(0 6 * * ? *)"
}
```

**`terraform/outputs.tf`**

```hcl
# terraform/outputs.tf
# ─────────────────────────────────────────────────────────────────
# Values exported after terraform apply.
# Use: terraform output data_lake_bucket
# ─────────────────────────────────────────────────────────────────

output "data_lake_bucket" {
  description = "Name of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.bucket
}

output "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "athena_results_bucket" {
  description = "Name of the S3 bucket for Athena query results"
  value       = aws_s3_bucket.athena_results.bucket
}

output "glue_database" {
  description = "Name of the main Glue Data Catalog database"
  value       = aws_glue_catalog_database.data_lake.name
}

output "glue_role_arn" {
  description = "ARN of the IAM role used by Glue crawler"
  value       = aws_iam_role.glue.arn
}

output "glue_crawler_name" {
  description = "Name of the Glue crawler"
  value       = aws_glue_crawler.raw_data.name
}

output "athena_workgroup" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.data_lake.name
}

output "raw_zone_path" {
  description = "S3 path for the raw zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/raw/"
}

output "processed_zone_path" {
  description = "S3 path for the processed zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/processed/"
}

output "curated_zone_path" {
  description = "S3 path for the curated zone"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/curated/"
}
```

**`terraform/terraform.tfvars`** (your personal overrides — add to .gitignore)

```hcl
# terraform/terraform.tfvars
# ─────────────────────────────────────────────────────────────────
# Override default variable values here.
# This file is gitignored — do not commit it.
# ─────────────────────────────────────────────────────────────────

region  = "us-east-1"
project = "handson"

# For learning: keep lifecycle days short to avoid Glacier costs
raw_lifecycle_glacier_days = 90
temp_lifecycle_expire_days = 7

# Safety: limit Athena to 1 GB per query
athena_scan_limit_gb = 1
```

---

#### Step-by-Step Terraform Workflow

**Step C1 — Initialize Terraform**

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake\terraform

terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.31.0...
- Installed hashicorp/aws v5.31.0 (signed by HashiCorp)

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure.
```

What happened:
- Terraform downloaded the AWS provider plugin (~60 MB)
- Created `.terraform/` directory with provider binaries
- Created `.terraform.lock.hcl` with exact provider version (commit this to git)

---

**Step C2 — Preview Changes with terraform plan**

```bash
terraform plan -var-file="terraform.tfvars"
```

Expected output (condensed):
```
Terraform will perform the following actions:

  # aws_athena_workgroup.data_lake will be created
  + resource "aws_athena_workgroup" "data_lake" {
      + name = "handson-data-lake"
      + configuration {
          + bytes_scanned_cutoff_per_query = 1073741824
          + result_configuration {
              + output_location = (known after apply)
          }
      }
    }

  # aws_glue_catalog_database.data_lake will be created
  + resource "aws_glue_catalog_database" "data_lake" {
      + name = "handson_data_lake"
    }

  # aws_glue_crawler.raw_data will be created
  + resource "aws_glue_crawler" "raw_data" {
      + name          = "handson-raw-crawler"
      + database_name = "handson_data_lake"
      + schedule      = "cron(0 6 * * ? *)"
    }

  # aws_iam_role.glue will be created
  # aws_s3_bucket.athena_results will be created
  # aws_s3_bucket.data_lake will be created
  # aws_s3_bucket_lifecycle_configuration.data_lake will be created
  # ...

Plan: 12 to add, 0 to change, 0 to destroy.
```

Key things to note in the plan:
- `+` = will be created
- `~` = will be modified
- `-` = will be destroyed
- `(known after apply)` = value depends on another resource being created first (e.g., bucket name in the Athena result path)

---

**Step C3 — Apply (Deploy Everything)**

```bash
terraform apply -var-file="terraform.tfvars"
```

Terraform shows the plan again and asks:
```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

Type `yes` and press Enter.

Expected output (resources created one by one):
```
aws_s3_bucket.data_lake: Creating...
aws_s3_bucket.data_lake: Creation complete after 2s [id=handson-data-lake-123456789012]
aws_s3_bucket.athena_results: Creating...
aws_s3_bucket.athena_results: Creation complete after 2s [id=handson-athena-results-123456789012]
aws_s3_bucket_versioning.data_lake: Creating...
aws_s3_bucket_versioning.data_lake: Creation complete after 1s
aws_s3_bucket_server_side_encryption_configuration.data_lake: Creating...
aws_s3_bucket_server_side_encryption_configuration.data_lake: Creation complete after 1s
aws_iam_role.glue: Creating...
aws_iam_role.glue: Creation complete after 1s [id=handson-glue-role]
aws_iam_role_policy_attachment.glue_service: Creating...
aws_iam_role_policy.glue_s3: Creating...
aws_glue_catalog_database.data_lake: Creating...
aws_glue_catalog_database.data_lake: Creation complete after 0s [id=handson_data_lake]
aws_athena_workgroup.data_lake: Creating...
aws_athena_workgroup.data_lake: Creation complete after 1s [id=handson-data-lake]
aws_glue_crawler.raw_data: Creating...
aws_glue_crawler.raw_data: Creation complete after 1s [id=handson-raw-crawler]

Apply complete! Resources: 12 added, 0 changed, 0 destroyed.

Outputs:

athena_workgroup      = "handson-data-lake"
data_lake_bucket      = "handson-data-lake-123456789012"
glue_crawler_name     = "handson-raw-crawler"
glue_database         = "handson_data_lake"
glue_role_arn         = "arn:aws:iam::123456789012:role/handson-glue-role"
raw_zone_path         = "s3://handson-data-lake-123456789012/raw/"
```

**📸 Screenshot here:** `terraform apply` completion with all outputs shown

---

**Step C4 — Inspect Terraform State**

```bash
# List all resources Terraform is managing
terraform state list

# Expected:
# aws_athena_workgroup.data_lake
# aws_glue_catalog_database.data_lake
# aws_glue_crawler.raw_data
# aws_iam_role.glue
# aws_iam_role_policy.glue_s3
# aws_iam_role_policy_attachment.glue_service
# aws_s3_bucket.athena_results
# aws_s3_bucket.data_lake
# aws_s3_bucket_lifecycle_configuration.data_lake
# aws_s3_bucket_server_side_encryption_configuration.data_lake
# aws_s3_bucket_versioning.data_lake

# View details of a specific resource
terraform state show aws_s3_bucket.data_lake

# Get a specific output value
terraform output data_lake_bucket
# Expected: "handson-data-lake-123456789012"

# Run plan again to confirm no drift (changes should be empty)
terraform plan
# Expected: "No changes. Your infrastructure matches the configuration."
```

---

**Step C5 — Upload Sample Data and Run Crawler (after Terraform apply)**

```bash
BUCKET=$(terraform output -raw data_lake_bucket)
WORKGROUP=$(terraform output -raw athena_workgroup)
DATABASE=$(terraform output -raw glue_database)
CRAWLER=$(terraform output -raw glue_crawler_name)

# Upload sample data
aws s3 cp ../data/sample_orders.csv \
  s3://$BUCKET/raw/orders/year=2024/month=01/day=15/orders.csv

# Run crawler
aws glue start-crawler --name $CRAWLER
echo "Waiting for crawler..."
aws glue wait crawler-ready --crawler-name $CRAWLER
echo "Crawler done"

# Query with Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT * FROM orders LIMIT 5;" \
  --query-execution-context Database=$DATABASE \
  --work-group $WORKGROUP \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID

aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" \
  --output table
```

---

## 6. Code Deep Dive

### Understanding `terraform/main.tf` — Line by Line

#### Provider Block
```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
```
- `source = "hashicorp/aws"` — download the official AWS provider from HashiCorp's registry
- `version = "~> 5.0"` — use any version from 5.0 to < 6.0 (pessimistic constraint)
- This prevents breaking changes from major version upgrades

#### Data Source
```hcl
data "aws_caller_identity" "current" {}
```
- Not a resource — reads existing AWS data
- `aws_caller_identity` returns the current IAM user/role's Account ID
- Used as: `data.aws_caller_identity.current.account_id`
- This makes bucket names globally unique without hardcoding your account ID

#### S3 Bucket Resource
```hcl
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project}-data-lake-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.common_tags, { Name = "data-lake" })
}
```
- `resource "aws_s3_bucket"` — declares an S3 bucket
- `"data_lake"` — Terraform's local name (used to reference this resource elsewhere)
- `bucket` — actual S3 bucket name (must be globally unique across all AWS accounts)
- `merge(local.common_tags, { Name = "data-lake" })` — combines common tags with a specific Name tag

#### Lifecycle Configuration
```hcl
rule {
  id     = "archive-raw-data"
  status = "Enabled"
  filter { prefix = "raw/" }
  transition {
    days          = 90
    storage_class = "GLACIER"
  }
}
```
- `filter { prefix = "raw/" }` — only applies to objects under the `raw/` prefix
- `transition { days = 90, storage_class = "GLACIER" }` — after 90 days, move to Glacier
- Glacier costs $0.004/GB vs $0.023/GB for S3 Standard — 83% savings on archived data
- Objects in Glacier take 3–5 hours to retrieve (acceptable for archival data)

#### Glue IAM Trust Policy
```hcl
assume_role_policy = jsonencode({
  Version = "2012-10-17"
  Statement = [{
    Effect    = "Allow"
    Principal = { Service = "glue.amazonaws.com" }
    Action    = "sts:AssumeRole"
  }]
})
```
- `Principal = { Service = "glue.amazonaws.com" }` — only the Glue service can assume this role
- Without this, no one could use the role — not even your IAM user
- `sts:AssumeRole` — the action that switches identity to this role

#### Athena Scan Limit
```hcl
bytes_scanned_cutoff_per_query = 1073741824   # 1 GB limit
```
- `1073741824 = 1024³ = 1 GB` in bytes
- If a query would scan more than 1 GB, Athena cancels it automatically
- Protects against accidentally running `SELECT * FROM huge_table` which could cost $$$
- At $5/TB, scanning 1 GB costs $0.005 — this is your per-query maximum

### Understanding Partitioning

```
raw/orders/year=2024/month=01/day=15/orders.csv
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           These path segments are partition keys
```

When Glue Crawler scans this path, it creates a table with extra columns:
`year`, `month`, `day` — automatically extracted from the folder names.

When Athena runs:
```sql
SELECT * FROM orders WHERE year = '2024' AND month = '01'
```

Athena only reads files inside `year=2024/month=01/` — it completely skips
`year=2023/`, `year=2022/`, etc. This is called **partition pruning** and is
the single most important cost-saving technique for Athena.

Without partitioning: Athena scans ALL data every query → expensive
With partitioning: Athena only scans the requested date range → cheap

### CSV vs Parquet — Why It Matters

| Format | Structure | Compression | 1 TB at $5/TB |
|--------|-----------|-------------|--------------|
| CSV | Row-based | None | $5.00 |
| Parquet | Columnar | Snappy | $0.50 |

Example: you have a table with 100 columns. You query 3 of them.
- CSV: Athena reads all 100 columns from every row → scans full file
- Parquet: Athena reads only the 3 requested column files → scans ~3% of file

This is why the processed/ and curated/ zones use Parquet format.

----------------------------------------------------------------------------------------------------------------------------------------------------------

## 7. Verification & Validation

### 7.1 AWS Console Verification

| Resource | Navigation | Expected State |
|----------|-----------|---------------|
| S3 Bucket | S3 → Buckets | `handson-data-lake-XXXX` visible |
| S3 Versioning | Bucket → Properties | Versioning = Enabled |
| S3 Encryption | Bucket → Properties | Default encryption = SSE-S3 |
| S3 Zones | Bucket → Objects | raw/, processed/, curated/, archive/ |
| Lifecycle Rules | Bucket → Management | 2 rules: archive-raw-data, expire-temp-data |
| Glue Databases | Glue → Databases | raw_db, handson_data_lake, curated_db |
| Glue Crawler | Glue → Crawlers | handson-raw-crawler, Last run = SUCCEEDED |
| Glue Tables | Glue → Tables | orders table in raw_db |
| Athena Workgroup | Athena → Workgroups | handson-data-lake = ENABLED |
| IAM Role | IAM → Roles | handson-glue-role with AWSGlueServiceRole attached |

### 7.2 CLI Verification Commands

```bash
BUCKET=$(terraform output -raw data_lake_bucket 2>/dev/null || echo $DATA_LAKE_BUCKET)

# Check 1: S3 bucket exists and is secure
aws s3api get-bucket-encryption --bucket $BUCKET \
  --query "ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm"
# Expected: "AES256"

aws s3api get-bucket-versioning --bucket $BUCKET --query "Status"
# Expected: "Enabled"

aws s3api get-public-access-block --bucket $BUCKET \
  --query "PublicAccessBlockConfiguration"
# Expected: all 4 = true

# Check 2: All zones accessible
for zone in raw processed curated archive athena-results; do
  aws s3 ls s3://$BUCKET/ | grep $zone && echo "✅ $zone/ exists" || echo "⚠️  $zone/ empty"
done

# Check 3: Glue databases exist
aws glue get-databases --query "DatabaseList[*].Name" --output table

# Check 4: Crawler last run succeeded
aws glue get-crawler --name handson-raw-crawler \
  --query "Crawler.LastCrawl.{Status:Status,Tables:TablesCreated}"
# Expected: {"Status": "SUCCEEDED", "Tables": 1}

# Check 5: Athena workgroup active
aws athena get-work-group --work-group handson-data-lake \
  --query "WorkGroup.State"
# Expected: "ENABLED"

# Check 6: IAM role has correct policies
aws iam list-attached-role-policies --role-name handson-glue-role \
  --query "AttachedPolicies[*].PolicyName"
# Expected: ["AWSGlueServiceRole"]
```

### 7.3 Terraform State Verification

```bash
# All resources tracked
terraform state list | wc -l
# Expected: 11-13 resources

# No drift
terraform plan 2>&1 | tail -3
# Expected: "No changes. Your infrastructure matches the configuration."

# Outputs are correct
terraform output
# Expected: all 9 outputs with valid values
```

### 7.4 End-to-End Data Flow Test

```bash
# Full pipeline test: upload → crawl → query
BUCKET=$(terraform output -raw data_lake_bucket)

# 1. Upload test file
echo "id,name,val
1,test,100" > /tmp/e2e_test.csv
aws s3 cp /tmp/e2e_test.csv \
  s3://$BUCKET/raw/e2e_test/year=2024/month=01/day=01/test.csv
echo "✅ Step 1: Data uploaded"

# 2. Run crawler
aws glue start-crawler --name handson-raw-crawler
aws glue wait crawler-ready --crawler-name handson-raw-crawler
echo "✅ Step 2: Crawler completed"

# 3. Query with Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM e2e_test;" \
  --query-execution-context Database=raw_db \
  --work-group handson-data-lake \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID

RESULT=$(aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue" --output text)
echo "✅ Step 3: Athena query result = $RESULT"

# 4. Clean up test file
aws s3 rm s3://$BUCKET/raw/e2e_test/ --recursive
echo "✅ Step 4: Test data cleaned up"
```

### 7.5 Expected Successful Outputs Summary

```
S3 bucket encryption:     "AES256"
S3 bucket versioning:     "Enabled"
S3 zones:                 raw/ processed/ curated/ archive/ athena-results/
Glue databases:           raw_db  handson_data_lake  curated_db
Crawler last run:         SUCCEEDED, TablesCreated: 1
Athena workgroup state:   ENABLED
End-to-end query result:  1 (count of test record)
Terraform plan:           No changes
```

----------------------------------------------------------------------------------------------------------------------------------------------------------

## 8. Observations & Learning Notes

### What to Observe During Execution

**During `terraform apply`:**
- Resources are created in dependency order — S3 bucket before Glue crawler
  (crawler needs the bucket path to exist)
- `(known after apply)` in the plan resolves to real values after apply
- Glue crawler creation is near-instant; it only runs when triggered

**During Glue Crawler run:**
- Watch the console: Status changes: `Starting` → `Running` → `Stopping` → `Ready`
- The crawler is actually running a small Apache Spark job on managed infrastructure
- AWS bills for DPU-hours from when state = `Running` to `Ready`
- Crawling 1 CSV file: ~1 DPU for ~30 seconds = $0.00367

**During Athena query:**
- First query is slower (~3-5s) due to metadata loading
- Subsequent queries on the same table are faster (metadata cached)
- Check "Data scanned" in Athena results — lower is better
- A query with `WHERE year='2024'` scans less than without the filter

### Internal AWS Behavior

**S3 Consistency Model:**
- Since December 2020, S3 has strong read-after-write consistency
- After `aws s3 cp`, the file is immediately visible to all readers
- No eventual consistency delays for new uploads

**Glue Catalog and IAM:**
- The Glue Data Catalog is a regional service
- Cross-region catalog sharing requires Glue resource policies
- Lake Formation adds another permission layer ON TOP of IAM — both must allow

**Athena Query Execution:**
- Athena is built on Presto/Trino under the hood
- Each query spins up workers automatically — no cluster management
- Results are stored in your S3 athena-results/ bucket
- Results are kept for 45 days by default

### Resource Dependencies

```
aws_s3_bucket
    ↓
aws_s3_bucket_versioning
aws_s3_bucket_server_side_encryption_configuration
aws_s3_bucket_lifecycle_configuration
    ↓
aws_iam_role
    ↓
aws_iam_role_policy_attachment
aws_iam_role_policy
    ↓
aws_glue_catalog_database
    ↓
aws_glue_crawler
    ↓
aws_athena_workgroup (depends on athena_results S3 bucket)
```

Terraform automatically resolves this dependency graph using `depends_on` and
implicit references (when resource A references resource B's attribute, Terraform
knows B must be created before A).

### Billing Observations

- **S3 storage:** Free up to 5 GB. After that, $0.023/GB/month.
- **Glue Crawler:** Charged when running. 1 DPU = $0.44/hour. A 2-minute crawl = ~$0.015.
- **Athena:** $5/TB scanned. A 1 MB query costs $0.000005. Partitioning can reduce cost 99%.
- **Lake Formation:** Free. Only the underlying services (Glue, Athena) have costs.
- **CloudWatch Logs (Glue):** Minimal cost for log storage.

**Free Tier:** S3 5 GB, Glue Data Catalog 1M objects, first 1M Athena DML queries/month free.

### Performance Observations

- Parquet queries in Athena return ~10x faster than CSV for same data volume
- Partition pruning reduces data scanned by 90-99% for time-range queries
- Glue Crawler is NOT real-time — it runs on schedule or manually triggered
- For real-time schema updates, use Glue Auto Discover or manual `CREATE TABLE` in Athena

---

## 9. Screenshots Guidance

### Before Implementation
📸 1. AWS Console home page showing your account ID in the top-right corner
📸 2. Empty S3 bucket list (to show baseline state)
📸 3. Empty Glue Databases list

### During Setup (Console Method)
📸 4. S3 Create Bucket form filled in with correct values
📸 5. S3 Lifecycle rules configuration form
📸 6. IAM Create Role — trusted entity selection (Glue service)
📸 7. Glue Create Database form
📸 8. Glue Create Crawler — S3 target configuration
📸 9. Glue Crawler running (Status = RUNNING)

### After Successful Deployment
📸 10. S3 bucket with all 5 zone folders visible
📸 11. S3 bucket Properties tab showing Versioning=Enabled and Encryption=AES-256
📸 12. S3 Management tab showing 2 lifecycle rules
📸 13. IAM role `handson-glue-role` with policies attached
📸 14. Glue Databases list showing all 3 databases
📸 15. Glue Crawler details showing "Last run: SUCCEEDED, Tables created: 1"
📸 16. Glue Tables list showing the `orders` table with columns
📸 17. Athena Query Editor with `SELECT * FROM orders LIMIT 5` returning results
📸 18. Athena query results showing "Data scanned: X KB"

### Terraform Method
📸 19. Terminal showing `terraform init` completion
📸 20. Terminal showing `terraform plan` output with resource count
📸 21. Terminal showing `terraform apply` completion with all outputs
📸 22. Terminal showing `terraform state list` with all resources

### Validation Screenshots
📸 23. Athena showing partition pruning — two queries: with/without WHERE year filter, compare data scanned
📸 24. CloudWatch Logs showing Glue crawler execution log

### Architecture Screenshot
📸 25. Final AWS Console view: S3 bucket + Glue + Athena side by side (use browser tabs)

-------------------------------------------------------------------------------------------------------------------------------------------------------

## 10. Cleanup Steps

**⚠️ Always clean up after learning to avoid ongoing charges.**
The main costs are Glue DPU-hours (only when running) and S3 storage.

---

### 10A — Terraform Destroy (Recommended)

```bash
cd terraform

# Preview what will be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy -var-file="terraform.tfvars"
# Type: yes

# Expected output:
# aws_glue_crawler.raw_data: Destroying...
# aws_glue_crawler.raw_data: Destruction complete after 0s
# aws_athena_workgroup.data_lake: Destroying...
# aws_athena_workgroup.data_lake: Destruction complete after 0s
# aws_glue_catalog_database.data_lake: Destroying...
# aws_s3_bucket_lifecycle_configuration.data_lake: Destroying...
# aws_iam_role_policy.glue_s3: Destroying...
# aws_iam_role_policy_attachment.glue_service: Destroying...
# aws_s3_bucket_versioning.data_lake: Destroying...
# aws_s3_bucket_server_side_encryption_configuration.data_lake: Destroying...
# aws_iam_role.glue: Destroying...
# aws_s3_bucket.athena_results: Destroying...
# aws_s3_bucket.data_lake: Destroying...
#
# Destroy complete! Resources: 12 destroyed.

# Verify state is empty
terraform state list
# Expected: (empty output)
```

**Note:** If S3 buckets have objects, `terraform destroy` will fail with:
`BucketNotEmpty: The bucket you tried to delete is not empty`

Solution — empty the buckets first:
```bash
BUCKET=$(terraform output -raw data_lake_bucket 2>/dev/null)
ATHENA_BUCKET=$(terraform output -raw athena_results_bucket 2>/dev/null)

# Empty the buckets (delete all objects and versions)
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-objects \
  --bucket $BUCKET \
  --delete "$(aws s3api list-object-versions --bucket $BUCKET \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --output json)" 2>/dev/null || true

aws s3 rm s3://$ATHENA_BUCKET --recursive

# Then destroy
terraform destroy -var-file="terraform.tfvars"
```

---

### 10B — AWS Console Cleanup

If you used the Console method (not Terraform):

1. **Delete Glue Crawler:**
   Glue → Crawlers → select `handson-raw-crawler` → Actions → Delete

2. **Delete Glue Tables:**
   Glue → Tables → select all tables → Actions → Delete

3. **Delete Glue Databases:**
   Glue → Databases → delete `raw_db`, `handson_data_lake`, `curated_db`

4. **Delete Athena Workgroup:**
   Athena → Workgroups → select `handson-data-lake` → Delete
   (tick the box to delete query history)

5. **Empty and Delete S3 Buckets:**
   S3 → `handson-data-lake-XXXX` → Empty bucket → Delete bucket
   S3 → `handson-athena-results-XXXX` → Empty bucket → Delete bucket

6. **Delete IAM Role:**
   IAM → Roles → `handson-glue-role` → Delete

7. **Deregister Lake Formation:**
   Lake Formation → Data lake locations → select → Deregister

---

### 10C — AWS CLI Cleanup

```bash
BUCKET="handson-data-lake-${AWS_ACCOUNT_ID}"
ATHENA_BUCKET="handson-athena-results-${AWS_ACCOUNT_ID}"

# Delete Glue crawler
aws glue delete-crawler --name handson-raw-crawler

# Delete Glue tables (replace TABLE_NAME with actual names)
aws glue get-tables --database-name raw_db \
  --query "TableList[*].Name" --output text | \
  tr '\t' '\n' | \
  xargs -I{} aws glue delete-table --database-name raw_db --name {}

# Delete Glue databases
aws glue delete-database --name raw_db
aws glue delete-database --name handson_data_lake
aws glue delete-database --name curated_db

# Delete Athena workgroup (force-delete removes all query history)
aws athena delete-work-group \
  --work-group handson-data-lake \
  --recursive-delete-option

# Empty and delete S3 buckets
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-bucket --bucket $BUCKET --region us-east-1

aws s3 rm s3://$ATHENA_BUCKET --recursive
aws s3api delete-bucket --bucket $ATHENA_BUCKET --region us-east-1

# Delete IAM role (must detach policies first)
aws iam detach-role-policy \
  --role-name handson-glue-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam delete-role-policy \
  --role-name handson-glue-role \
  --policy-name glue-s3-access

aws iam delete-role --role-name handson-glue-role

# Deregister Lake Formation location
aws lakeformation deregister-resource \
  --resource-arn arn:aws:s3:::$BUCKET 2>/dev/null || true

echo "✅ All resources deleted"
```

---

### 10D — Cost Verification After Cleanup

```bash
# Check no S3 buckets remain
aws s3 ls | grep handson-data-lake
# Expected: no output (buckets deleted)

# Check no Glue resources remain
aws glue get-databases --query "DatabaseList[*].Name" --output text | grep handson
# Expected: no output

# Check no Glue crawlers remain
aws glue list-crawlers --query "CrawlerNames" --output text | grep handson
# Expected: no output

# Check Athena workgroup deleted
aws athena list-work-groups \
  --query "WorkGroups[?Name=='handson-data-lake'].State" --output text
# Expected: no output

# In AWS Console: Billing → Bills → view current month charges
# Expected: $0 for Glue and Athena (resources deleted)
# Note: S3 charges for partial month may appear (cents)
```

---

## Estimated Total Cost for This Project

| Activity | Cost |
|----------|------|
| 2-hour lab session | ~$0.05 |
| Glue Crawler (3 manual runs) | ~$0.04 |
| Athena queries (< 100 MB) | ~$0.00 |
| S3 storage (< 5 GB) | $0 (free tier) |
| **Total for learning session** | **~$0.09** |

This project is effectively free on AWS Free Tier.

---

*Guide version: 1.0 | Last updated: June 2026*
*Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake*

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
