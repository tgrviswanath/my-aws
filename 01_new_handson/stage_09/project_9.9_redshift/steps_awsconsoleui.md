# Project 9.9 — Redshift Data Warehouse
# Console UI Steps (Improved Template Format)
# Namespace: handson-namespace | Workgroup: handson-workgroup | DB: analytics

---

> ⚠️ **Cost reminder:** Redshift Serverless charges $0.36/hr (8 RPU) while active.
> Delete the workgroup immediately after learning.

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `redshift-serverless:CreateNamespace`, `redshift-serverless:CreateWorkgroup`
- ✅ Services enabled: Amazon Redshift, IAM, EC2 VPC — all in us-east-1
- ✅ Region: us-east-1 selected
- ✅ VPC with subnets exists (default VPC is fine)
- ✅ S3 bucket with `processed/orders/` Parquet data

**Step 0.1: Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → **US East (N. Virginia) us-east-1**

**Step 0.2: Confirm VPC Exists**
1. Search → **VPC** → **Your VPCs**
2. **Expected View:** Default VPC listed (172.31.0.0/16 typically)
3. **If None:** Create default VPC or use the AWS default

**📸 Screenshot P0:** Console with us-east-1 + VPC confirmed

---

### STEP 1 — Create IAM Role for Redshift

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global)

**Step 1.1: Navigate and Verify**
1. Search bar → **IAM** → click it
2. Left sidebar → **Roles** → **Create role**

**Step 1.2: Make Selections — Trusted Entity**

**Decision Point 1:** Trusted entity
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | Service-to-service access | ✅ Redshift needs S3 access |
| Custom trust policy | Manual JSON | ❌ Unnecessary |

1. Select **AWS service**
2. Scroll down → find **Redshift** → select **Redshift - Customizable**
3. Click **Next**

**Step 1.3: Attach Permissions Policies**

**Decision Point 2:** S3 access policy
| Option | Access | For This Project |
|--------|--------|-----------------|
| **AmazonS3ReadOnlyAccess** | All S3 read | ✅ Simple for learning |
| Custom inline policy | Specific bucket | ✅ Production best practice |

1. Search: `AmazonS3ReadOnlyAccess` → ✅ check it
2. Search: `AWSGlueConsoleFullAccess` → ✅ check it (needed for Spectrum)
3. Click **Next**

**Step 1.4: Configure Role Details**

| Field | Value |
|-------|-------|
| Role name | `handson-redshift-role` |
| Description | `Allows Redshift Serverless to read S3 and Glue Catalog` |

4. Click **Create role**
5. **Click on role name → copy the Role ARN** — needed for COPY command

**Step 1.5: Validate Result**
**Expected Outcome:** Role with 2 attached policies: AmazonS3ReadOnlyAccess + AWSGlueConsoleFullAccess

**Troubleshooting:**
- "Invalid trust relationship": Must select Redshift - Customizable, not just Redshift
- "AccessDenied": Your user needs `iam:CreateRole` + `iam:AttachRolePolicy`

**📸 Screenshot 1a:** IAM role `handson-redshift-role` with 2 policies

---

### STEP 2 — Create Redshift Serverless Namespace + Workgroup

**Prerequisites Check:**
- ✅ Required permissions: `redshift-serverless:CreateNamespace`, `redshift-serverless:CreateWorkgroup`
- ✅ IAM role `handson-redshift-role` ARN copied
- ✅ Strong password ready (upper + lower + number + special char)

**Step 2.1: Navigate and Verify**
1. Search → **Amazon Redshift** → click it
2. **Expected View:** Redshift console
3. Left sidebar → **Serverless dashboard** → click **Create workgroup**

**📸 Screenshot 2a:** Redshift Serverless dashboard before creation

**Step 2.2: Make Selections — Workgroup Setup**

**Decision Point 1:** Base RPU capacity
| RPU | Cost/hr | Use Case | For This Project |
|-----|---------|---------|-----------------|
| **8** | $0.36 | Learning, small data | ✅ Minimum, cheapest |
| 16 | $0.72 | Dev/test | ❌ Unnecessary |
| 32 | $1.44 | Production | ❌ Not needed |

**Step 2.3: Configure Workgroup**

| Field | Value | Explanation |
|-------|-------|-------------|
| Workgroup name | `handson-workgroup` | Compute layer |
| Base RPU capacity | **8** | Minimum cost |
| Publicly accessible | **Off** | Keep in private VPC |

**Step 2.4: Configure Namespace**

1. Under **Namespace** → choose **Create a new namespace**

| Field | Value | Explanation |
|-------|-------|-------------|
| Namespace name | `handson-namespace` | Logical container |
| Database name | `analytics` | Default database |
| Admin user name | `admin` | Superuser |
| Admin password | `Admin@1234!` | Must have upper+lower+num+special |

**Step 2.5: Associate IAM Role**

1. Scroll to **Associated IAM roles** section
2. Click **Associate IAM role**
3. Select `handson-redshift-role`
4. Click **Associate IAM roles**

**Step 2.6: Configure Network**

1. VPC: select **default VPC**
2. VPC security groups: click **Create a new security group**
   - Name: `handson-redshift-sg`
   - Inbound rule: TCP port 5439 from your VPC CIDR
3. Subnets: select **2–3 subnets** in different AZs

**Step 2.7: Review and Create**
1. Review all settings
2. Click **Save configuration**
3. **Expected:** Status = **Creating** → wait 5–10 minutes → **Available**

**Troubleshooting:**
- "Password does not meet requirements": Must have uppercase, lowercase, digit, special char (no `@` variants that Redshift doesn't accept — try `!`, `#`, `$`)
- Status stuck Creating > 15 min: Check CloudTrail for CreateWorkgroup errors
- "Cannot create in subnet": VPC needs internet gateway or NAT for S3 access

**📸 Screenshot 2b:** Namespace + workgroup creation form filled in

---

### STEP 3 — Verify Workgroup Available + Get Endpoint

**Step 3.1: Navigate and Verify**
1. Redshift → **Serverless dashboard** → **Workgroups**
2. **Expected View:** `handson-workgroup` Status = **Available** (green)
3. **If Still Creating:** Wait and refresh every 2 minutes

**Step 3.2: Get the Endpoint**
1. Click on `handson-workgroup`
2. **Expected View:** Details page with **Endpoint** section
3. Note the endpoint:
   `handson-workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com`
4. Port: **5439**

**📸 Screenshot 3a:** Workgroup Status = Available (green)
**📸 Screenshot 3b:** Workgroup details showing endpoint URL

---

### STEP 4 — Create Tables + Load Data (Python Script)

> Runs locally from your terminal. Set env vars first.

**Step 4.1: Set Environment Variables (PowerShell)**
```powershell
$env:REDSHIFT_HOST     = "handson-workgroup.ACCOUNT.us-east-1.redshift-serverless.amazonaws.com"
$env:REDSHIFT_USER     = "admin"
$env:REDSHIFT_PASSWORD = "Admin@1234!"
$env:REDSHIFT_DB       = "analytics"
$env:S3_BUCKET         = "handson-data-lake-YOUR_ACCOUNT_ID"
$env:IAM_ROLE_ARN      = "arn:aws:iam::ACCOUNT:role/handson-redshift-role"
```

**Step 4.2: Create Tables**
```powershell
pip install psycopg2-binary boto3
python code\redshift_operations.py setup
```
**Expected:**
```
Creating schema: analytics  ✓
Creating table: analytics.fact_orders  ✓
Creating table: analytics.dim_date  ✓
Populating dim_date (2020–2030)...  ✓
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
VACUUM SORT ONLY  ✓  |  ANALYZE  ✓
```

**Step 4.4: Run Analytics Report**
```powershell
python code\redshift_operations.py report
```
**Expected:** 4 formatted tables — daily revenue, top products, customer LTV, regional perf

**Troubleshooting:**
- `psycopg2.OperationalError: could not connect`: VPC routing — run from within VPC or use Redshift Data API instead
- `S3ServiceException`: IAM role not associated with workgroup — check Step 2.5
- `No rows loaded`: Check `processed/orders/` prefix exists in S3 with Parquet files

**📸 Screenshot 4a:** Terminal showing `setup` — 4 checks ✓
**📸 Screenshot 4b:** Terminal showing `load` — COPY complete + row count
**📸 Screenshot 4c:** Terminal showing `report` — analytics tables

---

### STEP 5 — Query via Redshift Query Editor v2

**Prerequisites Check:**
- ✅ Workgroup Status = Available
- ✅ Tables created and data loaded

**Step 5.1: Navigate and Verify**
1. Redshift console → left sidebar → **Query editor v2**
2. **Expected View:** SQL editor interface
3. Click **Connect** → select workgroup `handson-workgroup`
4. Database: `analytics` | Auth: **Database user** | Username: `admin`
5. **If prompted for password:** Enter `Admin@1234!`

**📸 Screenshot 5a:** Query Editor v2 connected showing schema browser

**Step 5.2: Explore Schema Browser**
1. Left panel → expand `analytics` schema
2. **Expected View:** `fact_orders` and `dim_date` tables listed
3. Click on `fact_orders` → see column list with types

**Step 5.3: Run Revenue Query**
```sql
SELECT
    product_id,
    COUNT(DISTINCT order_id)  AS order_count,
    SUM(total_amount)         AS total_revenue,
    AVG(total_amount)         AS avg_order_value
FROM analytics.fact_orders
WHERE status != 'cancelled'
GROUP BY product_id
ORDER BY total_revenue DESC
LIMIT 10;
```
Click **Run** — note the execution time shown below the results.

**Decision Point 1:** Expected vs actual speed
| Data size | Expected time | If slower |
|-----------|--------------|-----------|
| 1,000 rows | < 500ms | First query — cache warming |
| 100,000 rows | < 1s | Normal for aggregation |
| 1M+ rows | 1–5s | Expected — add SORTKEY filter |

**Step 5.4: Validate Result**
**Expected Outcome:** Results table with product_id, order_count, total_revenue.
Execution time shown in bottom: < 1 second for small datasets.

**📸 Screenshot 5b:** Query Editor results + execution time shown

---

### STEP 6 — Test Redshift Spectrum (Optional)

**Step 6.1: Create External Schema**
In Query Editor v2, run (replace ACCOUNT):
```sql
CREATE EXTERNAL SCHEMA IF NOT EXISTS spectrum
FROM DATA CATALOG
DATABASE 'handson_data_lake'
IAM_ROLE 'arn:aws:iam::ACCOUNT:role/handson-redshift-role'
CREATE EXTERNAL DATABASE IF NOT EXISTS;
```

**Step 6.2: Query S3 Data Directly**
```sql
-- Query S3 Parquet without loading to Redshift
SELECT product_id, SUM(total_amount) AS s3_revenue
FROM spectrum.orders
GROUP BY product_id
ORDER BY s3_revenue DESC
LIMIT 5;
```
**Expected:** Returns results from S3 directly — no COPY needed.

**📸 Screenshot 6a:** Spectrum query returning S3 results from Query Editor

---

### Console UI Summary

| Step | Action | Resource |
|------|--------|---------|
| Step 1 | Create IAM Role | `handson-redshift-role` |
| Step 2 | Create Namespace + Workgroup | `handson-namespace` + `handson-workgroup` |
| Step 3 | Get endpoint URL | Port 5439 endpoint |
| Step 4 | Run Python script | Tables created + data loaded |
| Step 5 | Query Editor v2 | Revenue query < 1s |
| Step 6 | Spectrum (optional) | S3 query without loading |

### Screenshot Summary

| # | Description | Step |
|---|-------------|------|
| P0 | Console us-east-1 + VPC | Phase 0 |
| 1a | IAM role with 2 policies | Step 1.5 |
| 2a | Serverless dashboard | Step 2.1 |
| 2b | Namespace + workgroup form | Step 2.7 |
| 3a | Workgroup Status = Available | Step 3.1 |
| 3b | Workgroup endpoint URL | Step 3.2 |
| 4a | Terminal: setup ✓ | Step 4.2 |
| 4b | Terminal: load + row count | Step 4.3 |
| 4c | Terminal: report output | Step 4.4 |
| 5a | Query Editor connected + schema | Step 5.1 |
| 5b | Query result + execution time | Step 5.3 |
| 6a | Spectrum query from S3 | Step 6.2 |

**Total: 12 screenshots for complete documentation**
