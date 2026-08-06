# Complete Implementation Guide — Project 9.5: Airflow Data Orchestration
# Apache Airflow on Amazon MWAA + Local Docker + DAG-as-Code

**Level:** Beginner | **Stage:** 09 — Data Engineering | **Estimated Time:** 3–4 hours
**Local cost:** $0 (Docker) | **MWAA cost:** ~$670/month (production only)

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
**Data Pipeline Orchestration with Apache Airflow on AWS MWAA**

### Business / Problem Statement

Your data engineering team now has three separate pipelines:
- A Glue ETL job that runs manually
- A Spark job on EMR Serverless
- A dbt model that needs Glue to finish first

Currently, a data engineer manually triggers them in order at 2am every morning.
If the Glue job fails at 3am, they don't know until 8am when reports are missing.
If the S3 raw data arrives late, Spark fails. There is no retry logic.

**Orchestration** solves this:
- Define the pipeline once as Python code (a DAG)
- Airflow schedules it, handles dependencies, retries failures automatically
- Sends SNS alerts on failure — engineer wakes up only when needed
- Full audit trail: every run logged, every task's status visible

### Pipeline Input → Output

```
═══════════════════════════════════════════════════════════════════════════
 PIPELINE TRIGGER
═══════════════════════════════════════════════════════════════════════════
Schedule:    Daily at 02:00 UTC  (cron: "0 2 * * *")
Manual run:  Airflow UI → Trigger DAG  OR  airflow dags trigger

═══════════════════════════════════════════════════════════════════════════
 TASK 1 — check_source_data  (S3KeySensor)
═══════════════════════════════════════════════════════════════════════════
INPUT:   S3 path to watch:
         raw/orders/{YYYY}/{MM}/{DD}/orders_{YYYYMMDD}.csv
         (file placed by upstream system)
ACTION:  Poll S3 every 60 seconds until file appears (timeout: 1 hour)
OUTPUT:  Task SUCCESS when file exists → unblocks next task
         Task FAILED if file not found within 1 hour

═══════════════════════════════════════════════════════════════════════════
 TASK 2 — run_glue_etl  (GlueJobOperator)
═══════════════════════════════════════════════════════════════════════════
INPUT:   Glue job name: handson-etl-job
         Args: --execution_date, --source_prefix, --target_prefix
ACTION:  Starts Glue job, waits for SUCCEEDED/FAILED
OUTPUT:  Parquet files written to:
         processed/orders/year=YYYY/month=MM/day=DD/
         Task SUCCESS → unblocks validate_data_quality

═══════════════════════════════════════════════════════════════════════════
 TASK 3 — validate_data_quality  (PythonOperator)
═══════════════════════════════════════════════════════════════════════════
INPUT:   S3 prefix: processed/orders/year=YYYY/month=MM/day=DD/
ACTION:  Checks files exist and total size > 1 KB
         Pushes metrics to XCom: processed_file_count, processed_size_bytes
OUTPUT:  Task SUCCESS → unblocks run_dbt_models
         Task FAILED  → retries 2x → pipeline fails → SNS alert sent

═══════════════════════════════════════════════════════════════════════════
 TASK 4 — run_dbt_models  (PythonOperator / BashOperator)
═══════════════════════════════════════════════════════════════════════════
INPUT:   dbt project at DBT_PROJECT_DIR
         Redshift connection via environment variables
         Variable: execution_date = {{ ds }}
ACTION:  Runs: dbt run --select orders+
         Then:  dbt test --select orders+
OUTPUT:  Redshift analytics tables updated in schema: analytics
         Task SUCCESS → unblocks notify_success

═══════════════════════════════════════════════════════════════════════════
 TASK 5a — notify_success  (PythonOperator via SNS)
═══════════════════════════════════════════════════════════════════════════
INPUT:   trigger_rule="all_success" (only runs if all previous tasks passed)
ACTION:  sns.publish() to SNS topic
OUTPUT:  Email/SMS: "✓ Orders Pipeline SUCCESS — 2024-01-15"
         Message includes: DAG, Run ID, execution_date, Redshift schema

═══════════════════════════════════════════════════════════════════════════
 TASK 5b — notify_failure  (on_failure_callback)
═══════════════════════════════════════════════════════════════════════════
INPUT:   Fires automatically when ANY task fails
ACTION:  sns.publish() with failed task name + error message
OUTPUT:  Email/SMS: "✗ Orders Pipeline FAILED — 2024-01-15"
         Message includes: which task failed, the exception message
```

### Learning Objectives

By the end of this project you will be able to:
- [ ] Explain what orchestration is and why it's needed over cron jobs
- [ ] Understand DAG, Task, Operator, Sensor, XCom as Airflow concepts
- [ ] Run Airflow locally with Docker Compose (zero cost)
- [ ] Write a DAG with task dependencies using `>>` syntax
- [ ] Use S3KeySensor to wait for upstream data
- [ ] Use GlueJobOperator to trigger and monitor a Glue job
- [ ] Use PythonOperator to run custom Python logic
- [ ] Configure retries, timeouts, and failure callbacks
- [ ] Set Airflow Variables for environment-specific config
- [ ] Set up Airflow Connections (aws_default)
- [ ] Trigger DAGs manually via UI and CLI
- [ ] Read task instance logs in the Airflow UI
- [ ] Understand when to use MWAA vs local/self-hosted Airflow

---

## 2. Architecture & Concepts

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│               AIRFLOW ORCHESTRATION PIPELINE                               │
│          Schedule: 0 2 * * * (2am UTC daily)                               │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              AIRFLOW SCHEDULER                                       │  │
│  │  Reads DAG file → checks schedule → submits tasks to executor       │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│   ┌─────────────────────────────▼──────────────────────────────────────┐  │
│   │                    DAG: daily_data_pipeline                         │  │
│   │                                                                     │  │
│   │  [1] check_source_data (S3KeySensor)                               │  │
│   │        │ Polls S3 every 60s for raw/orders/YYYY/MM/DD/*.csv        │  │
│   │        ▼                                                            │  │
│   │  [2] run_glue_etl (GlueJobOperator)                                │  │
│   │        │ Starts handson-etl-job, waits for SUCCEEDED               │  │
│   │        ▼                                                            │  │
│   │  [3] run_dbt_transformations (PythonOperator)                      │  │
│   │        │ Runs dbt run + dbt test on Redshift                       │  │
│   │        ▼                                                            │  │
│   │  [4] validate_data_quality (PythonOperator)                        │  │
│   │        │ Checks S3 output files exist and have correct size        │  │
│   │        │                                                            │  │
│   │        ├──▶ [5a] notify_success (SnsPublishOperator)               │  │
│   │        │         trigger_rule="all_success"                         │  │
│   │        │                                                            │  │
│   │        └──▶ [5b] notify_failure (SnsPublishOperator)               │  │
│   │                  trigger_rule="one_failed"                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXTERNAL SERVICES CALLED BY TASKS                                   │  │
│  │  Amazon S3       ← S3KeySensor reads bucket                         │  │
│  │  AWS Glue        ← GlueJobOperator triggers job                     │  │
│  │  Amazon Redshift ← dbt connects to run SQL models                   │  │
│  │  Amazon SNS      ← SnsPublishOperator sends notifications           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  RUNTIME OPTIONS:                                                          │
│  ┌────────────────────────┐  ┌────────────────────────────────────────┐  │
│  │  LOCAL DOCKER (Learn)  │  │  AMAZON MWAA (Production)              │  │
│  │  docker compose up -d  │  │  Fully managed, auto-scaling           │  │
│  │  http://localhost:8080 │  │  ~$670/month (mw1.small)               │  │
│  │  Cost: $0              │  │  WebserverUrl via Console/CLI          │  │
│  └────────────────────────┘  └────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Core AWS Services

| Service | Role | Free Tier? |
|---------|------|-----------|
| **Amazon MWAA** | Managed Apache Airflow environment | ❌ ~$315+/month |
| **Amazon S3** | DAG file storage, raw/processed data | ✅ 5 GB free |
| **AWS Glue** | ETL job triggered by Airflow task | ❌ $0.44/DPU-hr |
| **Amazon SNS** | Pipeline success/failure notifications | ✅ 1M publishes free |
| **Amazon Redshift** | Analytics database (dbt target) | ❌ Expensive |
| **CloudWatch Logs** | Airflow task execution logs | ✅ 5 GB free |

### Key Concepts Explained

**DAG (Directed Acyclic Graph):**
```python
# A DAG is a Python file that defines tasks and their dependencies
# "Directed" = tasks have a direction (A runs before B)
# "Acyclic"  = no circular dependencies (A→B→A is forbidden)

check_source_data >> run_glue_etl >> validate_data_quality >> notify_success
#         ↑                                                          ↑
#  First task (no dependencies)                    Last task (depends on all before it)
```

**Operator — what a task does:**
```
PythonOperator  → runs a Python function
BashOperator    → runs a shell command
GlueJobOperator → starts an AWS Glue ETL job and waits
S3KeySensor     → waits for a file to appear in S3
SnsPublishOperator → publishes a message to SNS topic
```

**Sensor — waits for a condition:**
```python
S3KeySensor(
    task_id="check_source_data",
    bucket_name="my-bucket",
    bucket_key="raw/orders/2024/01/15/orders_20240115.csv",
    poke_interval=60,   # check every 60 seconds
    timeout=3600,       # give up after 1 hour
    mode="reschedule",  # release worker slot while waiting
)
# Without sensor: dbt would start while Glue is still running → failure
# With sensor: dbt only starts after S3 file confirmed present
```

**XCom — pass data between tasks:**
```python
# Task A pushes a value
context["task_instance"].xcom_push(key="file_count", value=42)

# Task B pulls the value from Task A
count = context["task_instance"].xcom_pull(task_ids="validate_data_quality", key="file_count")
# XCom is stored in Airflow's metadata database
# ⚠️ Only for small data — not for DataFrames or large files
```

**Airflow Variable — environment-specific config:**
```python
# Set in UI: Admin → Variables
# Or via CLI: airflow variables set data_lake_bucket my-bucket-name
DATA_LAKE_BUCKET = Variable.get("data_lake_bucket", default_var="my-data-lake-bucket")
# Avoids hardcoding bucket names, job names, ARNs in DAG code
```

**Retry logic:**
```python
DEFAULT_ARGS = {
    "retries": 2,                          # retry failed task 2 times
    "retry_delay": timedelta(minutes=5),   # wait 5 minutes between retries
    "execution_timeout": timedelta(hours=2), # kill task if it runs > 2 hours
}
# Without retries: transient AWS API errors fail the whole pipeline
# With retries: Glue API timeout → wait 5 min → retry → usually succeeds
```

**Cron vs Airflow:**
```
Cron:
  0 2 * * * /scripts/run_glue.sh && /scripts/run_spark.sh
  Problem: if Glue takes 3h, Spark starts 3h late
  Problem: no retry logic
  Problem: no UI to see what failed
  Problem: no dependency management

Airflow DAG:
  Glue and Spark tasks are linked with >>
  Spark only starts after Glue reports SUCCEEDED
  Automatic retry on failure
  Full audit trail in Airflow UI
  SNS alert on failure
```

### Best Practices Followed

- **`catchup=False`** — don't backfill missed runs (prevents hundreds of historical runs)
- **`max_active_runs=1`** — prevents overlapping pipeline runs on the same data
- **`mode="reschedule"` on sensor** — releases worker slot while waiting, reduces cost
- **`on_failure_callback`** on DAG — fires on ANY task failure, single place for alerting
- **Airflow Variables for config** — no hardcoded bucket names, job names, or ARNs in code
- **`execution_timeout`** — kills runaway tasks, prevents zombie processes
- **`provide_context=True`** — injects `execution_date`, `ds`, `dag_run` into Python callables
- **Local Docker for development** — $0 cost, same API as MWAA

---

## 3. Prerequisites

### 3.1 AWS Account Setup (MWAA Path)
- Active AWS account
- **Region:** `us-east-1` (N. Virginia)
- VPC with at least 2 private subnets (MWAA requirement)
- S3 bucket for DAG files (created by Terraform)
- Billing alert at $20/day (MWAA is expensive)

> **⚠️ MWAA Cost Warning:**
> MWAA mw1.small costs ~$315/month for the environment PLUS ~$355/month per worker.
> **For learning: use Local Docker (Phase 1 of CLI method) — it's free and identical API.**
> Only deploy MWAA when you need a team-accessible production environment.

### 3.2 IAM Permissions Required (for YOUR user)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["airflow:*", "mwaa:*"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::handson-mwaa-*", "arn:aws:s3:::handson-mwaa-*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole","iam:AttachRolePolicy","iam:PutRolePolicy",
                 "iam:PassRole","iam:GetRole","iam:DeleteRole","iam:DetachRolePolicy"],
      "Resource": "arn:aws:iam::*:role/handson-*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:*"],
      "Resource": "*"
    }
  ]
}
```

### 3.3 Required Software

| Tool | Version | Install (Windows) | Purpose |
|------|---------|------------------|---------|
| Docker Desktop | latest | [docker.com/desktop](https://docker.com/desktop) | Local Airflow |
| AWS CLI | v2.x | `winget install Amazon.AWSCLI` | S3 uploads, MWAA CLI |
| Python | >= 3.9 | `winget install Python.Python.3.11` | DAG authoring |
| Git | latest | `winget install Git.Git` | Version control |
| VS Code | latest | `winget install Microsoft.VisualStudioCode` | DAG editing |

**Python packages for local testing:**
```powershell
pip install apache-airflow==2.8.1
pip install apache-airflow-providers-amazon==8.x
```

### 3.4 Environment Variables (PowerShell)

```powershell
$env:AWS_REGION     = "us-east-1"
$env:ACCOUNT        = aws sts get-caller-identity --query Account --output text
$env:MWAA_BUCKET    = "handson-mwaa-$env:ACCOUNT"
$env:MWAA_ENV_NAME  = "handson-airflow"
$env:SNS_TOPIC_ARN  = "arn:aws:sns:us-east-1:$($env:ACCOUNT):data-pipeline-alerts"

aws sts get-caller-identity
```

---

## 4. Project Folder Structure

```
project_9.5_airflow/
│
├── GUIDE.md                  ← This comprehensive guide (you are here)
├── README.md                 ← Quick start and lessons learned
├── steps.md                  ← CLI commands (PowerShell + Docker)
├── steps_awsconsoleui.md     ← Console UI steps (improved template)
├── verify.md                 ← Verification checklist
├── cost_estimate.md          ← MWAA vs local cost comparison
│
├── dags/
│   └── daily_pipeline.py     ← PRIMARY DAG: daily_data_pipeline
│                                Tasks: S3Sensor → Glue → dbt → Quality → SNS
│
├── code/
│   └── orders_dag.py         ← ADVANCED DAG: orders_data_pipeline
│                                Full featured: XCom, failure callback, doc_md
│
├── docs/
│   └── architecture.md       ← DAG flow diagrams, Airflow concepts, MWAA vs local
│
└── terraform/
    └── main.tf               ← S3 bucket for MWAA DAGs + IAM role
                                 (reference — Terraform not covered in this guide)
```

### File-by-File Explanation

| File | Purpose |
|------|---------|
| `dags/daily_pipeline.py` | The primary DAG uploaded to S3/MWAA. `dag_id="daily_data_pipeline"`. Simpler, more readable. |
| `code/orders_dag.py` | Advanced reference DAG. `dag_id="orders_data_pipeline"`. Shows XCom, failure callbacks, Variables, full docstrings. |
| `docs/architecture.md` | DAG execution flow diagrams, Airflow key concepts, local vs MWAA comparison |
| `terraform/main.tf` | S3 bucket (`handson-mwaa-ACCOUNT`) + IAM role (`handson-mwaa-role`) for MWAA |

### DAG Comparison

| Feature | `daily_pipeline.py` | `orders_dag.py` |
|---------|--------------------|--------------------|
| `dag_id` | `daily_data_pipeline` | `orders_data_pipeline` |
| S3 Sensor | ✅ | ✅ |
| Glue Operator | ✅ | ✅ |
| dbt task | PythonOperator | BashOperator |
| Quality check | ✅ | ✅ with XCom |
| Failure callback | `on_failure_callback` | `on_failure_callback` |
| Airflow Variables | account_id, sns_topic_arn | data_lake_bucket, glue_job_name, etc. |
| Complexity | Beginner | Intermediate |
| Use for | Learning → MWAA | Production reference |

---

## 5. Hands-on Implementation

---

## 5A. AWS Management Console Method

> **Recommended approach for learning:**
> Use Phase 1 (Local Docker) to learn Airflow at zero cost.
> Use Phase 2 (MWAA Console) only when you need a cloud-hosted environment.

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Docker Desktop installed and running
- ✅ AWS CLI configured with `aws sts get-caller-identity` working
- ✅ `dags/daily_pipeline.py` exists in the project folder
- ✅ Region: us-east-1 selected in AWS Console

**Step 0.1: Verify Docker is Running**
1. Open PowerShell or Command Prompt
2. Run: `docker --version`
3. **Expected:** `Docker version 24.x.x`
4. **If Not Running:** Open Docker Desktop from the system tray

**📸 Screenshot P0:** Docker Desktop showing engine is running

---

### STEP 1 — Run Airflow Locally with Docker Compose

> This is the recommended first step. Zero cost. Same Airflow API as MWAA.

**Prerequisites Check:**
- ✅ Docker Desktop running
- ✅ 4 GB RAM available for Docker containers
- ✅ Port 8080 not in use by another application

**Step 1.1: Create Local Airflow Directory**
1. Open PowerShell
2. Run:
```powershell
mkdir C:\airflow-local
cd C:\airflow-local
mkdir dags, logs, plugins
```

**Step 1.2: Download Docker Compose File**
```powershell
# Download official Airflow Docker Compose
Invoke-WebRequest `
  -Uri "https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml" `
  -OutFile "docker-compose.yaml"
```

**Step 1.3: Set Environment Variables**
```powershell
# Create .env file for Docker Compose
"AIRFLOW_UID=50000" | Out-File -FilePath .env -Encoding utf8
```

**Step 1.4: Initialize Airflow Database**
```powershell
docker compose up airflow-init
```

**Expected Output (last lines):**
```
airflow-init-1  | User "airflow" created with role "Admin"
airflow-init-1  | 2.8.1
airflow-init-1 exited with code 0
```

**Step 1.5: Start All Airflow Services**
```powershell
docker compose up -d
```

**Decision Point 1:** Verify all containers are running

**Expected containers:**
| Container | Purpose |
|-----------|---------|
| `airflow-webserver-1` | Airflow UI at port 8080 |
| `airflow-scheduler-1` | Schedules and triggers tasks |
| `airflow-worker-1` | Executes task instances |
| `airflow-postgres-1` | Metadata database |
| `airflow-redis-1` | Task queue (Celery broker) |

```powershell
docker compose ps
# Expected: All containers Status=running (healthy)
```

**Step 1.6: Open Airflow UI**
1. Open browser → `http://localhost:8080`
2. **Expected View:** Airflow login page
3. Username: `airflow` | Password: `airflow`
4. Click **Sign In**
5. **Expected View:** Airflow DAGs list (empty initially)

**Troubleshooting:**
- "Connection refused" on 8080: Wait 30 seconds for webserver to start, refresh
- Docker out of memory: Increase Docker Desktop memory to 4+ GB in Settings

**📸 Screenshot 1a:** Airflow UI login page at localhost:8080
**📸 Screenshot 1b:** Airflow DAGs list (empty — before uploading DAG)

---

### STEP 2 — Upload DAG to Local Airflow

**Prerequisites Check:**
- ✅ Airflow running at localhost:8080
- ✅ `dags/daily_pipeline.py` exists in the project

**Step 2.1: Copy DAG to Local dags/ Folder**

```powershell
# From the project root
Copy-Item `
  "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow\dags\daily_pipeline.py" `
  "C:\airflow-local\dags\"
```

**Step 2.2: Wait for DAG to Load**

Airflow scans the `dags/` folder every 30 seconds.
1. Wait 30–60 seconds
2. Refresh the Airflow UI at `http://localhost:8080`
3. **Expected View:** `daily_data_pipeline` appears in the DAGs list

**Decision Point 1:** DAG loaded vs error

| Status | What you see | Action |
|--------|-------------|--------|
| ✅ Loaded | DAG listed, no red banner | Proceed to Step 2.3 |
| ❌ Import error | Red banner at top of page | Check Step 2.4 |

**Step 2.3: Examine DAG in Graph View**
1. Click on `daily_data_pipeline`
2. Click **Graph** tab
3. **Expected View:** 6 boxes connected by arrows:
```
check_source_data → run_glue_etl → run_dbt_transformations → validate_data_quality
                                                                      ↓               ↓
                                                             notify_success   notify_failure
```

**📸 Screenshot 2a:** Airflow DAG graph showing all 6 tasks connected

**Step 2.4: Fix DAG Import Error (if any)**

If you see a red "Broken DAG" banner:
1. Click the error banner → shows the Python traceback
2. Common causes:

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: apache-airflow-providers-amazon` | Install: `pip install apache-airflow-providers-amazon` |
| `SyntaxError` | Fix Python syntax in `daily_pipeline.py` |
| `ImportError` | Wrong import path — check Airflow version |

---

### STEP 3 — Configure Airflow Connections

Airflow **Connections** store credentials for external services (AWS, Redshift, etc.)

**Step 3.1: Navigate to Connections**
1. Airflow UI → top menu → **Admin** → **Connections**
2. **Expected View:** Connections list

**📸 Screenshot 3a:** Admin → Connections list

**Step 3.2: Create AWS Connection**

1. Click **+** (Add) button
2. Fill in the form:

| Field | Value | Explanation |
|-------|-------|-------------|
| Connection Id | `aws_default` | Name used in DAG code (`aws_conn_id="aws_default"`) |
| Connection Type | **Amazon Web Services** | From the dropdown |
| AWS Access Key ID | your-access-key | From IAM user credentials |
| AWS Secret Access Key | your-secret-key | From IAM user credentials |
| Extra | `{"region_name": "us-east-1"}` | JSON with region |

3. Click **Save**

**Decision Point 1:** Connection type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Amazon Web Services | Standard AWS connection | ✅ Used by S3Sensor, GlueJobOperator |
| Generic | Custom conn string | ❌ Won't work with AWS providers |

**📸 Screenshot 3b:** AWS connection form filled in

**Step 3.3: Create Airflow Variables**

Variables store environment-specific values referenced in DAG code.

1. Airflow UI → **Admin** → **Variables**
2. Click **+** to add each variable:

| Key | Value | Used By |
|-----|-------|---------|
| `account_id` | `YOUR_12_DIGIT_ACCOUNT_ID` | S3 bucket name in daily_pipeline.py |
| `sns_topic_arn` | `arn:aws:sns:us-east-1:ACCOUNT:data-pipeline-alerts` | notify_success/failure tasks |
| `data_lake_bucket` | `handson-data-lake-YOUR_ACCOUNT_ID` | orders_dag.py |
| `glue_job_name` | `handson-etl-job` | run_glue_etl task |

**📸 Screenshot 3c:** Variables list showing all 4 variables set

---

### STEP 4 — Trigger and Monitor the DAG

**Prerequisites Check:**
- ✅ DAG loaded without import errors
- ✅ aws_default connection configured
- ✅ Variables set

**Step 4.1: Enable the DAG**
1. In the DAGs list, find `daily_data_pipeline`
2. The toggle on the left should be **blue/on** (enabled)
3. **If grey/off:** Click the toggle to enable it

**Decision Point 1:** Paused vs enabled DAGs
| State | Meaning | Action |
|-------|---------|--------|
| **Enabled (blue)** | Scheduler will run on schedule | ✅ Normal |
| **Paused (grey)** | Won't run automatically | Click toggle to enable |

**Step 4.2: Trigger DAG Manually**
1. Click the **▶ Trigger DAG** button (play icon) next to `daily_data_pipeline`
2. Click **Trigger** in the confirmation popup
3. **Expected View:** Run appears in the Last Run column

**📸 Screenshot 4a:** DAG trigger button and confirmation dialog

**Step 4.3: Watch Task Execution**
1. Click on the run date under **Last Run**
2. Click **Graph** to see the live task status
3. **Expected View:** Tasks colored by state:

| Color | State | Meaning |
|-------|-------|---------|
| 🟡 Yellow | Running | Task is executing |
| 🟢 Green | Success | Task completed OK |
| 🔴 Red | Failed | Task failed (check logs) |
| ⚪ Grey | None/queued | Not started yet |
| 🟠 Orange | Up for retry | Failed, waiting to retry |

**📸 Screenshot 4b:** DAG graph during run showing colored task states

**Step 4.4: View Task Logs**
1. Click on any task box (e.g., `check_source_data`)
2. Click **Log** button
3. **Expected View:** Task execution log with timestamps

For `check_source_data` (S3KeySensor), expect to see:
```
[2024-01-15 02:00:01] INFO - Poking S3 Key: raw/orders/2024/01/15/orders_20240115.csv
[2024-01-15 02:00:01] INFO - Key handson-data-lake-.../raw/orders/... does not exist.
[2024-01-15 02:01:01] INFO - Poking S3 Key: raw/orders/2024/01/15/orders_20240115.csv
...
```
(The sensor will "fail" in local Docker since there's no real S3 connection — that's expected in local testing)

**📸 Screenshot 4c:** Task log viewer showing poke attempts

---

### STEP 5 — Deploy DAG to Amazon MWAA (Production)

> **⚠️ Skip this step for learning — it costs ~$670/month.**
> Complete Steps 1–4 locally first, then use this section when deploying to production.

**Prerequisites Check:**
- ✅ Required permissions: `mwaa:CreateEnvironment`, `s3:PutObject`, `iam:CreateRole`, `iam:PassRole`
- ✅ VPC with 2+ private subnets (MWAA requirement)
- ✅ S3 bucket for DAGs (create via Console)
- ✅ Region: us-east-1

**Step 5.1: Create S3 Bucket for DAGs**
1. Search bar → **S3** → **Create bucket**
2. Bucket name: `handson-mwaa-YOUR_ACCOUNT_ID`
3. Region: us-east-1
4. Block all public access: ✅ enabled
5. Versioning: ✅ Enabled (required by MWAA)
6. Click **Create bucket**

**Step 5.2: Upload DAG File to S3**
1. Click on bucket `handson-mwaa-YOUR_ACCOUNT_ID`
2. Create folder: `dags`
3. Inside `dags/`: Upload `dags/daily_pipeline.py`
4. **Expected:** `dags/daily_pipeline.py` visible in S3

**📸 Screenshot 5a:** S3 bucket showing `dags/daily_pipeline.py`

**Step 5.3: Create IAM Role for MWAA**
1. IAM → Roles → **Create role**
2. **Custom trust policy** (paste exactly):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "airflow.amazonaws.com",
          "airflow-env.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. Role name: `handson-mwaa-role`
4. After creation, add inline policy `mwaa-policy` (see Section 3.2 IAM permissions)

**Step 5.4: Create MWAA Environment**
1. Search bar → **MWAA** → **Amazon MWAA**
2. Click **Create environment**

**Decision Point 1:** Environment class
| Class | Workers | RAM | Cost/month | For This Project |
|-------|---------|-----|------------|-----------------|
| mw1.small | 1 worker | 2 GB | ~$315 | ✅ Cheapest option for learning |
| mw1.medium | 2 workers | 4 GB | ~$630 | ❌ Overkill |
| mw1.large | 5 workers | 8 GB | ~$1,890 | ❌ Production scale |

**Fill in MWAA form:**

| Field | Value |
|-------|-------|
| Environment name | `handson-airflow` |
| Airflow version | `2.8.1` |
| DAG S3 path | `s3://handson-mwaa-ACCOUNT/dags/` |
| Execution role | `handson-mwaa-role` |
| VPC | Your VPC |
| Subnets | Select 2 private subnets |
| Security group | Create or select existing |
| Environment class | `mw1.small` |
| Max workers | `1` |

5. Click **Next** through all screens → **Create environment**
6. **Expected:** Status = **Creating** (takes 20–30 minutes)
7. **Expected:** Status → **Available** (Airflow is ready)

**Troubleshooting:**
- "No subnets available": MWAA requires private subnets (with NAT gateway) — not public
- "IAM role error": Role needs both `airflow.amazonaws.com` AND `airflow-env.amazonaws.com` as principals
- Creation stuck > 30 min: Check CloudFormation events in the AWS Console

**📸 Screenshot 5b:** MWAA environment `handson-airflow` Status = **Available**

**Step 5.5: Access MWAA Airflow UI**
1. Click on environment `handson-airflow`
2. Click **Open Airflow UI** button
3. **Expected View:** Airflow UI with `daily_data_pipeline` DAG listed

**📸 Screenshot 5c:** MWAA Airflow UI showing daily_data_pipeline DAG

---

## 5B. AWS CLI Method

> Run from project root. Docker + PowerShell for local. AWS CLI for MWAA.

---

### Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$BUCKET    = "handson-mwaa-$ACCOUNT"
$ENV_NAME  = "handson-airflow"
$ROLE_NAME = "handson-mwaa-role"

Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
```

---

### Phase 1 — Run Airflow Locally (Free — Start Here)

```powershell
# Step 1.1 — Create working directory
New-Item -ItemType Directory -Path C:\airflow-local -Force
Set-Location C:\airflow-local
New-Item -ItemType Directory -Path dags, logs, plugins -Force

# Step 1.2 — Download Docker Compose file
Invoke-WebRequest `
  -Uri "https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml" `
  -OutFile "docker-compose.yaml"

# Step 1.3 — Set UID environment variable
"AIRFLOW_UID=50000" | Out-File -FilePath .env -Encoding utf8

# Step 1.4 — Initialize Airflow (creates admin user, sets up DB)
docker compose up airflow-init
# Wait for: "User 'airflow' created with role 'Admin'"

# Step 1.5 — Start all services
docker compose up -d

# Step 1.6 — Verify containers are healthy
docker compose ps
# Expected: All 5 containers Status=Up (healthy)

# Step 1.7 — Open browser
Start-Process "http://localhost:8080"
# Login: airflow / airflow
```

---

### Phase 2 — Upload DAG to Local Airflow

```powershell
# Copy DAG file to local dags folder
Copy-Item `
  "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow\dags\daily_pipeline.py" `
  "C:\airflow-local\dags\"

# Airflow auto-detects within 30 seconds
Start-Sleep -Seconds 35

# Verify DAG loaded (check via scheduler container)
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list
# Expected: daily_data_pipeline listed with is_paused=False
```

---

### Phase 3 — Configure Airflow Connections (CLI)

```powershell
# Add aws_default connection
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow connections add aws_default `
  --conn-type "aws" `
  --conn-extra '{"region_name": "us-east-1"}'

# Note: For actual AWS access, add credentials:
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow connections add aws_default `
  --conn-type "aws" `
  --conn-login "YOUR_AWS_ACCESS_KEY_ID" `
  --conn-password "YOUR_AWS_SECRET_ACCESS_KEY" `
  --conn-extra '{"region_name": "us-east-1"}'

# Verify connection added
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow connections get aws_default
# Expected: Connection details printed
```

---

### Phase 4 — Set Airflow Variables (CLI)

```powershell
# Set required variables referenced in daily_pipeline.py
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables set account_id $ACCOUNT

docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables set sns_topic_arn "arn:aws:sns:$REGION`:$ACCOUNT`:data-pipeline-alerts"

docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables set data_lake_bucket "handson-data-lake-$ACCOUNT"

docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables set glue_job_name "handson-etl-job"

# Verify
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables list
# Expected: 4 variables listed
```

---

### Phase 5 — Trigger and Monitor DAG (CLI)

```powershell
# Trigger DAG manually
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags trigger daily_data_pipeline
# Expected: Created <DagRun daily_data_pipeline @ ...>

# Watch run status
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-runs --dag-id daily_data_pipeline --limit 3
# Expected: recent runs with state

# Get task states for a specific run
$RUN_ID = docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-runs --dag-id daily_data_pipeline --limit 1 --output json 2>$null |
  ConvertFrom-Json | Select-Object -First 1 -ExpandProperty run_id

docker exec -it airflow-local-airflow-scheduler-1 `
  airflow tasks states-for-dag-run daily_data_pipeline $RUN_ID
# Expected: Each task with its state: success, running, failed, etc.

# View logs for a specific task
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow tasks logs daily_data_pipeline check_source_data $RUN_ID
# Expected: Log output for that task instance
```

---

### Phase 6 — Create S3 Bucket for MWAA (PowerShell + AWS CLI)

```powershell
# Create S3 bucket
aws s3api create-bucket --bucket $BUCKET --region $REGION
# Expected: {"Location": "/handson-mwaa-ACCOUNT"}

# Enable versioning (MWAA requirement)
aws s3api put-bucket-versioning `
  --bucket $BUCKET `
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block `
  --bucket $BUCKET `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Upload DAG file
aws s3 cp "dags\daily_pipeline.py" "s3://$BUCKET/dags/daily_pipeline.py"
# Expected: upload: dags\daily_pipeline.py to s3://handson-mwaa-.../dags/daily_pipeline.py

# Verify upload
aws s3 ls "s3://$BUCKET/dags/"
# Expected: daily_pipeline.py listed
```

---

### Phase 7 — Create IAM Role for MWAA

```powershell
# Trust policy — MWAA needs BOTH principals
@'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": ["airflow.amazonaws.com","airflow-env.amazonaws.com"]
    },
    "Action": "sts:AssumeRole"
  }]
}
'@ | Out-File "$env:TEMP\mwaa-trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\mwaa-trust.json"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME `
  --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"

# Attach MWAA policy
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject*","s3:GetBucket*","s3:List*"],
      "Resource": ["arn:aws:s3:::$BUCKET","arn:aws:s3:::$BUCKET/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents",
                 "logs:GetLogEvents","logs:GetLogRecord","logs:DescribeLogGroups"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["glue:StartJobRun","glue:GetJobRun","glue:GetJob"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["airflow:PublishMetrics"],
      "Resource": "arn:aws:airflow:$REGION`:$ACCOUNT`:environment/$ENV_NAME"
    }
  ]
}
"@ | Out-File "$env:TEMP\mwaa-policy.json" -Encoding utf8

aws iam put-role-policy --role-name $ROLE_NAME `
  --policy-name "mwaa-policy" `
  --policy-document "file://$env:TEMP\mwaa-policy.json"

Write-Host "✅ IAM role ready"
```

---

### Phase 8 — Create MWAA Environment (CLI)

> ⚠️ This costs ~$315+/month. Only proceed when ready for production.

```powershell
# Get your VPC and subnet IDs first
$VPC_ID = aws ec2 describe-vpcs `
  --query "Vpcs[?IsDefault==\`true\`].VpcId" --output text
$SUBNET_IDS = (aws ec2 describe-subnets `
  --filters "Name=vpc-id,Values=$VPC_ID" `
  --query "Subnets[?MapPublicIpOnLaunch==\`false\`].SubnetId" `
  --output text) -split "\t" | Select-Object -First 2

Write-Host "VPC: $VPC_ID | Subnets: $($SUBNET_IDS -join ', ')"

# Create MWAA environment
aws mwaa create-environment `
  --name $ENV_NAME `
  --airflow-version "2.8.1" `
  --dag-s3-path "dags/" `
  --source-bucket-arn "arn:aws:s3:::$BUCKET" `
  --execution-role-arn $ROLE_ARN `
  --network-configuration "SubnetIds=$($SUBNET_IDS[0]),$($SUBNET_IDS[1])" `
  --airflow-configuration-options "core.default_timezone=utc" `
  --environment-class "mw1.small" `
  --max-workers 1 `
  --logging-configuration '{
    "DagProcessingLogs": {"Enabled": true, "LogLevel": "INFO"},
    "SchedulerLogs": {"Enabled": true, "LogLevel": "INFO"},
    "TaskLogs": {"Enabled": true, "LogLevel": "INFO"},
    "WebserverLogs": {"Enabled": true, "LogLevel": "INFO"},
    "WorkerLogs": {"Enabled": true, "LogLevel": "INFO"}
  }'

# Monitor creation (takes 20-30 minutes)
Write-Host "Creating MWAA environment (20-30 min)..."
for ($i=0; $i -lt 60; $i++) {
  $STATUS = aws mwaa get-environment `
    --name $ENV_NAME --query "Environment.Status" --output text
  Write-Host "[$i] Status: $STATUS"
  if ($STATUS -eq "AVAILABLE") { break }
  if ($STATUS -eq "CREATE_FAILED") { Write-Host "❌ Failed!"; break }
  Start-Sleep -Seconds 30
}
```

---

### Phase 9 — Trigger DAG via MWAA CLI Token

```powershell
# Get CLI token and webserver URL
$CLI_TOKEN = aws mwaa create-cli-token `
  --name $ENV_NAME `
  --query "CliToken" --output text

$WEB_URL = aws mwaa get-environment `
  --name $ENV_NAME `
  --query "Environment.WebserverUrl" --output text

Write-Host "Airflow UI: https://$WEB_URL"

# Trigger DAG
$BODY = '{"command":"dags trigger daily_data_pipeline"}'
$RESPONSE = Invoke-RestMethod `
  -Uri "https://$WEB_URL/aws_mwaa/cli" `
  -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN"; "Content-Type"="application/json"} `
  -Body $BODY

# Decode base64 output
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($RESPONSE.stdout))
# Expected: "Created <DagRun daily_data_pipeline @...>"

# List recent DAG runs
$BODY2 = '{"command":"dags list-runs -d daily_data_pipeline --limit 3"}'
$RESPONSE2 = Invoke-RestMethod `
  -Uri "https://$WEB_URL/aws_mwaa/cli" `
  -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN"; "Content-Type"="application/json"} `
  -Body $BODY2

[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($RESPONSE2.stdout))
# Expected: table of recent DAG runs with state
```

---

## 6. Code Deep Dive

### `dags/daily_pipeline.py` — Primary DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
```
- `DAG` — the pipeline container. All tasks live inside a `with DAG(...) as dag:` block.
- `PythonOperator` — runs any Python function as a task.
- `GlueJobOperator` — starts a Glue job by name, polls until SUCCEEDED/FAILED.
  Part of `apache-airflow-providers-amazon` — not in base Airflow.
- `S3KeySensor` — polls S3 for a specific key. Blocks downstream tasks until found.
- `SnsPublishOperator` — publishes a message to an SNS topic.

---

```python
default_args = {
    "owner":            "data-engineering",
    "depends_on_past":  False,
    "start_date":       datetime(2024, 1, 1),
    "email_on_failure": True,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}
```
- `depends_on_past = False` — each daily run is independent.
  If True: today's run waits for yesterday's run to succeed. Almost never what you want.
- `start_date = datetime(2024, 1, 1)` — the first date the DAG can run.
  With `catchup=False`, this only affects the very first scheduling.
- `email_on_failure = True` — sends email (if SMTP configured). We use SNS instead.
- `retries = 2` — if a task fails, Airflow retries it 2 times automatically.
  After 3 total attempts (1 + 2 retries), the task is marked FAILED.
- `retry_delay = timedelta(minutes=5)` — wait 5 min between retries.
  Good for transient AWS API errors (rate limits, timeouts).

---

```python
with DAG(
    dag_id="daily_data_pipeline",
    schedule_interval="0 2 * * *",
    catchup=False,
    tags=["data-engineering", "production"],
) as dag:
```
- `dag_id="daily_data_pipeline"` — unique identifier. Shown in UI. Used in CLI commands.
  Cannot have spaces or special characters (except underscore/hyphen).
- `schedule_interval="0 2 * * *"` — cron syntax: minute=0, hour=2, every day.
  Runs at 02:00 UTC. Use `@daily`, `@hourly` as shortcuts (not recommended — ambiguous).
- `catchup=False` — **critical setting**.
  With `catchup=True`: if DAG is first enabled on Jan 15 with start_date Jan 1,
  Airflow creates 15 backfill runs immediately. Usually causes chaos.
  With `catchup=False`: only runs from now forward.

---

```python
check_source_data = S3KeySensor(
    task_id="check_source_data",
    bucket_name="handson-data-lake-{{ var.value.account_id }}",
    bucket_key="raw/orders/year={{ ds_nodash[:4] }}/month={{ ds_nodash[4:6] }}/",
    wildcard_match=True,
    timeout=3600,
    poke_interval=300,
    aws_conn_id="aws_default",
)
```
- `bucket_key` — the S3 key to wait for. Uses Jinja templating:
  `{{ ds_nodash }}` = execution date as `20240115`
  `{{ ds_nodash[:4] }}` = `2024`, `{{ ds_nodash[4:6] }}` = `01`
- `wildcard_match=True` — any key matching the prefix pattern triggers success.
  Without wildcard: needs exact key match.
- `timeout=3600` — if file doesn't arrive in 1 hour, task FAILS.
- `poke_interval=300` — checks S3 every 5 minutes.
- `mode="reschedule"` (in orders_dag.py) — releases the worker slot between checks.
  Without reschedule: worker slot held while waiting = wastes resources = expensive on MWAA.

---

```python
run_glue_etl = GlueJobOperator(
    task_id="run_glue_etl",
    job_name="handson-etl-job",
    script_args={
        "--source_bucket": "handson-data-lake-{{ var.value.account_id }}",
        "--execution_date": "{{ ds }}",
    },
    aws_conn_id="aws_default",
    region_name="us-east-1",
)
```
- `job_name="handson-etl-job"` — must match the exact Glue job name in your AWS account.
- `script_args` — key-value pairs passed to the Glue job as `--key value` arguments.
  `{{ ds }}` = execution date as `2024-01-15` (ISO format).
  `{{ var.value.account_id }}` = Airflow Variable named `account_id`.
- `GlueJobOperator` internally calls `start_job_run` then polls `get_job_run` until
  the status is SUCCEEDED, FAILED, or STOPPED.
  No need for a separate `GlueJobSensor` — the operator waits automatically.

---

```python
notify_success = SnsPublishOperator(
    task_id="notify_success",
    target_arn="{{ var.value.sns_topic_arn }}",
    message="✅ Daily pipeline completed successfully for {{ ds }}",
    aws_conn_id="aws_default",
    trigger_rule="all_success",
)

notify_failure = SnsPublishOperator(
    task_id="notify_failure",
    target_arn="{{ var.value.sns_topic_arn }}",
    message="❌ Daily pipeline FAILED for {{ ds }}. Check Airflow logs.",
    aws_conn_id="aws_default",
    trigger_rule="one_failed",
)
```
- `trigger_rule="all_success"` — runs only if ALL upstream tasks succeeded. Default rule.
- `trigger_rule="one_failed"` — runs if ANY upstream task failed.
  Both notifications are in the dependency graph, but only one fires per run.
- `target_arn="{{ var.value.sns_topic_arn }}"` — Jinja pulls the value from
  Airflow Variable `sns_topic_arn` at runtime.

---

```python
check_source_data >> run_glue_etl >> run_dbt_task >> validate_task
validate_task >> [notify_success, notify_failure]
```
- `>>` is the **bitshift operator** Airflow overloads as "set downstream".
  `A >> B` means: B depends on A. A must finish before B starts.
- `validate_task >> [notify_success, notify_failure]` — validate_task has TWO
  downstream tasks. Both are triggered from it, but only one fires based on trigger_rule.
- Equivalent: `validate_task.set_downstream([notify_success, notify_failure])`

---

### `code/orders_dag.py` — Advanced Reference Features

**Failure Callback Pattern:**
```python
def notify_failure_fn(context) -> None:
    task_instance = context.get("task_instance")
    exception = context.get("exception")
    # Sends SNS with the specific task name and error message

with DAG(
    on_failure_callback=notify_failure_fn,  # fires on ANY task failure
) as dag:
```
- `on_failure_callback` is set on the DAG (not individual tasks).
  One function handles all failures — no need to add trigger_rule="one_failed" tasks.
- Difference from `daily_pipeline.py`: orders_dag uses callback (fires immediately on failure)
  vs. daily_pipeline uses SnsPublishOperator (appears in DAG graph visually).

**XCom Pattern (validate_data_quality_fn):**
```python
# Push in task A:
context["task_instance"].xcom_push(key="processed_file_count", value=len(files))

# Pull in task B (hypothetically):
count = context["task_instance"].xcom_pull(task_ids="validate_data_quality", key="processed_file_count")
```
- XCom is stored in Airflow's PostgreSQL metadata database.
- Visible in UI: Task → XCom tab.
- Size limit: 48 KB (default). Not for DataFrames — use S3 for large data.

**Airflow Variable Pattern:**
```python
DATA_LAKE_BUCKET = Variable.get("data_lake_bucket", default_var="my-data-lake-bucket")
```
- `Variable.get()` called at DAG parse time (not task run time).
- `default_var` prevents DAG import errors if variable not set.
- Set via CLI: `airflow variables set data_lake_bucket my-bucket`
- Set via UI: Admin → Variables → +

### Common Mistakes and Fixes

| Mistake | Error / Symptom | Fix |
|---------|----------------|-----|
| `catchup=True` with old start_date | 100s of backfill runs created | Set `catchup=False` |
| No `mode="reschedule"` on sensor | Workers blocked while waiting | Add `mode="reschedule"` |
| Wrong `dag_id` in trigger CLI | "DAG not found" | Check exact `dag_id` in Python file |
| Hardcoded bucket name in DAG | Works locally, breaks in MWAA | Use `Variable.get()` |
| `depends_on_past=True` | New day's run waits forever | Set `depends_on_past=False` |
| No `provide_context=True` | Python callable gets no `context` | Add `provide_context=True` |
| `Variable.get()` without default | DAG parse error if variable missing | Add `default_var=` |
| `>>` operator only sets order | Parallel tasks with same priority | Use `[taskA, taskB] >> taskC` |

---

## 7. Verification & Validation

### 7.1 Local Docker Verification

```powershell
# Verify all containers running
docker compose -f C:\airflow-local\docker-compose.yaml ps
# Expected: 5 containers all Up (healthy)

# Check DAG is loaded
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list
# Expected: daily_data_pipeline listed, is_paused=False

# Check for import errors
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-import-errors
# Expected: empty output (no errors)

# Verify variables set
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow variables list
# Expected: account_id, sns_topic_arn, data_lake_bucket, glue_job_name

# Verify connection
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow connections get aws_default
# Expected: Connection details printed
```

### 7.2 MWAA Verification (PowerShell)

```powershell
# Check MWAA environment status
aws mwaa get-environment --name $ENV_NAME `
  --query "Environment.{Status:Status,Version:AirflowVersion,URL:WebserverUrl}"
# Expected: Status=AVAILABLE, Version=2.8.1

# List DAGs via MWAA CLI token
$CLI_TOKEN = aws mwaa create-cli-token `
  --name $ENV_NAME --query "CliToken" --output text
$WEB_URL = aws mwaa get-environment `
  --name $ENV_NAME --query "Environment.WebserverUrl" --output text

$R = Invoke-RestMethod `
  -Uri "https://$WEB_URL/aws_mwaa/cli" -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN";"Content-Type"="application/json"} `
  -Body '{"command":"dags list"}'
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($R.stdout))
# Expected: daily_data_pipeline listed, is_paused=False

# Verify DAG files in S3
aws s3 ls "s3://$BUCKET/dags/"
# Expected: daily_pipeline.py listed

# Check MWAA environment logs
aws logs describe-log-groups `
  --log-group-name-prefix "airflow-$ENV_NAME" `
  --query "logGroups[*].logGroupName"
# Expected: scheduler, task, webserver log groups
```

### 7.3 End-to-End Test

```powershell
Write-Host "=== AIRFLOW END-TO-END TEST ===" -ForegroundColor Cyan

# Trigger a run
$R = Invoke-RestMethod `
  -Uri "https://$WEB_URL/aws_mwaa/cli" -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN";"Content-Type"="application/json"} `
  -Body '{"command":"dags trigger daily_data_pipeline"}'
$OUT = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($R.stdout))
Write-Host "✅ Triggered: $OUT"

# Wait 60s then check runs
Start-Sleep -Seconds 60
$R2 = Invoke-RestMethod `
  -Uri "https://$WEB_URL/aws_mwaa/cli" -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN";"Content-Type"="application/json"} `
  -Body '{"command":"dags list-runs -d daily_data_pipeline --limit 1"}'
$OUT2 = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($R2.stdout))
Write-Host "✅ Run status:`n$OUT2"

Write-Host "=== TEST COMPLETE ===" -ForegroundColor Green
```

### 7.4 Verification Checklist

- [ ] Docker containers all healthy (local) OR MWAA Status=AVAILABLE (cloud)
- [ ] `daily_data_pipeline` visible in Airflow UI DAGs list
- [ ] DAG has no import errors (no red banner)
- [ ] DAG graph shows 6 tasks in correct order
- [ ] `aws_default` connection configured
- [ ] Airflow Variables: account_id, sns_topic_arn, data_lake_bucket set
- [ ] DAG can be triggered manually without error
- [ ] Task logs accessible from UI
- [ ] No DAG import errors in scheduler logs

---

## 8. Observations & Learning Notes

### 8.1 What to Observe During Execution

**When DAG is triggered:**
- The Scheduler immediately queues the first task (`check_source_data`)
- Status changes: Scheduled → Queued → Running
- The S3Sensor starts poking S3 every 5 minutes (in local Docker, it will fail or skip
  since there's no real S3 data — that's expected for local testing)

**When a task is Running:**
- One worker slot is consumed (visible in UI: Browse → Task Instances)
- Logs stream in real-time in the task log view
- If `mode="reschedule"`, sensor releases the worker slot between pokes

**When a task Fails:**
- Status goes Running → Failed
- Orange retry badge appears
- After `retry_delay` (5 min), state goes back to Queued → Running
- After all retries exhausted: task state = Failed (red)
- `on_failure_callback` fires immediately on the first failure

### 8.2 Airflow Internal Behavior

```
Scheduler:
  - Reads all DAG files every 30s (parsing)
  - Checks which tasks are ready to run (dependencies met)
  - Creates TaskInstance records in the metadata DB
  - Sends task to executor (Celery or LocalExecutor)

Executor:
  - Pulls tasks from the queue (Redis for Celery)
  - Spawns a subprocess to run the task operator
  - Reports task result back to Scheduler

Worker (Celery mode, used in Docker Compose):
  - Separate process that executes tasks
  - Can be scaled horizontally (multiple workers)
  - In MWAA: workers auto-scale based on queue depth
```

### 8.3 MWAA vs Self-Hosted vs Local

| Option | Cost/Month | Setup Time | Best For |
|--------|-----------|-----------|---------|
| Local Docker | $0 | 5 min | Learning, development |
| Self-hosted (ECS) | ~$30 | 2–4 hours | Small team, cost-sensitive |
| MWAA mw1.small | ~$670 | 30 min | Large team, enterprise |

### 8.4 Billing Observations

- **MWAA charges start** the moment environment is Created (not just when DAGs run)
- **No free tier** for MWAA
- `mw1.small` with 1 worker = ~$22/day regardless of whether any DAGs run
- **Local Docker = $0** — identical Airflow API, best for learning
- Delete MWAA environment immediately after testing: saves $22/day

---

## 9. Screenshots Guidance

### Before Implementation
| # | What to Capture | When |
|---|----------------|------|
| SS-01 | Docker Desktop showing engine running | Before Step 1 |
| SS-02 | Empty Airflow DAGs list (before DAG upload) | Step 1.6 |

### During Setup
| # | What to Capture | When |
|---|----------------|------|
| SS-03 | Airflow login page at localhost:8080 | Step 1.6 |
| SS-04 | Admin → Connections list | Step 3.1 |
| SS-05 | AWS connection form filled in | Step 3.2 |
| SS-06 | Admin → Variables with 4 variables set | Step 3.3 |
| SS-07 | MWAA Create Environment form | Step 5.4 (if using MWAA) |

### After Deployment
| # | What to Capture | When |
|---|----------------|------|
| SS-08 | DAGs list showing `daily_data_pipeline` loaded | Step 2.2 |
| SS-09 | DAG Graph view showing all 6 tasks connected | Step 2.3 |
| SS-10 | MWAA environment Status = Available | Step 5.4 (MWAA) |
| SS-11 | S3 bucket dags/ folder with daily_pipeline.py | Step 5.2 |

### Execution
| # | What to Capture | When |
|---|----------------|------|
| SS-12 | Trigger DAG button + confirmation | Step 4.2 |
| SS-13 | DAG graph with colored task states (running) | Step 4.3 |
| SS-14 | Task log viewer for check_source_data | Step 4.4 |
| SS-15 | Completed run — all tasks green | After successful run |
| SS-16 | Failed task with retry count visible | If a task fails |

**Total: 16 screenshots for complete documentation**

---

## 10. Cleanup Steps

### 10.1 Local Docker Cleanup

```powershell
# Stop all containers
docker compose -f C:\airflow-local\docker-compose.yaml down

# Remove volumes (deletes all DAG run history, logs, metadata)
docker compose -f C:\airflow-local\docker-compose.yaml down --volumes

# Remove images (optional — frees ~1 GB disk space)
docker compose -f C:\airflow-local\docker-compose.yaml down --rmi all

Write-Host "✅ Local Airflow removed"
```

### 10.2 AWS Console Cleanup (MWAA)

1. **Delete MWAA Environment** (stops all billing):
   - MWAA → Environments → `handson-airflow` → **Delete** → Confirm
   - Takes ~5 minutes

2. **Delete S3 Bucket**:
   - S3 → `handson-mwaa-ACCOUNT` → **Empty** bucket first → **Delete bucket**

3. **Delete IAM Role**:
   - IAM → Roles → `handson-mwaa-role` → **Delete**

### 10.3 AWS CLI Cleanup (PowerShell)

```powershell
# Step 1 — Delete MWAA environment
aws mwaa delete-environment --name $ENV_NAME
Write-Host "Deleting MWAA environment (5 min)..."
for ($i=0; $i -lt 20; $i++) {
  $STATUS = aws mwaa get-environment --name $ENV_NAME `
    --query "Environment.Status" --output text 2>&1
  if ($STATUS -match "NoSuchEntity|does not exist") { break }
  Write-Host "Status: $STATUS"
  Start-Sleep -Seconds 30
}
Write-Host "✅ MWAA deleted"

# Step 2 — Empty and delete S3 bucket
aws s3 rm "s3://$BUCKET" --recursive
aws s3api delete-bucket --bucket $BUCKET
Write-Host "✅ S3 bucket deleted"

# Step 3 — Delete IAM role
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "mwaa-policy"
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ IAM role deleted"
```

### 10.4 Verify Cleanup

```powershell
# Confirm MWAA deleted
aws mwaa list-environments --query "Environments[?contains(@,'handson')]"
# Expected: []

# Confirm S3 bucket deleted
aws s3api head-bucket --bucket $BUCKET 2>&1
# Expected: error (bucket not found)

Write-Host "✅ All resources cleaned up"
```

### 10.5 Cost Verification

```powershell
aws ce get-cost-and-usage `
  --time-period "Start=$(Get-Date -Format 'yyyy-MM-01'),End=$(Get-Date -Format 'yyyy-MM-dd')" `
  --granularity DAILY `
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AmazonMWAA"]}}' `
  --metrics UnblendedCost `
  --query "ResultsByTime[-1].Total.UnblendedCost.Amount"
# After deletion: no new charges
```

---

## Quick Reference Card

```
LOCAL AIRFLOW (FREE — START HERE):
  mkdir C:\airflow-local && cd C:\airflow-local
  Invoke-WebRequest -Uri ".../docker-compose.yaml" -OutFile docker-compose.yaml
  "AIRFLOW_UID=50000" | Out-File .env
  docker compose up airflow-init
  docker compose up -d
  Open: http://localhost:8080  (admin/airflow)

UPLOAD DAG:
  Copy-Item dags\daily_pipeline.py C:\airflow-local\dags\

TRIGGER:
  docker exec -it airflow-local-airflow-scheduler-1 airflow dags trigger daily_data_pipeline

MWAA TRIGGER (production):
  $TOKEN = aws mwaa create-cli-token --name handson-airflow --query "CliToken" -o text
  $URL   = aws mwaa get-environment --name handson-airflow --query "Environment.WebserverUrl" -o text
  Invoke-RestMethod -Uri "https://$URL/aws_mwaa/cli" -Method POST ...

CLEANUP LOCAL:
  docker compose down --volumes

CLEANUP MWAA ($22/day savings):
  aws mwaa delete-environment --name handson-airflow
  aws s3 rm s3://BUCKET --recursive
  aws s3api delete-bucket --bucket BUCKET
  aws iam delete-role-policy --role-name handson-mwaa-role --policy-name mwaa-policy
  aws iam delete-role --role-name handson-mwaa-role
```

---
*Guide version: 1.0 | Project path: D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow*

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
