# Project 9.5 — Airflow Data Orchestration
# Console UI Steps (Improved Template Format)
# Primary DAG: daily_data_pipeline | MWAA: handson-airflow

---

> **Recommendation:** Complete STEPS 1–4 (Local Docker) first at zero cost.
> Only proceed to STEP 5 (MWAA) when ready for production.

---

## PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Docker Desktop installed and running
- ✅ AWS CLI configured (`aws sts get-caller-identity` works)
- ✅ Port 8080 not in use
- ✅ `dags/daily_pipeline.py` exists in the project folder

**Step 0.1: Verify Docker Running**
1. Look at system tray → Docker Desktop icon should be visible
2. Run: `docker --version` in PowerShell
3. **Expected View:** `Docker version 24.x.x`
4. **If Not Running:** Open Docker Desktop application

**📸 Screenshot P0:** Docker Desktop showing green status

---

### STEP 1 — Run Airflow Locally (Local Docker)

**Prerequisites Check:**
- ✅ Docker Desktop running with 4 GB RAM allocated
- ✅ No other service on port 8080

**Step 1.1: Navigate and Verify**
1. Open PowerShell
2. Create local directory: `mkdir C:\airflow-local`

**Step 1.2: Make Selections — Airflow Version**

**Decision Point 1:** Airflow version
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **2.8.1** | Stable, matches MWAA | ✅ Use this |
| 2.9.x+ | Latest features | ❌ May differ from MWAA |

Use: `https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml`

**Step 1.3: Configure Details**
```powershell
Set-Location C:\airflow-local
New-Item -ItemType Directory -Path dags, logs, plugins -Force
Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml" -OutFile docker-compose.yaml
"AIRFLOW_UID=50000" | Out-File .env -Encoding utf8
docker compose up airflow-init
docker compose up -d
```

**Step 1.4: Validate Result**
**Expected Outcome:** `docker compose ps` shows 5 containers Up (healthy)
Open `http://localhost:8080` → login page appears

**Troubleshooting:**
- Port 8080 busy: `netstat -ano | findstr :8080` → kill that process
- Docker out of memory: Increase to 4 GB in Docker Desktop → Settings → Resources

**📸 Screenshot 1a:** `docker compose ps` showing 5 healthy containers
**📸 Screenshot 1b:** Airflow login page at http://localhost:8080

---

### STEP 2 — Upload DAG

**Prerequisites Check:**
- ✅ Airflow running at localhost:8080
- ✅ `dags/daily_pipeline.py` exists in project

**Step 2.1: Navigate and Verify**
1. Open http://localhost:8080 → Login: airflow/airflow
2. **Expected View:** DAGs list page (empty initially)

**Step 2.2: Copy DAG File**
```powershell
Copy-Item "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow\dags\daily_pipeline.py" "C:\airflow-local\dags\"
```

**Step 2.3: Validate Result**
1. Wait 30–60 seconds, refresh Airflow UI
2. **Expected Outcome:** `daily_data_pipeline` appears in DAGs list
3. Click on DAG name → click **Graph** tab

**Expected DAG Graph:**
```
check_source_data → run_glue_etl → run_dbt_transformations → validate_data_quality
                                                                    ↓               ↓
                                                           notify_success   notify_failure
```

**Troubleshooting:**
- Red banner "Broken DAG": Click banner → see Python error → fix DAG file
- DAG not appearing after 60s: Check `docker exec -it airflow-local-airflow-scheduler-1 airflow dags list-import-errors`

**📸 Screenshot 2a:** DAGs list showing `daily_data_pipeline` (no red banner)
**📸 Screenshot 2b:** DAG Graph view with 6 tasks connected

---

### STEP 3 — Configure Connections and Variables

**Prerequisites Check:**
- ✅ Airflow UI accessible at localhost:8080

**Step 3.1: Navigate to Connections**
1. Airflow UI → top menu → **Admin** → **Connections**
2. **Expected View:** Connections list
3. Click **+** (Add connection)

**📸 Screenshot 3a:** Admin → Connections list

**Step 3.2: Make Selections — Connection Type**

**Decision Point 1:** Connection type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Amazon Web Services** | S3, Glue, SNS providers | ✅ Required |
| Generic | Custom conn string | ❌ AWS providers won't work |

**Step 3.3: Configure AWS Connection**

| Field | Value |
|-------|-------|
| Connection Id | `aws_default` |
| Connection Type | **Amazon Web Services** |
| AWS Access Key ID | your-access-key-id |
| AWS Secret Access Key | your-secret-access-key |
| Extra | `{"region_name": "us-east-1"}` |

Click **Save**

**Step 3.4: Set Airflow Variables**
1. Admin → **Variables** → **+**
2. Add each:

| Key | Value |
|-----|-------|
| `account_id` | `YOUR_12_DIGIT_ACCOUNT_ID` |
| `sns_topic_arn` | `arn:aws:sns:us-east-1:ACCOUNT:data-pipeline-alerts` |
| `data_lake_bucket` | `handson-data-lake-YOUR_ACCOUNT_ID` |
| `glue_job_name` | `handson-etl-job` |

**Step 3.5: Validate Result**
**Expected Outcome:** Admin → Variables shows 4 variables. Admin → Connections shows aws_default.

**📸 Screenshot 3b:** Variables list with 4 entries
**📸 Screenshot 3c:** Connections list showing aws_default

---

### STEP 4 — Trigger and Monitor DAG

**Prerequisites Check:**
- ✅ DAG loaded, no import errors
- ✅ aws_default connection configured
- ✅ Variables set

**Step 4.1: Enable DAG**
1. DAGs list → find `daily_data_pipeline`
2. **If toggle is grey:** Click it to enable (turn blue)

**Step 4.2: Trigger Manually**
1. Click **▶** (Trigger DAG) button on the right side of the row
2. Click **Trigger** in the popup
3. **Expected View:** Run appears in "Last Run" column

**📸 Screenshot 4a:** Trigger button and confirmation popup

**Step 4.3: Monitor Execution**
1. Click on the run date → opens the Run detail view
2. Click **Graph** tab to see live task status

**Decision Point 1:** Task state interpretation
| Color | State | Meaning |
|-------|-------|---------|
| 🟡 Yellow | Running | Executing now |
| 🟢 Green | Success | Completed OK |
| 🔴 Red | Failed | Failed — check logs |
| 🟠 Orange | Up for retry | Failed, waiting to retry |
| ⚪ Grey | None/Queued | Not started |

**📸 Screenshot 4b:** DAG graph during run with colored task states

**Step 4.4: View Task Logs**
1. Click any task box → **Log** button
2. **Expected View:** Log lines with timestamps

**📸 Screenshot 4c:** Task log viewer

**Step 4.5: Validate Result**
**Expected Outcome:** All tasks show green (Success) on a completed run.
Note: `check_source_data` will fail/skip in local Docker since S3 data may not exist.

---

### STEP 5 — Deploy to Amazon MWAA (Production)

> ⚠️ Costs ~$670/month. Skip for learning — complete Steps 1–4 locally first.

**Prerequisites Check:**
- ✅ Required permissions: `mwaa:CreateEnvironment`, `s3:CreateBucket`, `iam:CreateRole`
- ✅ VPC with 2+ private subnets (NAT gateway required)
- ✅ Region: us-east-1

**Step 5.1: Create S3 Bucket for DAGs**
1. Search → **S3** → **Create bucket**

| Field | Value |
|-------|-------|
| Bucket name | `handson-mwaa-YOUR_ACCOUNT_ID` |
| Region | us-east-1 |
| Versioning | ✅ Enable (required by MWAA) |
| Public access | ✅ Block all |

2. Create `dags/` folder → Upload `dags/daily_pipeline.py`

**📸 Screenshot 5a:** S3 bucket with dags/daily_pipeline.py

**Step 5.2: Create IAM Role**
1. IAM → Roles → **Create role**
2. **Custom trust policy** (BOTH principals required):

```json
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
```

3. Role name: `handson-mwaa-role`
4. Add inline policy with S3, Glue, SNS, CloudWatch Logs permissions

**Step 5.3: Create MWAA Environment**
1. Search → **MWAA** → **Create environment**

| Field | Value |
|-------|-------|
| Environment name | `handson-airflow` |
| Airflow version | `2.8.1` |
| DAG S3 path | `s3://handson-mwaa-ACCOUNT/dags/` |
| Execution role | `handson-mwaa-role` |
| VPC | your VPC |
| Subnets | 2 private subnets |
| Environment class | `mw1.small` |
| Max workers | `1` |
| Logs | Enable all (INFO level) |

2. Click **Create environment** → Wait 20–30 minutes

**Step 5.4: Validate Result**
**Expected Outcome:** Status = **Available**. Click **Open Airflow UI** to access.

**Troubleshooting:**
- "No subnets": Need private subnets (with NAT gateway, not public subnets)
- IAM role error: Must have BOTH `airflow.amazonaws.com` AND `airflow-env.amazonaws.com`
- Creation fails: Check CloudFormation events for detailed error

**📸 Screenshot 5b:** MWAA environment Status = Available
**📸 Screenshot 5c:** MWAA Airflow UI with daily_data_pipeline listed

---

## Console UI Summary

| Step | Action | Resource |
|------|--------|---------|
| Step 1 | Start Docker Compose | Local Airflow at :8080 |
| Step 2 | Copy DAG file | daily_data_pipeline loaded |
| Step 3 | Admin → Connections + Variables | aws_default, 4 variables |
| Step 4 | Trigger + monitor | Run visible in graph view |
| Step 5 | (MWAA) Create S3 + IAM + Environment | handson-airflow Available |

## Screenshot Summary

| # | Description | Step |
|---|-------------|------|
| P0 | Docker Desktop running | Phase 0 |
| 1a | `docker compose ps` healthy | Step 1.4 |
| 1b | Airflow login page | Step 1.4 |
| 2a | DAGs list with daily_data_pipeline | Step 2.3 |
| 2b | DAG Graph — 6 tasks | Step 2.3 |
| 3a | Admin → Connections list | Step 3.1 |
| 3b | Variables list — 4 entries | Step 3.4 |
| 3c | aws_default connection | Step 3.2 |
| 4a | Trigger button + popup | Step 4.2 |
| 4b | DAG graph with colored tasks | Step 4.3 |
| 4c | Task log viewer | Step 4.4 |
| 5a | S3 dags/daily_pipeline.py | Step 5.1 (MWAA) |
| 5b | MWAA Status = Available | Step 5.3 (MWAA) |
| 5c | MWAA Airflow UI | Step 5.4 (MWAA) |

**Total: 14 screenshots for complete documentation**
