# Project 9.2 — AWS Glue ETL Pipeline
# PART 2: Folder Structure & Console UI Implementation

---

## 4. PROJECT FOLDER STRUCTURE

```
project_9.2_glue_etl/
│
├── src/
│   └── etl_job.py                  ← PySpark ETL script (runs inside Glue)
│
├── terraform/
│   └── main.tf                     ← All Terraform resources (Glue job, trigger, S3 upload)
│
├── docs/
│   └── architecture.md             ← Architecture diagrams and pipeline flow
│
├── screenshots/                    ← (create this folder) — capture your screenshots here
│
├── README.md                       ← Quick start and lessons learned
├── steps.md                        ← Deployment and run commands
├── verify.md                       ← Verification and validation commands
├── cost_estimate.md                ← DPU pricing breakdown
├── GUIDE_PART1_overview_architecture.md   ← This guide Part 1
├── GUIDE_PART2_console_ui.md              ← This guide Part 2
├── GUIDE_PART3_cli_terraform.md           ← This guide Part 3
└── GUIDE_PART4_verification_cleanup.md   ← This guide Part 4
```

### File-by-File Purpose

| File | Purpose |
|------|---------|
| `src/etl_job.py` | The actual PySpark code that runs on Glue workers. Uploaded to S3 before the job runs. |
| `terraform/main.tf` | IaC — creates Glue job, uploads script, creates daily trigger |
| `docs/architecture.md` | Architecture reference with pipeline flow diagrams |
| `README.md` | Quick start: one-command deploy + key lessons |
| `steps.md` | Phase-by-phase CLI commands to deploy, run, and verify |
| `verify.md` | Checklist + CLI commands to confirm everything works |
| `cost_estimate.md` | Billing breakdown — DPU-hours, run duration, monthly estimate |

---

## 5A. CONSOLE UI IMPLEMENTATION (AWS Management Console)

> As of June 2025 — AWS Glue Console (new unified interface)
> Region: us-east-1 (N. Virginia)

---

### PHASE 0 — Prerequisites Check Before Starting

**Prerequisites Check:**
- ✅ Project 9.1 deployed and S3 bucket exists
- ✅ Glue IAM Role from Project 9.1 exists (check IAM → Roles → search "glue")
- ✅ Raw CSV data uploaded to `s3://YOUR_BUCKET/raw/orders/`
- ✅ Region set to us-east-1 in top-right of AWS Console

**📸 Screenshot 0:** IAM Roles list showing your Glue role — capture before starting

---

### STEP 1 — Upload the ETL Script to S3

The Glue job reads its Python script from S3. You must upload it first.

#### Step 1.1 — Navigate to S3

1. Go to [https://s3.console.aws.amazon.com/s3/](https://s3.console.aws.amazon.com/s3/)
2. **Expected View:** List of your S3 buckets
3. **If Different:** Make sure region selector at top shows "Global" (S3 is global)

#### Step 1.2 — Open Your Data Lake Bucket

1. Click on your data lake bucket (from Project 9.1 — name like `handson-data-lake-123456789012`)
2. **Expected View:** Bucket contents with folders: `raw/`, `temp/`, `athena-results/`
3. **If you don't see these folders:** Project 9.1 was not fully deployed. Go back and run `terraform apply` there first.

#### Step 1.3 — Create the `scripts/` Folder

1. Click **"Create folder"** button (orange)
2. **Folder name:** `scripts`
3. Leave Server-side encryption as default (SSE-S3)
4. Click **"Create folder"**
5. **Expected View:** `scripts/` now appears in the bucket listing

**📸 Screenshot 1:** Bucket listing showing `scripts/` folder created

#### Step 1.4 — Upload the ETL Script

1. Click on the `scripts/` folder to open it
2. Click **"Upload"** button (orange)
3. Click **"Add files"**
4. Navigate to your local path: `D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl\src\etl_job.py`
5. Select `etl_job.py` and click **Open**
6. **Expected View:** File listed with size ~4KB

**Decision Point — Storage Class:**
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Standard | Frequently accessed | ✅ Scripts are re-read every job run |
| Standard-IA | Infrequently accessed | ❌ Script runs daily |
| Intelligent-Tiering | Unknown access pattern | ❌ Overkill for a script |

7. Leave storage class as **Standard**
8. Click **"Upload"** at the bottom
9. **Expected View:** Upload succeeded — green checkmark, file listed

**📸 Screenshot 2:** `etl_job.py` successfully uploaded to `s3://bucket/scripts/`

---

### STEP 2 — Create the Glue ETL Job

#### Step 2.1 — Navigate to AWS Glue

1. Go to [https://console.aws.amazon.com/glue/](https://console.aws.amazon.com/glue/)
2. **Expected View:** Glue Studio welcome page OR Glue home with left navigation panel
3. **If you see "Getting Started" banner:** Dismiss it or click "Continue to AWS Glue"

#### Step 2.2 — Go to ETL Jobs

1. In the left navigation, find **"ETL Jobs"**
   - If you see the new Glue Studio UI: click **"ETL Jobs"** in the left sidebar
   - If you see classic Glue UI: click **"Jobs"** under "ETL" section
2. **Expected View:** Empty jobs list (or existing jobs if you have them)

**📸 Screenshot 3:** Glue ETL Jobs list page (before creating job — shows empty state)

#### Step 2.3 — Create New Job

1. Click **"Create job"** button (orange, top-right)
2. **Expected View:** Job creation options panel

**Decision Point — Job Creation Method:**
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Visual ETL (drag & drop) | Learning, simple pipelines | ❌ Generates bloated code |
| Script editor | Custom PySpark, full control | ✅ We have our own script |
| Jupyter notebook | Interactive development | ❌ Not needed here |

3. Select **"Script editor"**
4. **Sub-option — Engine:**

| Engine | Use Case | For This Project |
|--------|----------|-----------------|
| Spark | Large-scale batch ETL, PySpark | ✅ Our script is PySpark |
| Spark Streaming | Real-time data processing | ❌ Not streaming |
| Python Shell | Lightweight Python, no Spark | ❌ Our script needs Spark |
| Ray | Distributed Python ML | ❌ Not ML workload |

5. Select **"Spark"**
6. **Option: Start fresh or upload script?**

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Start fresh | Write code in browser | ❌ We have our own script |
| Upload and edit | Use existing script file | ✅ We already uploaded to S3 |

7. Select **"Upload and edit an existing script"**
8. Click **"Choose"** next to "Script path"

#### Step 2.4 — Set Script Location

1. In the file browser, navigate to your bucket → `scripts/` → `etl_job.py`
2. Click **"Choose"**
3. **Expected View:** Script path populated with `s3://YOUR_BUCKET/scripts/etl_job.py`

**📸 Screenshot 4:** Script editor showing your etl_job.py code loaded in browser

#### Step 2.5 — Configure Job Properties

Scroll down to find **"Job details"** tab (or click it).

**Basic Properties:**

| Field | Value | Why |
|-------|-------|-----|
| Name | `handson-etl-job` | Consistent naming with Terraform |
| Description | `Orders CSV to Parquet ETL` | Self-documenting |
| IAM Role | Select your Glue role from Project 9.1 | Required — Glue assumes this role |
| Type | Spark | Already selected |
| Glue version | **Glue 4.0** | Latest — supports Python 3.10, better performance |
| Language | Python 3 | Our script is Python |

**Worker Configuration:**

| Field | Value | Why |
|-------|-------|-----|
| Worker type | **G.1X** | 4 vCPU + 16GB RAM — sufficient for orders data |
| Number of workers | **2** | Minimum for Spark distributed execution |
| Max retries | **1** | Retry once on transient failures |
| Job timeout | **60** minutes | Prevent cost overrun on stuck jobs |

> **Why G.1X and 2 workers?**
> Our orders CSV is small (< 500MB). G.1X provides enough memory.
> Glue requires minimum 2 workers — 1 driver + 1 executor.
> Using G.2X or more workers is wasteful for small data.

**Advanced Properties:**

| Field | Value | Why |
|-------|-------|-----|
| Script path | `s3://bucket/scripts/etl_job.py` | Already set |
| Temporary directory | `s3://bucket/temp/` | Required for Glue shuffle data |
| Spark UI logs | Enable → `s3://bucket/sparkhistory/` | (Optional) View Spark DAG |

**📸 Screenshot 5:** Job details panel showing all configuration values filled in

#### Step 2.6 — Add Job Parameters

In "Job details", scroll to **"Job parameters"** section.

Click **"Add new parameter"** for each row below:

| Key (with -- prefix) | Value | Purpose |
|----------------------|-------|---------|
| `--job-bookmark-option` | `job-bookmark-enable` | Enable incremental processing |
| `--enable-metrics` | `true` | CloudWatch Spark metrics |
| `--enable-continuous-cloudwatch-log` | `true` | Real-time log streaming |
| `--source_bucket` | `YOUR_BUCKET_NAME` | Passed to script as arg |
| `--target_bucket` | `YOUR_BUCKET_NAME` | Passed to script as arg |
| `--database_name` | `handson_data_lake` | Glue Catalog database |
| `--TempDir` | `s3://YOUR_BUCKET/temp/` | Glue temp storage |

> **Important:** Keys MUST start with `--` (two dashes). Without this prefix,
> Glue will not pass them as script arguments.

**📸 Screenshot 6:** Job parameters section showing all 7 parameters entered

#### Step 2.7 — Save the Job

1. Click **"Save"** button (top-right)
2. **Expected View:** Green banner "Job saved successfully"
3. **If Error "Role not found":** Your IAM role ARN is wrong — go to IAM → Roles and copy the exact ARN
4. **If Error "Script not found":** Double-check the S3 path is exactly `s3://bucket/scripts/etl_job.py`

**📸 Screenshot 7:** Job saved — green success banner with job name `handson-etl-job`

---

### STEP 3 — Run the Glue Job Manually

#### Step 3.1 — Start Job Run

1. You should be on the job detail page
2. Click **"Run"** button (orange, top-right)
3. **Expected View:** "Run job" confirmation dialog

**Decision Point — Job Run Options:**
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Run with defaults | Use saved job parameters | ✅ We configured all params already |
| Override parameters | One-time parameter change | ❌ Not needed now |

4. Leave defaults and click **"Run"**
5. **Expected View:** "Job run started" notification with a Run ID like `jr_abc123...`

**📸 Screenshot 8:** Job run started — notification with Run ID visible

#### Step 3.2 — Monitor Job Run

1. Click on **"Runs"** tab on the job detail page (or navigate to ETL Jobs → click job → Runs tab)
2. **Expected View:** Table showing your job run with status:
   - `STARTING` (0–2 min) — Glue spinning up workers
   - `RUNNING` (2–10 min) — PySpark executing
   - `SUCCEEDED` — completed successfully
   - `FAILED` — check logs (see troubleshooting below)

3. Refresh the page every 30 seconds (or click the refresh icon)
4. Total expected duration: **5–12 minutes** for first run

**What is happening internally during STARTING:**
- Glue allocates EC2 instances for workers in AWS-managed account
- Apache Spark is initialized on the workers
- Your script is downloaded from S3 to the workers
- Spark context is created with 2 executors

**📸 Screenshot 9:** Job run in RUNNING state — shows start time and duration counter

**📸 Screenshot 10:** Job run SUCCEEDED — shows duration and DPU hours consumed

#### Step 3.3 — View Job Logs

1. Click on the Run ID link in the Runs table
2. Click **"CloudWatch Logs"** link (or go to tab "Output logs")
3. **Expected View:** Log stream with output like:
   ```
   Reading raw orders data...
   Raw record count: 1000
   Transforming data...
   Clean record count: 998
   Writing processed data to S3...
   ETL job complete!
   ```
4. **If logs are empty:** Wait 2–3 minutes after job completes for logs to propagate

**Inline Troubleshooting:**
- "AccessDenied" in logs → IAM role missing S3 permissions — check role policy
- "FileNotFoundException: s3://bucket/raw/orders/" → raw data not uploaded — upload CSV first
- "JobRunState: TIMEOUT" → increase timeout or reduce data size for testing
- "GlueException: No module named awsglue" → script uses wrong import — verify etl_job.py

**📸 Screenshot 11:** CloudWatch log stream showing "ETL job complete!" message

---

### STEP 4 — Create a Glue Trigger (Daily Schedule)

#### Step 4.1 — Navigate to Triggers

1. In Glue left navigation, click **"Triggers"** (under ETL section)
2. **Expected View:** Empty triggers list
3. Click **"Add trigger"** (orange button)

#### Step 4.2 — Configure Trigger

| Field | Value | Why |
|-------|-------|-----|
| Name | `handson-etl-daily` | Descriptive name |
| Trigger type | **Schedule** | Time-based automatic trigger |
| Frequency | **Daily** | Or use "Custom (cron expression)" |
| Cron expression | `cron(0 2 * * ? *)` | 2:00 AM UTC every day |
| Start the trigger | **On demand** for now | Don't activate during learning |

**Decision Point — Trigger Type:**
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Schedule | Time-based, recurring | ✅ Daily ETL runs |
| On demand | Manual trigger only | ❌ Not automated |
| Event | Triggered by another job | ❌ No dependency chain yet |
| Conditional | Trigger based on job state | ❌ Advanced use case |

#### Step 4.3 — Add Jobs to Trigger

1. Under "Jobs to trigger", click **"Add job"**
2. Select `handson-etl-job`
3. Click **"Add"**

#### Step 4.4 — Save Trigger

1. Click **"Add trigger"** (or "Save")
2. **Expected View:** Trigger listed with status **CREATED** (not ACTIVATED)
3. **Important:** Leave it in CREATED state during learning to avoid daily charges

**📸 Screenshot 12:** Trigger `handson-etl-daily` created with CREATED status (not active)

---

### STEP 5 — Verify S3 Output

#### Step 5.1 — Check Processed Parquet Files

1. Go to S3 → your data lake bucket
2. Click on `processed/` folder
3. Click on `orders/` subfolder
4. **Expected View:** Partition folders like `year=2024/`
5. Drill down: `year=2024/` → `month=01/` → you should see `.parquet` files

**📸 Screenshot 13:** S3 processed/orders/ showing year=XXXX/month=XX partition structure

#### Step 5.2 — Quick Athena Query on Processed Data

1. Go to [https://console.aws.amazon.com/athena/](https://console.aws.amazon.com/athena/)
2. Make sure workgroup is `handson-data-lake` (from Project 9.1) or `primary`
3. Select database: `handson_data_lake`
4. Run this query:
   ```sql
   SELECT product, SUM(amount) AS revenue, COUNT(*) AS orders
   FROM orders
   GROUP BY product
   ORDER BY revenue DESC
   LIMIT 10;
   ```
5. **Expected View:** Results table with product names and revenue totals
6. **If "Table not found":** Glue Catalog table was not updated — run the Glue Crawler from Project 9.1

**📸 Screenshot 14:** Athena query results showing product revenue from processed Parquet data

---

### Console UI Summary — What Was Created

| Resource | Name | Location in Console |
|----------|------|-------------------|
| Glue Job | `handson-etl-job` | Glue → ETL Jobs |
| ETL Script | `scripts/etl_job.py` | S3 → bucket → scripts/ |
| Job Run | Job run ID | Glue → ETL Jobs → Runs tab |
| Trigger | `handson-etl-daily` | Glue → Triggers |
| Processed data | `processed/orders/` | S3 → bucket → processed/ |
