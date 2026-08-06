# Verification & Validation — Project 9.5 Airflow Data Orchestration

> Primary DAG: `daily_data_pipeline` (dags/daily_pipeline.py)
> Local: http://localhost:8080 | MWAA: aws mwaa get-environment --name handson-airflow

---

## 1. Local Docker Verification

| Check | Command / Location | Expected |
|-------|-------------------|----------|
| Containers | `docker compose ps` | 5 containers Up (healthy) |
| Webserver | http://localhost:8080 | Login page loads |
| DAG loaded | UI → DAGs list | `daily_data_pipeline` visible, no red banner |
| No import errors | UI → red banner at top | No red banner |
| Variables set | Admin → Variables | account_id, sns_topic_arn, data_lake_bucket, glue_job_name |
| Connection set | Admin → Connections | aws_default exists |
| DAG graph | DAG → Graph tab | 6 tasks connected in correct order |
| Task trigger | ▶ button → trigger | Run appears in Run column |

📸 Screenshot: Airflow DAGs list with daily_data_pipeline, no import errors
📸 Screenshot: DAG Graph showing all 6 tasks connected
📸 Screenshot: Run with task states colored

---

## 2. AWS CLI Verification (PowerShell)

### Local Docker

```powershell
# Verify containers
docker compose -f C:\airflow-local\docker-compose.yaml ps
# Expected: 5 containers all "running" or "healthy"

# Check DAG list
docker exec -it airflow-local-airflow-scheduler-1 airflow dags list
# Expected: daily_data_pipeline with is_paused=False

# Check for import errors
docker exec -it airflow-local-airflow-scheduler-1 airflow dags list-import-errors
# Expected: empty output

# Verify variables
docker exec -it airflow-local-airflow-scheduler-1 airflow variables list
# Expected: account_id, sns_topic_arn, data_lake_bucket, glue_job_name

# Verify connection
docker exec -it airflow-local-airflow-scheduler-1 airflow connections get aws_default
# Expected: connection details printed

# Trigger and watch
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags trigger daily_data_pipeline
docker exec -it airflow-local-airflow-scheduler-1 `
  airflow dags list-runs --dag-id daily_data_pipeline --limit 3
```

### MWAA (PowerShell)

```powershell
$ENV_NAME = "handson-airflow"
$BUCKET   = "handson-mwaa-$ACCOUNT"

# Check environment status
aws mwaa get-environment --name $ENV_NAME `
  --query "Environment.{Status:Status,Version:AirflowVersion,URL:WebserverUrl}"
# Expected: Status=AVAILABLE, Version=2.8.1

# Verify DAG file in S3
aws s3 ls "s3://$BUCKET/dags/"
# Expected: daily_pipeline.py listed

# Get token and check DAG via API
$CLI_TOKEN = aws mwaa create-cli-token --name $ENV_NAME --query "CliToken" -o text
$WEB_URL   = aws mwaa get-environment --name $ENV_NAME --query "Environment.WebserverUrl" -o text

$R = Invoke-RestMethod -Uri "https://$WEB_URL/aws_mwaa/cli" -Method POST `
  -Headers @{"Authorization"="Bearer $CLI_TOKEN";"Content-Type"="application/json"} `
  -Body '{"command":"dags list"}'
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($R.stdout))
# Expected: daily_data_pipeline listed, is_paused=False

# Check MWAA logs
aws logs describe-log-groups `
  --log-group-name-prefix "airflow-$ENV_NAME" `
  --query "logGroups[*].logGroupName"
# Expected: scheduler, task, webserver log groups
```

---

## 3. Health Check — Full Pipeline Test

```powershell
Write-Host "=== AIRFLOW HEALTH CHECK ===" -ForegroundColor Cyan

# Local Docker path
$SCHED = "airflow-local-airflow-scheduler-1"

# 1. DAG loaded without errors
$ERRORS = docker exec -it $SCHED airflow dags list-import-errors 2>&1
if ($ERRORS -match "daily_data_pipeline") {
  Write-Host "❌ Import error in DAG" -ForegroundColor Red
} else {
  Write-Host "✅ DAG loaded without import errors"
}

# 2. Variables set
$VARS = docker exec -it $SCHED airflow variables list 2>&1
Write-Host "✅ Variables: $VARS"

# 3. Trigger run
docker exec -it $SCHED airflow dags trigger daily_data_pipeline 2>&1
Write-Host "✅ DAG triggered"

# 4. Check run appeared
Start-Sleep -Seconds 5
$RUNS = docker exec -it $SCHED airflow dags list-runs `
  --dag-id daily_data_pipeline --limit 1 2>&1
Write-Host "✅ Run status: $RUNS"

Write-Host "=== CHECK COMPLETE ===" -ForegroundColor Green
```

---

## 4. Expected Successful Outputs

**`airflow dags list` output:**
```
dag_id               | filepath              | owner            | paused
daily_data_pipeline  | /opt/airflow/dags/... | data-engineering | False
```

**`airflow dags list-import-errors` output:**
```
(empty — no output means no errors)
```

**`airflow dags list-runs --dag-id daily_data_pipeline` output:**
```
dag_id               | run_id                              | state   | execution_date
daily_data_pipeline  | manual__2024-01-15T00:00:00+00:00   | running | 2024-01-15 00:00:00+00:00
```

**MWAA get-environment:**
```json
{"Status": "AVAILABLE", "AirflowVersion": "2.8.1", "URL": "xxx.c2.us-east-1.airflow.amazonaws.com"}
```

---

## 5. Verification Checklist

**Local Docker:**
- [ ] 5 Docker containers Up and healthy
- [ ] http://localhost:8080 loads login page
- [ ] Login with airflow/airflow succeeds
- [ ] `daily_data_pipeline` in DAGs list
- [ ] No red import-error banner
- [ ] DAG Graph shows 6 tasks in correct order
- [ ] `aws_default` connection configured
- [ ] 4 Airflow Variables set
- [ ] Manual trigger creates a DagRun
- [ ] Task logs visible in UI

**MWAA (if deployed):**
- [ ] MWAA environment `handson-airflow` Status = AVAILABLE
- [ ] `dags/daily_pipeline.py` in S3 bucket
- [ ] Airflow UI accessible via WebserverUrl
- [ ] DAG visible in MWAA Airflow UI
- [ ] CLI token trigger works
- [ ] CloudWatch log groups exist for MWAA

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
