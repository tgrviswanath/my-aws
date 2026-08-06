# Project 9.6 — dbt Transformation Pipeline
# Console UI Steps (Improved Template Format)
# Region: us-east-1 | dbt runs locally | AWS Console for infrastructure setup

---

> **Important:** dbt Core runs entirely on your local machine.
> The AWS Console steps below cover the infrastructure dbt needs:
> 1. Verify the Glue source table exists (from Project 9.1)
> 2. Create the Athena workgroup for dbt queries
> 3. Create the S3 staging bucket for Athena results
> 4. Verify dbt output tables in Athena after running `dbt run`

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `athena:CreateWorkGroup`, `s3:CreateBucket`, `glue:GetTable`
- ✅ Services enabled: Amazon Athena, AWS Glue, Amazon S3 — all in us-east-1
- ✅ Region: us-east-1 selected in top-right of AWS Console
- ✅ Project 9.1 completed: Glue database `handson_data_lake` with `orders` table

**Step 0.1: Navigate and Verify Region**
1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right shows **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → **US East (N. Virginia) us-east-1**

**Step 0.2: Verify Glue Source Table**
1. Search bar → **AWS Glue** → click it
2. Left sidebar → **Data Catalog** → **Tables**
3. **Expected View:** `orders` table in database `handson_data_lake`
4. **If Not Found:** Run the Glue Crawler from Project 9.1 first — dbt cannot run without this source table

**📸 Screenshot P0:** Glue Tables showing `orders` in `handson_data_lake`

---

### STEP 1 — Create S3 Staging Bucket for dbt

**Prerequisites Check:**
- ✅ Required permissions: `s3:CreateBucket`, `s3:PutLifecycleConfiguration`
- ✅ Services enabled: Amazon S3 (global)
- ✅ Region availability: S3 bucket in us-east-1

**Step 1.1: Navigate and Verify**
1. Search bar → **S3** → click it
2. **Expected View:** S3 Buckets list
3. Click **Create bucket** (orange button)

**📸 Screenshot 1a:** S3 Buckets list before creation

**Step 1.2: Make Selections — Bucket Naming**

**Decision Point 1:** Bucket name strategy
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Generic name (`my-dbt-bucket`) | Risk of name conflict | ❌ May already be taken |
| **Account-based name** | Globally unique | ✅ Use `handson-dbt-staging-ACCOUNT_ID` |

| Field | Value | Explanation |
|-------|-------|-------------|
| Bucket name | `handson-dbt-staging-YOUR_ACCOUNT_ID` | Replace with your 12-digit account ID |
| AWS Region | `US East (N. Virginia) us-east-1` | Same region as Athena |

**Step 1.3: Configure Security Settings**

| Setting | Value | Why |
|---------|-------|-----|
| Block all public access | ✅ All 4 boxes | Query results must never be public |
| Bucket Versioning | Disabled | Results are temporary, no need for versioning |
| Default encryption | SSE-S3 | Encrypt at rest (free) |

**Step 1.4: Create the Bucket**
1. Click **Create bucket**
2. **Expected Outcome:** Bucket listed in S3 with green confirmation banner

**📸 Screenshot 1b:** S3 bucket `handson-dbt-staging-ACCOUNT` just created

**Step 1.5: Add Lifecycle Policy (Cost Control)**
1. Click on the new bucket → **Management** tab
2. Click **Create lifecycle rule**
3. Fill in:

| Field | Value | Why |
|-------|-------|-----|
| Rule name | `expire-dbt-results` | Clear description |
| Rule scope | **Limit to specific prefix** | Only affect dbt results |
| Prefix | `dbt/` | Only dbt query result files |
| Action | ✅ Expire current versions | Delete after N days |
| Days | `7` | Keeps storage near $0 |

4. Click **Create rule**

**Step 1.6: Validate Result**
**Expected Outcome:** Lifecycle rule `expire-dbt-results` listed under Management tab

**Troubleshooting:**
- "Bucket name already exists": Another AWS account has this name — add a random 4-digit suffix
- "Access Denied": Your IAM user needs `s3:CreateBucket` and `s3:PutLifecycleConfiguration`

**📸 Screenshot 1c:** Bucket Management tab showing `expire-dbt-results` lifecycle rule

---

### STEP 2 — Create Athena Workgroup for dbt

**Prerequisites Check:**
- ✅ Required permissions: `athena:CreateWorkGroup`
- ✅ Services enabled: Amazon Athena
- ✅ S3 staging bucket created in Step 1

**Step 2.1: Navigate and Verify**
1. Search bar → **Athena** → click it
2. Left sidebar → **Workgroups**
3. **Expected View:** Workgroups list (primary workgroup exists by default)
4. Click **Create workgroup** (orange button)

**📸 Screenshot 2a:** Athena Workgroups list before creation

**Step 2.2: Make Selections — Workgroup Purpose**

**Decision Point 1:** Why a separate workgroup for dbt?
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Use `primary` workgroup | All queries in one place | ❌ No cost isolation |
| **Dedicated `handson-dbt` workgroup** | Separate dbt costs, query limits | ✅ Best practice |

**Step 2.3: Configure Workgroup Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Workgroup name | `handson-dbt` | Matches `work_group` in profiles.yml |
| Description | `dbt transformation queries` | Clear purpose |

**Step 2.4: Configure Query Result Settings**

1. Expand **Query result configuration**
2. Fill in:

| Field | Value | Explanation |
|-------|-------|-------------|
| Query result location | `s3://handson-dbt-staging-YOUR_ACCOUNT_ID/dbt/` | Where Athena writes results |
| Encrypt query results | SSE-S3 | Free encryption |
| Override client-side settings | ✅ Enable | Forces all dbt queries to use this S3 path |

**Step 2.5: Configure Cost Control**

**Decision Point 2:** Data scan limit per query
| Option | Monthly cost exposure | For This Project |
|--------|----------------------|-----------------|
| No limit | Could scan unlimited data | ❌ Risk of surprise cost |
| **1 GB per query** | Max $0.005 per query | ✅ Prevents accidental full-table scans |

1. Expand **Query limits** section
2. Enable: ✅ **Bytes scanned limit per query**
3. Value: `1073741824` (1 GB = 1 × 1024 × 1024 × 1024)
4. Action: **Cancel query** (kills query if it exceeds limit)

**Step 2.6: Create and Validate**
1. Click **Create workgroup**
2. **Expected Outcome:** `handson-dbt` listed as **Active** in workgroups list

**Troubleshooting:**
- "Invalid S3 location": Include trailing `/` — `s3://bucket/dbt/`
- "Access Denied on workgroup creation": Need `athena:CreateWorkGroup` permission
- "Workgroup already exists": A workgroup with that name was created before — delete it first

**📸 Screenshot 2b:** Workgroup `handson-dbt` Status = Active

---

### STEP 3 — Configure Athena Query Editor (First-Time Setup)

**Prerequisites Check:**
- ✅ Athena workgroup `handson-dbt` created
- ✅ S3 staging bucket exists

**Step 3.1: Navigate to Query Editor**
1. Athena → **Query editor** (left sidebar)
2. **Expected View:** SQL query editor

**Step 3.2: Select Workgroup**
1. Top-right of Athena editor → workgroup dropdown
2. **If showing `primary`**: click → select **handson-dbt**
3. **Expected View:** Workgroup changes to `handson-dbt`

**Step 3.3: Select Database**
1. Left panel → **Database** dropdown
2. Select **handson_data_lake**
3. **Expected View:** Tables list shows `orders`

**Step 3.4: Test Query (Verify Source)**
1. Type in the query editor:
```sql
SELECT COUNT(*) FROM orders;
```
2. Click **Run**
3. **Expected View:** A number > 0 returned (the raw order count)

**Decision Point 1:** Query result
| Result | Meaning | Action |
|--------|---------|--------|
| Number > 0 | Source data exists ✅ | Proceed to dbt CLI setup |
| 0 rows | Empty table | Add CSV data to S3 raw/orders/ and re-run Glue Crawler |
| Error: "Table not found" | Glue table missing | Run Glue Crawler from Project 9.1 |

**📸 Screenshot 3a:** Athena editor showing `orders` count > 0

---

### STEP 4 — Run dbt Locally (CLI — Not Console)

> dbt runs from your terminal, not the AWS Console.
> The following steps use PowerShell. See GUIDE.md Section 5B for full details.

**Step 4.1: Install and Configure (PowerShell)**
```powershell
pip install dbt-athena-community==1.7.1
# Configure ~/.dbt/profiles.yml (see GUIDE.md Phase 2)
# Create dbt_project.yml and staging/schema.yml (see GUIDE.md Phase 3)
```

**Step 4.2: Run dbt**
```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt\dbt_project
dbt deps && dbt debug && dbt run && dbt test
```

**Expected terminal output:**
```
Done. PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=2   ← dbt run
Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7   ← dbt test
```

---

### STEP 5 — Verify dbt Output in Athena Console

**Prerequisites Check:**
- ✅ `dbt run` completed successfully (PASS=2)
- ✅ Both `stg_orders` and `fct_orders` created

**Step 5.1: Navigate and Verify Tables**
1. Athena → **Query editor**
2. Left panel → Database: **handson_data_lake**
3. **Expected View:** Tables list now shows:
   - `orders` (original raw source)
   - `stg_orders` (dbt VIEW — new)
   - `fct_orders` (dbt TABLE — new)
4. **If stg_orders/fct_orders Missing:** `dbt run` may have failed — check terminal output

**📸 Screenshot 5a:** Athena tables list showing `orders` + `stg_orders` + `fct_orders`

**Step 5.2: Preview stg_orders (VIEW)**
1. Click ⋮ next to `stg_orders` → **Preview table**
2. **Expected View:** First 10 rows with:
   - `product_name` in UPPERCASE (e.g., `WIDGET A`)
   - `order_status` in lowercase (e.g., `delivered`)
   - `order_amount_usd` as a number (not a string)
   - `order_date` as a proper date (not a string)

**📸 Screenshot 5b:** stg_orders preview showing clean, typed data

**Step 5.3: Query fct_orders (TABLE) — Business Logic**
1. In the query editor, run:
```sql
SELECT
    order_tier,
    COUNT(*) AS total_orders,
    ROUND(SUM(order_amount_usd), 2) AS total_revenue
FROM handson_data_lake.fct_orders
GROUP BY order_tier
ORDER BY total_revenue DESC;
```
2. **Expected View:** Results table like:

| order_tier | total_orders | total_revenue |
|------------|-------------|---------------|
| high_value | 23 | 3450.20 |
| medium_value | 45 | 2870.50 |
| low_value | 122 | 1890.30 |

**Step 5.4: Verify Incremental Column**
```sql
SELECT
    order_tier,
    order_amount_usd,
    quantity,
    unit_price_usd,
    _dbt_updated_at
FROM handson_data_lake.fct_orders
LIMIT 5;
```
**Expected:** `unit_price_usd` = `order_amount_usd / quantity` and `_dbt_updated_at` = recent timestamp

**Step 5.5: Validate Result**
**Expected Outcome:**
- Both tables visible in Athena
- `stg_orders` returns clean, properly typed rows
- `fct_orders` returns rows with `order_tier` values (high_value / medium_value / low_value)

**Troubleshooting:**
- "Table stg_orders not found": `dbt run` may have failed. Check terminal for errors.
- "HIVE_CANNOT_OPEN_SPLIT" on fct_orders: S3 output path issue — check profiles.yml `s3_staging_dir`
- Results from `fct_orders` are empty: Input `orders` table may be empty — add sample data

**📸 Screenshot 5c:** Athena fct_orders query showing order_tier distribution

---

### STEP 6 — View dbt Documentation (Local Browser)

> dbt docs serve from your terminal — not an AWS Console feature.

**Step 6.1: Generate Docs**
```powershell
cd dbt_project
dbt docs generate
dbt docs serve --port 8080
```

**Step 6.2: Explore Lineage Graph**
1. Open `http://localhost:8080`
2. Click the **graph icon** (bottom-right) to open lineage view
3. **Expected View:**

```
[raw.orders] ──→ [stg_orders] ──→ [fct_orders]
  (source)          (view)       (incremental table)
```

4. Click on `fct_orders` → see all columns, descriptions, test results

**Step 6.3: Validate Result**
**Expected Outcome:** Lineage graph shows full chain from source to mart.
All columns documented. Tests shown as passing.

**📸 Screenshot 6a:** dbt docs lineage graph in browser (raw.orders → stg_orders → fct_orders)
**📸 Screenshot 6b:** fct_orders model page showing columns + tests

---

### Console UI Summary

| Step | Action | Resource Created |
|------|--------|----------------|
| Step 1 | Create S3 staging bucket | `handson-dbt-staging-ACCOUNT` |
| Step 2 | Create Athena workgroup | `handson-dbt` (Active) |
| Step 3 | Configure Athena editor | `handson_data_lake` selected |
| Step 4 | Run dbt (CLI) | `stg_orders` VIEW + `fct_orders` TABLE |
| Step 5 | Verify Athena output | Query both tables, confirm results |
| Step 6 | View dbt docs (local) | Lineage graph + column docs |

### Screenshot Summary

| # | Description | Step |
|---|-------------|------|
| P0 | Glue Tables showing `orders` in handson_data_lake | Phase 0 |
| 1a | S3 Buckets list before creation | Step 1.1 |
| 1b | S3 bucket created | Step 1.4 |
| 1c | Lifecycle rule `expire-dbt-results` | Step 1.5 |
| 2a | Athena Workgroups list | Step 2.1 |
| 2b | Workgroup `handson-dbt` Active | Step 2.6 |
| 3a | Athena editor showing orders COUNT > 0 | Step 3.4 |
| 5a | Athena tables: orders + stg_orders + fct_orders | Step 5.1 |
| 5b | stg_orders preview — clean typed data | Step 5.2 |
| 5c | fct_orders order_tier query results | Step 5.3 |
| 6a | dbt docs lineage graph | Step 6.2 |
| 6b | fct_orders model page in dbt docs | Step 6.2 |

**Total: 12 screenshots for complete documentation**
