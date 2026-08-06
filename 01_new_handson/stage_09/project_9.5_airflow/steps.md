# Steps — Project 9.5 Airflow Data Orchestration
# PowerShell (Windows) + Docker

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$BUCKET    = "handson-mwaa-$ACCOUNT"
$ENV_NAME  = "handson-airflow"
$ROLE_NAME = "handson-mwaa-role"
Write-Host "Account: $ACCOUNT"
```

---

## Phase 1 — Run Airflow Locally (FREE — Start Here)

```powershell
# Setup
New-Item -ItemType Directory -Path C:\airflow-local -Force
Set-Location C:\airflow-local
New-Item -ItemType Directory -Path dags, logs, plugins -Force

# Download Docker Compose
Invoke-WebRequest `
  -Uri "https://airflow.apache.org/docs/apache-airflow/2.8.1/docker-compose.yaml" `
  -OutFile "docker-compose.yaml"

# Initialize
"AIRFLOW_UID=50000" | Out-File .env -Encoding utf8
docker compose up airflow-init

# Start
docker compose up -d
docker compose ps   # All 5 containers should be Up (healthy)

# Open UI
Start-Process "http://localhost:8080"
# Login: airflow / airflow
```

---

## Phase 2 — Upload DAG

```powershell
# From project root
Copy-Item `
  "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.5_airflow\dags\daily_pipeline.py" `
  "C:\airflow-local\dags\"

# Verify loaded (wait 30s first)
Start-Sleep -Seconds 35
docker exec -it airflow-local-airflow-scheduler-1 airflow dags list
# Expected: daily_data_pipeline listed
```

---

## Phase 3 — Configure Connection + Variables

```powershell
# Add AWS connection
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow connections add aws_default `
  --conn-type "aws" `
  --conn-extra "{`"region_name`": `"$REGION`"}"

# Set variables
docker exec -it airflow-local-airflow-scheduler-1 airflow variables set account_id $ACCOUNT
docker exec -it airflow-local-airflow-scheduler-1 airflow variables set sns_topic_arn "arn:aws:sns:$REGION`:$ACCOUNT`:data-pipeline-alerts"
docker exec -it airflow-local-airflow-scheduler-1 airflow variables set data_lake_bucket "handson-data-lake-$ACCOUNT"
docker exec -it airflow-local-airflow-scheduler-1 airflow variables set glue_job_name "handson-etl-job"

# Verify
docker exec -it airflow-local-airflow-scheduler-1 airflow variables list
```

---

## Phase 4 — Trigger and Monitor

```powershell
# Trigger manually
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags trigger daily_data_pipeline

# Watch task states
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-runs --dag-id daily_data_pipeline --limit 3

# Check for import errors
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-import-errors
# Expected: empty (no errors)
```

---

## Phase 5 — Deploy to MWAA (Optional — $670/month)

```powershell
# Create S3 bucket
aws s3api create-bucket --bucket $BUCKET --region $REGION
aws s3api put-bucket-versioning --bucket $BUCKET `
  --versioning-configuration Status=Enabled
aws s3 cp dags\daily_pipeline.py "s3://$BUCKET/dags/daily_pipeline.py"

# Create IAM role
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":["airflow.amazonaws.com","airflow-env.amazonaws.com"]},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\mwaa-trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\mwaa-trust.json"
$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query "Role.Arn" -o text

# Get subnets (requires private subnets)
$VPC_ID = aws ec2 describe-vpcs --query "Vpcs[?IsDefault==\`true\`].VpcId" -o text

# Create MWAA environment
aws mwaa create-environment --name $ENV_NAME `
  --airflow-version "2.8.1" --dag-s3-path "dags/" `
  --source-bucket-arn "arn:aws:s3:::$BUCKET" `
  --execution-role-arn $ROLE_ARN `
  --environment-class "mw1.small" --max-workers 1

Write-Host "Creating... check Console for status (20-30 min)"
```

---

## Phase 6 — Trigger MWAA DAG via CLI

```powershell
$CLI_TOKEN = aws mwaa create-cli-token --name $ENV_NAME --query "CliToken" -o text
$WEB_URL   = aws mwaa get-environment --name $ENV_NAME --query "Environment.WebserverUrl" -o text

# Trigger DAG
$R = Invoke-RestMethod -Uri "https://$WEB_URL/aws_mwaa/cli" -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN";"Content-Type"="application/json"} `
  -Body '{"command":"dags trigger daily_data_pipeline"}'
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($R.stdout))
```

---

## Phase 7 — Cleanup

```powershell
# Local Docker cleanup
docker compose -f C:\airflow-local\docker-compose.yaml down --volumes

# MWAA cleanup (if deployed)
aws mwaa delete-environment --name $ENV_NAME
aws s3 rm "s3://$BUCKET" --recursive
aws s3api delete-bucket --bucket $BUCKET
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "mwaa-policy"
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] Docker containers all Up (healthy)
- [ ] Airflow UI at localhost:8080 (login page)
- [ ] DAGs list showing daily_data_pipeline
- [ ] DAG Graph view — 6 tasks connected
- [ ] Admin → Variables — 4 variables set
- [ ] Triggered run with colored task states
- [ ] Task log viewer for check_source_data
- [ ] MWAA environment Status=Available (if deployed)
