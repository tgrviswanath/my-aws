# Project 9.2 — AWS Glue ETL Pipeline
# PART 3: CLI Method, Terraform IaC & Code Deep Dive

---

## 5B. AWS CLI IMPLEMENTATION

> Run all commands from PowerShell (Windows) in the project directory.
> Replace `YOUR_BUCKET` with your actual bucket name from Project 9.1.

### Setup — Export Variables First

```powershell
# Get outputs from Project 9.1 (run this in the project_9.1 terraform folder)
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.1_data_lake\terraform

$BUCKET   = terraform output -raw data_lake_bucket
$ROLE_ARN = terraform output -raw glue_role_arn
$DATABASE = terraform output -raw glue_database

Write-Host "Bucket:   $BUCKET"
Write-Host "Role ARN: $ROLE_ARN"
Write-Host "Database: $DATABASE"

# Then go back to project 9.2
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl
```

---

### CLI Step 1 — Upload ETL Script to S3

```bash
# Upload the PySpark script to S3
aws s3 cp src/etl_job.py s3://$BUCKET/scripts/etl_job.py

# Expected output:
# upload: src/etl_job.py to s3://handson-data-lake-123456789012/scripts/etl_job.py

# Verify the upload
aws s3 ls s3://$BUCKET/scripts/
# Expected output:
# 2024-01-15 10:30:00       3847 etl_job.py
```

**Command explanation:**
- `aws s3 cp` — copy a file to/from S3
- `src/etl_job.py` — local source file (relative path)
- `s3://$BUCKET/scripts/etl_job.py` — S3 destination path (bucket + key)

---

### CLI Step 2 — Create the Glue Job

```bash
aws glue create-job \
  --name "handson-etl-job" \
  --role "$ROLE_ARN" \
  --command '{
    "Name": "glueetl",
    "ScriptLocation": "s3://'"$BUCKET"'/scripts/etl_job.py",
    "PythonVersion": "3"
  }' \
  --default-arguments '{
    "--job-language":                       "python",
    "--job-bookmark-option":                "job-bookmark-enable",
    "--enable-metrics":                     "true",
    "--enable-continuous-cloudwatch-log":   "true",
    "--source_bucket":                      "'"$BUCKET"'",
    "--target_bucket":                      "'"$BUCKET"'",
    "--database_name":                      "'"$DATABASE"'",
    "--TempDir":                            "s3://'"$BUCKET"'/temp/"
  }' \
  --glue-version "4.0" \
  --number-of-workers 2 \
  --worker-type "G.1X" \
  --timeout 60

# Expected output:
# {
#     "Name": "handson-etl-job"
# }
```

**Parameter-by-parameter explanation:**
```
--name                  Job display name in Glue console
--role                  IAM role ARN Glue assumes during execution
--command.Name          "glueetl" = Spark ETL job type (not Python Shell)
--command.ScriptLocation S3 path to your PySpark script
--command.PythonVersion "3" = Python 3.x
--default-arguments     Key-value pairs passed to script as sys.argv
  --job-bookmark-option "job-bookmark-enable" = track processed files
  --enable-metrics      Publish Spark metrics to CloudWatch
  --enable-continuous-cloudwatch-log Stream logs in real-time (not end-of-job)
  --source_bucket       Custom arg read by getResolvedOptions() in script
  --TempDir             Required: Glue uses this for shuffle/intermediate data
--glue-version          "4.0" = Spark 3.3.0, Python 3.10
--number-of-workers     2 = minimum for Spark distributed mode
--worker-type           G.1X = 4 vCPU, 16GB RAM per worker
--timeout               60 = kill job if it runs > 60 minutes
```

**Verify job was created:**
```bash
aws glue get-job --job-name "handson-etl-job" \
  --query "Job.{Name:Name,GlueVersion:GlueVersion,Workers:NumberOfWorkers,WorkerType:WorkerType}"

# Expected output:
# {
#     "Name": "handson-etl-job",
#     "GlueVersion": "4.0",
#     "Workers": 2,
#     "WorkerType": "G.1X"
# }
```

---

### CLI Step 3 — Start a Job Run

```bash
# Start the job
RUN_ID=$(aws glue start-job-run \
  --job-name "handson-etl-job" \
  --query "JobRunId" \
  --output text)

echo "Job Run ID: $RUN_ID"
# Expected: jr_abc123def456...
```

---

### CLI Step 4 — Monitor Job Status

```bash
# Check status once
aws glue get-job-run \
  --job-name "handson-etl-job" \
  --run-id "$RUN_ID" \
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime,Error:ErrorMessage}"

# Expected output during run:
# {
#     "State": "RUNNING",
#     "Duration": 45,
#     "Error": null
# }

# Expected output on completion:
# {
#     "State": "SUCCEEDED",
#     "Duration": 387,
#     "Error": null
# }

# Poll every 30 seconds until done (PowerShell)
do {
  $STATUS = aws glue get-job-run `
    --job-name "handson-etl-job" `
    --run-id "$RUN_ID" `
    --query "JobRun.JobRunState" `
    --output text
  Write-Host "$(Get-Date -Format 'HH:mm:ss') Status: $STATUS"
  Start-Sleep 30
} while ($STATUS -eq "RUNNING" -or $STATUS -eq "STARTING")

Write-Host "Final status: $STATUS"
```

---

### CLI Step 5 — Verify S3 Output

```bash
# List processed Parquet files
aws s3 ls s3://$BUCKET/processed/orders/ --recursive

# Expected output:
# 2024-01-15 10:45:00      45312 processed/orders/year=2024/month=01/part-00000.parquet
# 2024-01-15 10:45:00      42156 processed/orders/year=2024/month=02/part-00000.parquet

# Count total files
aws s3 ls s3://$BUCKET/processed/orders/ --recursive | Measure-Object -Line
# Expected: at least 1 line (1+ parquet files)
```

---

### CLI Step 6 — Query with Athena

```bash
# Run Athena query on processed data
$QUERY_ID = aws athena start-query-execution `
  --query-string "SELECT product, COUNT(*) as orders, SUM(amount) as revenue FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 5" `
  --query-execution-context Database=$DATABASE `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" `
  --output text

# Wait for completion
aws athena wait query-execution-complete --query-execution-id $QUERY_ID

# Get results
aws athena get-query-results `
  --query-execution-id $QUERY_ID `
  --query "ResultSet.Rows[*].Data[*].VarCharValue" `
  --output table

# Expected output:
# -----------------------------------------------
# |          GetQueryResults                     |
# +----------+-------+---------------------------+
# |  WIDGET  | 150   | 15823.50                  |
# |  GADGET  | 142   | 14219.00                  |
# +----------+-------+---------------------------+
```

---

### CLI Step 7 — Create Glue Trigger

```bash
aws glue create-trigger \
  --name "handson-etl-daily" \
  --type "SCHEDULED" \
  --schedule "cron(0 2 * * ? *)" \
  --actions '[{"JobName": "handson-etl-job"}]' \
  --no-start-on-creation

# Expected output:
# {
#     "Name": "handson-etl-daily"
# }

# Verify trigger
aws glue get-trigger --name "handson-etl-daily" \
  --query "Trigger.{Name:Name,Type:Type,Schedule:Schedule,State:State}"

# Expected output:
# {
#     "Name": "handson-etl-daily",
#     "Type": "SCHEDULED",
#     "Schedule": "cron(0 2 * * ? *)",
#     "State": "CREATED"
# }
```

> `--no-start-on-creation` keeps trigger in CREATED (not ACTIVATED) state.
> This prevents it from firing automatically and incurring unexpected charges.
> To activate: `aws glue start-trigger --name handson-etl-daily`
> To deactivate: `aws glue stop-trigger --name handson-etl-daily`

---

## 5C. TERRAFORM IMPLEMENTATION

### Complete Terraform Code (with Annotations)

The existing `terraform/main.tf` is production-ready. Here it is with full annotations:

```hcl
# terraform/main.tf

terraform {
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
    # ~> 5.0 means "5.x but not 6.0" — allows patch/minor upgrades
  }
}

provider "aws" { region = var.region }
# Configures the AWS provider to use us-east-1

# ─── Variables ────────────────────────────────────────────────────────────────

variable "region"           { default = "us-east-1" }
variable "project"          { default = "handson" }
variable "data_lake_bucket" { description = "Data lake S3 bucket name" }
variable "glue_role_arn"    { description = "Glue IAM role ARN from project 9.1" }
variable "database_name"    { description = "Glue database name from project 9.1" }
# These three have no default — MUST be passed via -var or terraform.tfvars

locals {
  common_tags = {
    Project   = var.project
    Stage     = "stage-09"
    ManagedBy = "terraform"
  }
  # Reusable tag map — applied to all resources for cost allocation
}

# ─── Upload ETL Script to S3 ──────────────────────────────────────────────────

resource "aws_s3_object" "etl_script" {
  bucket = var.data_lake_bucket
  key    = "scripts/etl_job.py"             # S3 object key (path inside bucket)
  source = "${path.module}/../src/etl_job.py" # Local file path relative to main.tf
  etag   = filemd5("${path.module}/../src/etl_job.py")
  # etag = MD5 hash of file content
  # If etl_job.py changes locally → etag changes → Terraform re-uploads
  # This ensures S3 always has the latest version of the script
}

# ─── Glue ETL Job ─────────────────────────────────────────────────────────────

resource "aws_glue_job" "etl" {
  name     = "${var.project}-etl-job"   # "handson-etl-job"
  role_arn = var.glue_role_arn          # IAM role with S3 + Glue permissions

  command {
    name            = "glueetl"         # Job type: Spark ETL (not Python Shell)
    script_location = "s3://${var.data_lake_bucket}/scripts/etl_job.py"
    python_version  = "3"               # Python 3.x
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--job-bookmark-option"             = "job-bookmark-enable"
    # Bookmark: Glue tracks which S3 files were already processed
    # Next run only processes NEW files → incremental, not full reload

    "--enable-metrics"                  = "true"
    # Publishes Spark metrics (executor CPU, memory, shuffle read/write)
    # Viewable in CloudWatch → Metrics → Glue

    "--enable-continuous-cloudwatch-log" = "true"
    # Without this: logs only appear AFTER job completes
    # With this: logs stream in real-time → easier debugging

    "--source_bucket"                   = var.data_lake_bucket
    "--target_bucket"                   = var.data_lake_bucket
    "--database_name"                   = var.database_name
    # Custom args read by getResolvedOptions() in etl_job.py

    "--TempDir"                         = "s3://${var.data_lake_bucket}/temp/"
    # REQUIRED: Glue uses this for shuffle data between Spark stages
    # Without this: job will fail with "TempDir not configured" error
  }

  glue_version      = "4.0"   # Spark 3.3.0 + Python 3.10 (latest stable)
  number_of_workers = 2        # Minimum: 1 driver + 1 executor
  worker_type       = "G.1X"  # 4 vCPU, 16GB RAM — right-sized for this data

  timeout = 60   # Kill job if still running after 60 minutes — cost protection

  tags = local.common_tags
}

# ─── Glue Trigger ─────────────────────────────────────────────────────────────

resource "aws_glue_trigger" "daily" {
  name     = "${var.project}-etl-daily"
  type     = "SCHEDULED"
  schedule = "cron(0 2 * * ? *)"
  # AWS cron format: cron(Minutes Hours Day-of-month Month Day-of-week Year)
  # cron(0 2 * * ? *) = 2:00 AM UTC, every day, any day-of-week
  # ? = "no specific value" — required when Day-of-month or Day-of-week is set
  # Note: AWS cron is different from standard cron (has 6 fields, not 5)

  actions {
    job_name = aws_glue_job.etl.name
    # Reference to job defined above — creates implicit dependency
    # Terraform will create the job BEFORE the trigger
  }

  tags = local.common_tags
  # Note: trigger is CREATED but not ACTIVATED by default in Terraform
  # To activate: add enabled = true to this resource (default is false)
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "glue_job_name"     { value = aws_glue_job.etl.name }
output "glue_trigger_name" { value = aws_glue_trigger.daily.name }
# These outputs can be referenced by other projects or printed after apply
```

---

### Terraform Workflow — Step by Step

#### Step T1 — Initialize

```bash
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.2_glue_etl\terraform

terraform init

# Expected output:
# Initializing the backend...
# Initializing provider plugins...
# - Finding hashicorp/aws versions matching "~> 5.0"...
# - Installing hashicorp/aws v5.x.x...
# - Installed hashicorp/aws v5.x.x
#
# Terraform has been successfully initialized!
```

**What `terraform init` does:**
- Downloads the AWS provider plugin (~100MB)
- Creates `.terraform/` directory with provider binary
- Creates `.terraform.lock.hcl` locking provider version

#### Step T2 — Plan (Dry Run)

```bash
terraform plan \
  -var="data_lake_bucket=YOUR_BUCKET_NAME" \
  -var="glue_role_arn=arn:aws:iam::123456789012:role/handson-glue-role" \
  -var="database_name=handson_data_lake"

# Expected output:
# Terraform will perform the following actions:
#
#   # aws_glue_job.etl will be created
#   + resource "aws_glue_job" "etl" {
#       + name              = "handson-etl-job"
#       + role_arn          = "arn:aws:iam::123456789012:role/handson-glue-role"
#       + glue_version      = "4.0"
#       + number_of_workers = 2
#       + worker_type       = "G.1X"
#       + timeout           = 60
#     }
#
#   # aws_glue_trigger.daily will be created
#   + resource "aws_glue_trigger" "daily" {
#       + name     = "handson-etl-daily"
#       + type     = "SCHEDULED"
#       + schedule = "cron(0 2 * * ? *)"
#     }
#
#   # aws_s3_object.etl_script will be created
#   + resource "aws_s3_object" "etl_script" {
#       + bucket = "YOUR_BUCKET_NAME"
#       + key    = "scripts/etl_job.py"
#     }
#
# Plan: 3 to add, 0 to change, 0 to destroy.
```

**What to look for in `terraform plan`:**
- `+` (green) = resource will be CREATED
- `~` (yellow) = resource will be MODIFIED
- `-` (red) = resource will be DESTROYED
- Numbers at bottom: "3 to add, 0 to change, 0 to destroy" → safe to apply

#### Step T3 — Apply

```bash
terraform apply \
  -var="data_lake_bucket=YOUR_BUCKET_NAME" \
  -var="glue_role_arn=arn:aws:iam::123456789012:role/handson-glue-role" \
  -var="database_name=handson_data_lake"

# Type "yes" when prompted:
# Do you want to perform these actions?
#   Terraform will perform the actions described above.
#   Only 'yes' will be accepted to approve.
# Enter a value: yes

# Expected output:
# aws_s3_object.etl_script: Creating...
# aws_s3_object.etl_script: Creation complete after 1s
# aws_glue_job.etl: Creating...
# aws_glue_job.etl: Creation complete after 5s
# aws_glue_trigger.daily: Creating...
# aws_glue_trigger.daily: Creation complete after 3s
#
# Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
#
# Outputs:
# glue_job_name     = "handson-etl-job"
# glue_trigger_name = "handson-etl-daily"
```

#### Step T4 — Run and Monitor via CLI (after Terraform apply)

```bash
# Start job run
$JOB_NAME = terraform output -raw glue_job_name
$RUN_ID   = aws glue start-job-run --job-name $JOB_NAME --query "JobRunId" --output text
echo "Run ID: $RUN_ID"

# Monitor
aws glue get-job-run --job-name $JOB_NAME --run-id $RUN_ID `
  --query "JobRun.{State:JobRunState,Duration:ExecutionTime}"
```

#### Step T5 — State Verification

```bash
# List all resources managed by Terraform
terraform state list

# Expected:
# aws_glue_job.etl
# aws_glue_trigger.daily
# aws_s3_object.etl_script

# Inspect specific resource
terraform state show aws_glue_job.etl

# Confirm no drift (real vs desired state)
terraform plan
# Expected: "No changes. Your infrastructure matches the configuration."
```

---

## 6. CODE DEEP DIVE — etl_job.py

### Section 1 — Initialization

```python
args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "source_bucket",
    "target_bucket",
    "database_name",
])
```
- `getResolvedOptions` reads arguments passed via `--default-arguments` in the job config
- `JOB_NAME` is automatically injected by Glue (not in your --default-arguments)
- Your custom args (`source_bucket`, etc.) must match the key names in default_arguments
- **Common mistake:** using `--source_bucket` in job args but `source-bucket` (hyphen) in script → KeyError

```python
sc          = SparkContext()
glueContext = GlueContext(sc)
spark       = glueContext.spark_session
job         = Job(glueContext)
job.init(args["JOB_NAME"], args)
```
- `SparkContext` — entry point to Spark; allocates executors
- `GlueContext` — Glue-specific wrapper adding DynamicFrame support
- `spark_session` — SparkSession for DataFrame API
- `job.init()` — REQUIRED: initializes job bookmark tracking
- **Common mistake:** forgetting `job.commit()` at end → bookmarks never saved

### Section 2 — Extract with DynamicFrame

```python
raw_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [f"s3://{SOURCE_BUCKET}/raw/orders/"],
        "recurse": True,        # ← scan subdirectories too
    },
    format="csv",
    format_options={"withHeader": True, "separator": ","},
    transformation_ctx="raw_orders",  # ← bookmark key for this step
)
```
- `connection_type="s3"` — read from S3 (can also be "jdbc", "dynamodb", etc.)
- `recurse: True` — reads all files in all subdirectories under the path
- `transformation_ctx` — MUST be unique per DynamicFrame; used by bookmark to track state
- **Common mistake:** re-using the same `transformation_ctx` for two DynamicFrames → bookmark confusion

### Section 3 — Transform

```python
df_clean = (
    df
    .dropna(subset=["order_id", "amount"])    # Remove rows where these are null
    .withColumn("amount", F.col("amount").cast(DoubleType()))   # String → Double
    .withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))  # String → Date
    .withColumn("year",  F.year("order_date"))    # Extract year for partitioning
    .withColumn("month", F.month("order_date"))   # Extract month for partitioning
    .withColumn("product", F.upper(F.trim("product")))  # Clean text: trim spaces + uppercase
    .withColumn("processed_at", F.current_timestamp())  # Audit column
    .dropDuplicates(["order_id"])               # Remove exact duplicate order IDs
)
```

**Why each step matters:**
- `dropna(subset=...)` — Athena will error on NULL in certain functions; clean first
- `cast(DoubleType())` — CSV reads everything as string; Athena needs proper types
- `to_date(...)` — enables year/month extraction; Athena date functions need Date type
- `F.upper(F.trim(...))` — normalizes text: "widget " and "WIDGET" become "WIDGET"
- `dropDuplicates(["order_id"])` — CSV files may have duplicates from reprocessing

### Section 4 — Load with Partitioning

```python
df_clean.write.mode("overwrite").partitionBy("year", "month").parquet(...)
```
- `mode("overwrite")` — replaces existing data at this path
- `partitionBy("year", "month")` — creates folder structure `year=2024/month=01/`
- `.parquet(...)` — columnar format with Snappy compression by default
- **Common mistake:** using `mode("append")` without thinking → duplicates accumulate

### Common Syntax Mistakes to Avoid

| Mistake | Error | Fix |
|---------|-------|-----|
| `job.init()` without `job.commit()` | Bookmarks never saved; reprocesses all files next run | Add `job.commit()` at end |
| `F.col("amount").cast("double")` string vs `DoubleType()` | Both work but DoubleType() is more explicit | Either is fine |
| Reading from wrong S3 path | FileNotFoundException | Print and verify `SOURCE_BUCKET` at start |
| Forgetting `--TempDir` in job args | GlueException: No TempDir | Always include in default_arguments |
| `getResolvedOptions` key mismatch | KeyError | Exact match: `source_bucket` not `source-bucket` |
