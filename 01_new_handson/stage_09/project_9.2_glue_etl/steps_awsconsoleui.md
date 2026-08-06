# Project 9.2 — AWS Glue ETL Pipeline
# Console UI Steps (Improved Template Format)
# Region: us-east-1 (N. Virginia) | Adapt account ID and region to your setup

---

## 5A. AWS Management Console Implementation

> Format reference: project_9.1_data_lake/steps_awsconsoleui.md
> Every step follows: Prerequisites Check → Navigate → Decision Points → Configure → Validate

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateJob`, `glue:StartJobRun`, `glue:CreateTrigger`, `s3:PutObject`
- ✅ Project 9.1 deployed: S3 bucket `handson-data-lake-YOUR_ACCOUNT_ID` exists
- ✅ Glue IAM Role from 9.1: `handson-glue-role` exists in IAM
- ✅ Raw data uploaded: `s3://bucket/raw/orders/year=2024/month=01/day=15/orders.csv`
- ✅ Region: us-east-1 selected in top-right of AWS Console
- ✅ ETL script ready locally: `src/etl_job.py`

**Step 0.1: Verify Prerequisites in Console**

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Left sidebar → **Roles** → search for `handson-glue-role`
3. **Expected View:** Role listed with `AWSGlueServiceRole` attached
4. **If Missing:** Return to Project 9.1 and run `terraform apply` first

**📸 Screenshot P0a:** IAM Roles list showing `handson-glue-role` with policies attached

**Step 0.2: Confirm S3 Raw Data Exists**

1. Go to [S3 Console](https://s3.console.aws.amazon.com/s3/)
2. Click your data lake bucket
3. Navigate to `raw/orders/year=2024/month=01/day=15/`
4. **Expected View:** `orders.csv` file listed with size > 0
5. **If Missing:** Upload sample data from Project 9.1 before continuing

**📸 Screenshot P0b:** S3 showing `orders.csv` at the partition path

---

### STEP 1 — Upload ETL Script to S3

**Prerequisites Check:**
- ✅ Required permissions: `s3:PutObject`, `s3:ListBucket`
- ✅ S3 bucket exists from Project 9.1
- ✅ Local file `src/etl_job.py` exists in project folder

**Step 1.1: Navigate to Your S3 Bucket**

1. Go to [S3 Console](https://s3.console.aws.amazon.com/s3/)
2. **Expected View:** List of your S3 buckets
3. Click on `handson-data-lake-YOUR_ACCOUNT_ID`
4. **Expected View:** Bucket with folders: `raw/`, `athena-results/`, `temp/`
5. **If Different:** Verify you clicked the correct bucket (not `handson-athena-results-*`)

**📸 Screenshot 1a:** S3 bucket root showing existing zone folders

**Step 1.2: Create the `scripts/` Folder**

1. Click **"Create folder"** (orange button, top-right area)
2. **Expected View:** Create folder form

**Decision Point 1:** Folder naming
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| `scripts/` | Standard convention for Glue scripts | ✅ Use this |
| `code/` | Alternative naming | ❌ Not standard for Glue |
| `glue/` | Service-specific naming | ❌ Too broad |

3. **Folder name:** `scripts`
4. Leave Server-side encryption as default (SSE-S3 inherited from bucket)
5. Click **"Create folder"**
6. **Expected Outcome:** `scripts/` folder appears in bucket listing

**Troubleshooting:**
- If "Access Denied": Your IAM user lacks `s3:PutObject` — check IAM permissions
- If folder not visible: Refresh browser (F5)

**📸 Screenshot 1b:** Bucket listing showing new `scripts/` folder

**Step 1.3: Upload the PySpark ETL Script**

1. Click on the `scripts/` folder
2. **Expected View:** Empty folder with "Upload" button
3. Click **"Upload"** (orange button)
4. **Expected View:** Upload interface

**Step 1.4: Add the ETL Script File**

1. Click **"Add files"**
2. Navigate to: `D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl\src\`
3. Select `etl_job.py` → Click **Open**
4. **Expected View:** File listed as `etl_job.py` with size ~4 KB

**Decision Point 2:** Storage class for the script
| Option | Cost | Access Pattern | For This Project |
|--------|------|---------------|-----------------|
| Standard | $0.023/GB/mo | Frequent (runs daily) | ✅ Use this |
| Standard-IA | $0.0125/GB/mo | Infrequent | ❌ Script runs every job |
| Intelligent-Tiering | Variable | Unknown | ❌ Overkill for 4KB file |

5. Leave storage class as **Standard**
6. Click **"Upload"** at the bottom

**Step 1.5: Validate Upload**

**Expected Outcome:** Green banner "Upload succeeded" with `etl_job.py` listed

**Troubleshooting:**
- "403 Forbidden": Your IAM user lacks `s3:PutObject` on this bucket
- "Upload failed": Check file size — corrupt file? Re-save `etl_job.py`
- File not appearing: Wait 5 seconds and refresh (S3 has strong read-after-write consistency)

**📸 Screenshot 1c:** `etl_job.py` uploaded to `s3://bucket/scripts/` with success banner

---

### STEP 2 — Create the Glue ETL Job

**Prerequisites Check:**
- ✅ Required permissions: `glue:CreateJob`, `iam:PassRole`
- ✅ ETL script uploaded to S3 in previous step
- ✅ Glue service available in us-east-1
- ✅ IAM role `handson-glue-role` exists

**Step 2.1: Navigate to AWS Glue Console**

1. Go to [AWS Glue Console](https://console.aws.amazon.com/glue/)
2. **Expected View:** Glue Studio home page with navigation sidebar
3. **If Different:** You may see a "Getting Started" banner — click "Continue to AWS Glue"

**📸 Screenshot 2a:** Glue console home page before any jobs exist

**Step 2.2: Navigate to ETL Jobs**

1. In left sidebar, click **"ETL Jobs"** (under "Data Integration and ETL" section)
2. **Expected View:** Empty jobs list with "Create job" button
3. **If you see existing jobs:** That's fine — you'll add a new one

**📸 Screenshot 2b:** ETL Jobs list page (empty state — before creation)

**Step 2.3: Initiate Job Creation**

1. Click **"Create job"** (orange button, top-right)
2. **Expected View:** Job creation options panel with 4 options

**Decision Point 3:** Job creation method
| Option | Use Case | Pros | Cons | For This Project |
|--------|----------|------|------|-----------------|
| Visual ETL | Simple drag-drop pipelines | Easy to start | Generates verbose code | ❌ Less educational |
| Script editor | Custom PySpark, full control | Maximum flexibility | Requires PySpark knowledge | ✅ Use this |
| Jupyter Notebook | Interactive development | Iterative testing | Not for scheduled jobs | ❌ Dev tool only |
| Python Shell | Lightweight scripts, no Spark | Fast startup | No distributed processing | ❌ Not for large data |

3. Select **"Script editor"**

**Decision Point 4:** Script engine
| Engine | Use Case | For This Project |
|--------|----------|-----------------|
| Spark | Large-scale batch ETL, PySpark | ✅ Our script is PySpark |
| Spark Streaming | Real-time data processing | ❌ Not streaming |
| Python Shell | Lightweight Python | ❌ Our script needs Spark |
| Ray | ML distributed Python | ❌ Not ML workload |

4. Select engine: **Spark**

**Decision Point 5:** Script source
| Option | When to Use | For This Project |
|--------|-------------|-----------------|
| Start fresh | Writing new code from scratch | ❌ We have existing script |
| Upload and edit | Using existing script from local | ❌ Already in S3 |
| Use existing from S3 | Script already in S3 | ✅ Use this |

5. Select **"Upload and edit an existing script"**
6. Under "Script path", click **"Choose"**
7. Browse: your bucket → `scripts/` → `etl_job.py` → click **"Choose"**
8. **Expected View:** Script path shows `s3://YOUR_BUCKET/scripts/etl_job.py`
9. Script code should appear in the editor panel

**📸 Screenshot 2c:** Script editor showing `etl_job.py` code loaded from S3

**Step 2.4: Configure Job Basic Properties**

Click the **"Job details"** tab (top of the page, next to "Script" tab)

**Expected View:** Form with multiple configuration fields

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `handson-etl-job` | Must match Terraform — no spaces |
| Description | `Orders CSV to Parquet ETL` | Self-documenting |
| IAM Role | select `handson-glue-role` | Role from Project 9.1 |
| Type | `Spark` | Already selected from previous step |
| Glue version | **`Glue 4.0`** | Spark 3.3, Python 3.10 — latest stable |
| Language | `Python 3` | Our script uses Python |

**Decision Point 6:** IAM Role selection
| Option | Security | For This Project |
|--------|----------|-----------------|
| Create new role | Good — fresh permissions | ❌ Already created in 9.1 |
| Use existing role | Reuse, consistent | ✅ Use `handson-glue-role` |

**📸 Screenshot 2d:** Job details tab with Name, Description, IAM Role filled in

**Step 2.5: Configure Worker Settings**

Scroll down to the **Worker configuration** section:

| Field | Value | Explanation |
|-------|-------|-------------|
| Worker type | **G.1X** | 4 vCPU + 16GB RAM per worker |
| Number of workers | **2** | Minimum: 1 driver + 1 executor |
| Max retries | **1** | Retry once on transient S3/network errors |
| Job timeout (minutes) | **60** | Kill job if stuck — cost protection |

**Decision Point 7:** Worker type selection
| Worker | vCPU | RAM | Cost/hr | For This Project |
|--------|------|-----|---------|-----------------|
| G.1X | 4 | 16GB | $0.44 | ✅ Right-sized for < 1GB data |
| G.2X | 8 | 32GB | $0.88 | ❌ Overkill for orders CSV |
| G.4X | 16 | 64GB | $1.76 | ❌ Enterprise-scale only |
| G.8X | 32 | 128GB| $3.52 | ❌ Very large datasets only |

**Why 2 workers minimum?**
Spark requires at least 1 driver + 1 executor. With only 1 worker, Spark cannot distribute work. 2 workers = the minimum functional Spark cluster.

**📸 Screenshot 2e:** Worker configuration showing G.1X, 2 workers, 60min timeout

**Step 2.6: Configure Advanced Properties**

Scroll down to **Advanced properties** section:

| Field | Value | Explanation |
|-------|-------|-------------|
| Script path | `s3://bucket/scripts/etl_job.py` | Already set |
| Temporary directory | `s3://bucket/temp/` | Required for Spark shuffle |
| Spark UI logs path | (optional) `s3://bucket/sparkhistory/` | For Spark DAG visualization |

**Step 2.7: Add Job Parameters**

Scroll down to find **"Job parameters"** section.

Click **"Add new parameter"** for each row:

| Key (must include `--`) | Value | Why |
|------------------------|-------|-----|
| `--job-bookmark-option` | `job-bookmark-enable` | Track processed files (incremental) |
| `--enable-metrics` | `true` | Spark metrics in CloudWatch |
| `--enable-continuous-cloudwatch-log` | `true` | Real-time log streaming |
| `--source_bucket` | `handson-data-lake-YOUR_ACCOUNT_ID` | Passed to script |
| `--target_bucket` | `handson-data-lake-YOUR_ACCOUNT_ID` | Passed to script |
| `--database_name` | `handson_data_lake` | Glue Catalog database |
| `--TempDir` | `s3://handson-data-lake-YOUR_ACCOUNT_ID/temp/` | Glue temp storage |

> ⚠️ Keys MUST start with `--` (two dashes). Missing the `--` prefix means the argument is silently ignored — the script will fail with a `KeyError`.

**📸 Screenshot 2f:** Job parameters section showing all 7 parameters entered

**Step 2.8: Save the Job**

1. Click **"Save"** button (top-right corner)
2. **Expected Outcome:** Green banner: "Job saved successfully"

**Troubleshooting:**
- "Role not found or insufficient permissions": IAM role ARN wrong — go to IAM → Roles → copy exact ARN
- "Script location is required": S3 path not set — go back to Script tab and verify
- "Invalid parameter key": Parameter key missing `--` prefix — fix the double-dash

**📸 Screenshot 2g:** Success banner "Job saved successfully" with job name `handson-etl-job`

---

### STEP 3 — Run the Glue Job Manually

**Prerequisites Check:**
- ✅ Job `handson-etl-job` saved successfully
- ✅ Raw CSV data in `s3://bucket/raw/orders/`
- ✅ IAM role has S3 read/write permissions
- ✅ Understanding: First run takes 8–12 minutes (worker startup overhead)

**Step 3.1: Start the Job Run**

1. Confirm you are on the `handson-etl-job` detail page
2. Click **"Run"** button (orange, top-right)
3. **Expected View:** "Run job" confirmation dialog

**Decision Point 8:** Run options
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Run with defaults | Use saved job parameters | ✅ Parameters already configured |
| Override parameters | One-time parameter change | ❌ Not needed |
| Run with job bookmark reset | Re-process all data | ❌ Only needed for reprocessing |

4. Leave defaults → click **"Run"**
5. **Expected View:** "Job run started" with Run ID like `jr_abc123...`

**📸 Screenshot 3a:** Job run started — notification showing Run ID

**Step 3.2: Monitor Job Execution**

1. Click the **"Runs"** tab on the job detail page
2. **Expected View:** Table with your run showing status

**Status progression — what you'll see:**
| Status | Duration | What's happening |
|--------|----------|-----------------|
| `STARTING` | 0–2 min | AWS allocating EC2 workers, Spark initializing |
| `RUNNING` | 2–10 min | PySpark script executing: extract → transform → load |
| `SUCCEEDED` | Final | All data written to S3 as Parquet |
| `FAILED` | Final | Error occurred — check logs (Step 3.3) |

3. Refresh every 30 seconds (click refresh icon or F5)
4. **Expected final duration:** 5–12 minutes for first run with sample data

**📸 Screenshot 3b:** Job run in RUNNING state — duration counter visible

**📸 Screenshot 3c:** Job run SUCCEEDED — duration and DPU-hours consumed

**Step 3.3: View Real-Time Logs**

1. Click on the Run ID (link in the Runs table)
2. Click **"Output logs"** tab (or scroll down to "Output")
3. Click on the CloudWatch log stream link
4. **Expected View:** Log entries like:
   ```
   Reading raw orders data...
   Raw record count: 10
   Transforming data...
   Clean record count: 10
   Writing processed data to S3...
   ETL job complete!
   ```
5. **If logs are empty:** Wait 2–3 minutes for log propagation after job completes

**Inline Troubleshooting:**
| Log Message | Meaning | Fix |
|-------------|---------|-----|
| `AccessDenied s3://bucket/raw/` | IAM role missing S3 read | Add `s3:GetObject` to Glue role |
| `FileNotFoundException` | Raw CSV not in S3 | Upload `orders.csv` to raw zone |
| `KeyError: source_bucket` | Job parameter missing `--` | Fix parameter key in Job details |
| `TIMEOUT` status | Job exceeded 60 min limit | Reduce data size or increase timeout |
| `GlueException: TempDir not set` | Missing `--TempDir` parameter | Add `--TempDir` to job parameters |

**📸 Screenshot 3d:** CloudWatch log stream showing `ETL job complete!` message

---

### STEP 4 — Verify S3 Output (Parquet Files)

**Prerequisites Check:**
- ✅ Job run shows SUCCEEDED status
- ✅ Required permissions: `s3:ListBucket`, `s3:GetObject`

**Step 4.1: Navigate to Processed Zone**

1. Go to [S3 Console](https://s3.console.aws.amazon.com/s3/)
2. Click your data lake bucket
3. Click on `processed/` folder
4. **Expected View:** `orders/` and `orders_daily/` sub-folders

**Step 4.2: Verify Partition Structure**

1. Click on `orders/`
2. **Expected View:** `year=2024/` folder (or current year)
3. Drill down: `year=2024/` → `month=01/`
4. **Expected View:** One or more `.parquet` files named `part-00000.parquet`

**Decision Point 9:** Expected file structure
| Path | Content | Expected |
|------|---------|----------|
| `processed/orders/year=2024/month=01/` | Individual orders | ✅ Should exist |
| `processed/orders_daily/year=2024/month=01/` | Daily aggregates | ✅ Should exist |
| `raw/orders/year=2024/month=01/day=15/` | Original CSV | ✅ Untouched |

**Step 4.3: Validate File Format**

1. Click on a `.parquet` file
2. **Expected View:** File properties showing:
   - Format: `.parquet`
   - Size: smaller than the original CSV (70–80% smaller)
   - Encryption: SSE-S3

**Troubleshooting:**
- `processed/` folder is empty: Job ran but failed silently — check CloudWatch logs
- Only `part-00000.parquet` exists: Normal — small data creates 1 partition file
- Size larger than CSV: Unusual — Parquet is always smaller for structured data

**📸 Screenshot 4a:** S3 `processed/orders/year=2024/month=01/` showing `.parquet` file

**📸 Screenshot 4b:** Size comparison — raw CSV vs processed Parquet (smaller)

---

### STEP 5 — Query Processed Data with Athena

**Prerequisites Check:**
- ✅ Parquet files exist in `processed/orders/`
- ✅ Glue Data Catalog database `handson_data_lake` exists
- ✅ Athena workgroup `handson-data-lake` configured from Project 9.1
- ✅ Required permissions: `athena:StartQueryExecution`, `glue:GetTable`

**Step 5.1: Navigate to Athena**

1. Go to [Amazon Athena Console](https://console.aws.amazon.com/athena/)
2. **Expected View:** Athena Query Editor
3. **If workgroup banner appears:** Click "Acknowledge" — workgroup from Project 9.1 already has result location set

**Step 5.2: Add Partition to Glue Catalog**

The ETL job wrote Parquet files but Athena's table still maps to the old schema.
You need to register the new partitions.

1. In Athena Query Editor, select database: `handson_data_lake`
2. Run this repair query:
   ```sql
   MSCK REPAIR TABLE orders;
   ```
3. **Expected Outcome:** "Query successful" — partitions now registered

**Why this is needed:**
When Glue ETL writes new partition folders to S3, the Glue Catalog table does
not automatically know about them. `MSCK REPAIR TABLE` scans S3 and registers
all discovered partitions. In production, this is automated — but for this lab,
run it manually after each ETL job.

**Step 5.3: Execute Revenue Query on Processed Parquet**

1. In Athena Query Editor, select database: `handson_data_lake`
2. Run:
   ```sql
   -- Business Query: Product revenue from processed Parquet data
   SELECT
       product,
       COUNT(*) AS order_count,
       ROUND(SUM(amount), 2) AS total_revenue,
       ROUND(AVG(amount), 2) AS avg_order_value
   FROM orders
   WHERE year = '2024' AND month = '01'
   GROUP BY product
   ORDER BY total_revenue DESC;
   ```
3. Click **Run** (orange button)
4. **Expected Execution time:** 2–5 seconds (Parquet is fast)

**Expected Results:**
| product | order_count | total_revenue | avg_order_value |
|---------|-------------|---------------|-----------------|
| WIDGET B | 3 | 149.97 | 49.99 |
| WIDGET A | 4 | 119.96 | 29.99 |
| WIDGET C | 3 | 59.97 | 19.99 |

**📸 Screenshot 5a:** Athena query results showing product revenue

**Step 5.4: Compare CSV vs Parquet Query Cost**

1. Note the "Data scanned" shown below the results
2. Compare with same query on raw CSV data:
   ```sql
   -- Same query on raw CSV (from Project 9.1)
   SELECT product_name, COUNT(*), SUM(amount)
   FROM raw_db.orders
   WHERE year = '2024' AND month = '01'
   GROUP BY product_name;
   ```
3. **Expected observation:**
   - CSV query: scans ~280 bytes (entire file)
   - Parquet query: scans less — only the columns you selected

**Decision Point 10:** Query performance comparison
| Data format | Data scanned | Athena cost | Query time |
|-------------|-------------|-------------|------------|
| CSV (raw zone) | ~280 bytes | $0.0000014 | ~3s |
| Parquet (processed zone) | < 100 bytes | $0.0000005 | ~2s |
| Parquet at scale (1TB) | ~100GB | $0.50 | ~10s |
| CSV at scale (1TB) | 1TB | $5.00 | ~120s |

**📸 Screenshot 5b:** Side-by-side Athena query results: CSV vs Parquet data scanned comparison

**Step 5.5: Query the Daily Aggregates Table**

The ETL job also wrote a `orders_daily` dataset. Create a table for it:

```sql
-- Create table for daily aggregates
CREATE EXTERNAL TABLE IF NOT EXISTS handson_data_lake.orders_daily (
  product         string,
  order_count     bigint,
  total_revenue   double,
  avg_order_value double,
  unique_customers bigint
)
PARTITIONED BY (year string, month string)
STORED AS PARQUET
LOCATION 's3://handson-data-lake-YOUR_ACCOUNT_ID/processed/orders_daily/';

-- Register partitions
MSCK REPAIR TABLE orders_daily;

-- Query daily aggregates
SELECT product, order_count, total_revenue
FROM orders_daily
WHERE year = '2024' AND month = '01'
ORDER BY total_revenue DESC;
```

**📸 Screenshot 5c:** Athena query on `orders_daily` showing aggregated results

---

### STEP 6 — Create a Glue Trigger (Daily Schedule)

**Prerequisites Check:**
- ✅ Job `handson-etl-job` exists and ran successfully
- ✅ Required permissions: `glue:CreateTrigger`
- ✅ Understanding: Trigger will NOT fire automatically until activated

**Step 6.1: Navigate to Glue Triggers**

1. In Glue Console, left sidebar → click **"Triggers"** (under ETL section)
2. **Expected View:** Empty triggers list
3. Click **"Add trigger"** (orange button)

**📸 Screenshot 6a:** Empty Triggers list before creation

**Step 6.2: Configure Trigger Properties**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `handson-etl-daily` | Consistent with Terraform naming |
| Trigger type | **Schedule** | Time-based recurring trigger |
| Frequency | **Custom (cron expression)** | More precise than built-in options |
| Cron expression | `cron(0 2 * * ? *)` | 2:00 AM UTC every day |

**Decision Point 11:** Trigger type
| Type | Use Case | For This Project |
|------|----------|-----------------|
| Schedule | Time-based: run at 2am daily | ✅ Batch ETL pattern |
| On demand | Manual trigger only | ❌ Not automated |
| Event | Triggered by job success/failure | ❌ No chain needed yet |
| Conditional | Complex multi-job conditions | ❌ Advanced pattern |

**AWS Cron Expression Format (different from standard cron):**
```
cron(Minutes  Hours  Day-of-month  Month  Day-of-week  Year)
cron(0        2      *             *      ?            *)
     ↑        ↑      ↑             ↑      ↑            ↑
     min 0    2am    any day       any    ? = no spec   any year
```

> ⚠️ AWS cron has 6 fields (not 5). The `?` is required when Day-of-month OR Day-of-week is set to `*`.

**Step 6.3: Link Job to Trigger**

1. Under **"Jobs to trigger"** section, click **"Add job"**
2. Select `handson-etl-job` from dropdown
3. Click **"Add"**
4. **Expected View:** `handson-etl-job` listed under jobs to trigger

**Step 6.4: Save Trigger (do NOT activate)**

1. Click **"Add trigger"** (save button)
2. **Expected Outcome:** Trigger listed with status **CREATED**

> ⚠️ **Important for learning:** Leave trigger in CREATED state, not ACTIVATED.
> Activating it means it fires every day at 2am and costs ~$0.15/day.
> To activate later: Actions → Activate trigger
> To deactivate: Actions → Deactivate trigger

**Troubleshooting:**
- Invalid cron expression: Use the AWS cron validator — note the 6-field format
- Job not in dropdown: Job creation failed — return to Step 2
- Permission denied: Add `glue:CreateTrigger` to your IAM user

**📸 Screenshot 6b:** Trigger `handson-etl-daily` with CREATED status (not ACTIVATED)

---

### STEP 7 — Monitor with CloudWatch

**Prerequisites Check:**
- ✅ Job ran at least once (from Step 3)
- ✅ Required permissions: `logs:GetLogEvents`, `cloudwatch:GetMetricData`

**Step 7.1: View Glue Job Logs**

1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. Left sidebar → **Logs** → **Log groups**
3. Search for: `/aws-glue/jobs/output`
4. **Expected View:** Log group with streams named by job run ID
5. Click on a log stream
6. **Expected View:** Your `print()` statements from `etl_job.py`

**Step 7.2: View Glue Metrics**

1. Left sidebar → **Metrics** → **All metrics**
2. Search: `Glue`
3. Select namespace: **AWS/Glue**
4. Available metrics:
   - `glue.driver.aggregate.numCompletedTasks` — tasks completed
   - `glue.driver.aggregate.numFailedTasks` — tasks failed
   - `glue.ALL.s3.filesystem.read_bytes` — bytes read from S3
   - `glue.ALL.s3.filesystem.write_bytes` — bytes written to S3
5. Check these after a job run to confirm data volumes

**📸 Screenshot 7a:** CloudWatch metrics for Glue job showing bytes written

---

### Console UI Summary — Resources Created

| Resource | Name | Location in Console |
|----------|------|-------------------|
| S3 script | `scripts/etl_job.py` | S3 → bucket → scripts/ |
| Glue Job | `handson-etl-job` | Glue → ETL Jobs |
| Job run | Run ID `jr_xxx` | Glue → Jobs → Runs tab |
| Trigger | `handson-etl-daily` | Glue → Triggers |
| Processed Parquet | `processed/orders/` | S3 → bucket → processed/ |
| Daily aggregates | `processed/orders_daily/` | S3 → bucket → processed/ |
| CloudWatch Logs | `/aws-glue/jobs/output` | CloudWatch → Log groups |

---

### Screenshot Summary (Complete List for Project 9.2)

| # | What to Capture | When |
|---|----------------|------|
| P0a | IAM role `handson-glue-role` with policies | Before starting |
| P0b | S3 raw data — `orders.csv` at partition path | Before starting |
| 1a | S3 bucket root showing zone folders | During Step 1 |
| 1b | `scripts/` folder created in bucket | During Step 1 |
| 1c | `etl_job.py` uploaded — success banner | During Step 1 |
| 2a | Glue console home | Before job creation |
| 2b | ETL Jobs list (empty state) | Before job creation |
| 2c | Script editor with `etl_job.py` loaded | During Step 2 |
| 2d | Job details — name, role, version filled | During Step 2 |
| 2e | Worker config — G.1X, 2 workers, 60min | During Step 2 |
| 2f | Job parameters — all 7 parameters | During Step 2 |
| 2g | Job saved — success banner | After Step 2 |
| 3a | Job run started — Run ID notification | During Step 3 |
| 3b | Job in RUNNING state | During Step 3 |
| 3c | Job SUCCEEDED — duration shown | After Step 3 |
| 3d | CloudWatch logs — `ETL job complete!` | After Step 3 |
| 4a | S3 processed/orders/year=X/month=X/.parquet | After Step 4 |
| 4b | File size comparison: CSV vs Parquet | After Step 4 |
| 5a | Athena product revenue query results | During Step 5 |
| 5b | Athena: data scanned CSV vs Parquet | During Step 5 |
| 5c | Athena orders_daily aggregates | During Step 5 |
| 6a | Triggers list (empty) | Before Step 6 |
| 6b | Trigger created with CREATED status | After Step 6 |
| 7a | CloudWatch Glue metrics | After Step 7 |

**Total: 23 screenshots** — capture all to build a complete hands-on portfolio.
