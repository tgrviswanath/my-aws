# Steps — Project 9.4 Spark Processing on EMR Serverless
# PowerShell commands (Windows). Run from project root.

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.4_spark_emr

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$BUCKET    = "handson-data-lake-$ACCOUNT"   # update to your actual bucket
$APP_NAME  = "handson-spark"
$ROLE_NAME = "handson-emr-serverless-role"

Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
aws sts get-caller-identity
```

---

## Phase 1 — Create IAM Role

```powershell
# Trust policy for EMR Serverless
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"emr-serverless.amazonaws.com"},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\emr-trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\emr-trust.json"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME `
  --query "Role.Arn" --output text

# S3 access policy
@"
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],"Resource":["arn:aws:s3:::$BUCKET","arn:aws:s3:::$BUCKET/*"]}]}
"@ | Out-File "$env:TEMP\emr-s3.json" -Encoding utf8
aws iam put-role-policy --role-name $ROLE_NAME --policy-name "emr-s3-access" `
  --policy-document "file://$env:TEMP\emr-s3.json"

# Glue policy
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["glue:GetDatabase","glue:GetTable","glue:GetPartitions","glue:CreateTable","glue:UpdateTable"],"Resource":"*"}]}
'@ | Out-File "$env:TEMP\emr-glue.json" -Encoding utf8
aws iam put-role-policy --role-name $ROLE_NAME --policy-name "emr-glue-access" `
  --policy-document "file://$env:TEMP\emr-glue.json"

# CloudWatch Logs policy
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents","logs:DescribeLogGroups","logs:DescribeLogStreams"],"Resource":"*"}]}
'@ | Out-File "$env:TEMP\emr-logs.json" -Encoding utf8
aws iam put-role-policy --role-name $ROLE_NAME --policy-name "emr-cloudwatch-access" `
  --policy-document "file://$env:TEMP\emr-logs.json"

Write-Host "Role ARN: $ROLE_ARN"
```

---

## Phase 2 — Upload Script to S3

```powershell
aws s3 cp src\spark_job.py "s3://$BUCKET/scripts/spark_job.py"
aws s3 ls "s3://$BUCKET/scripts/"
# Expected: spark_job.py ~3 KB

$SCRIPT_S3 = "s3://$BUCKET/scripts/spark_job.py"
```

---

## Phase 3 — Create EMR Serverless Application

```powershell
$APP_ID = aws emr-serverless create-application `
  --name $APP_NAME --type "SPARK" --release-label "emr-6.15.0" `
  --initial-capacity '{"Driver":{"workerCount":1,"workerConfiguration":{"cpu":"2 vCPU","memory":"4 GB"}}}' `
  --maximum-capacity '{"cpu":"20 vCPU","memory":"40 GB"}' `
  --auto-stop-configuration '{"enabled":true,"idleTimeoutMinutes":15}' `
  --tags "Project=handson" `
  --query "applicationId" --output text

Write-Host "App ID: $APP_ID"
```

---

## Phase 4 — Start Application

```powershell
aws emr-serverless start-application --application-id $APP_ID

# Wait for STARTED
for ($i=0; $i -lt 20; $i++) {
  $S = aws emr-serverless get-application --application-id $APP_ID `
    --query "application.state" --output text
  Write-Host "State: $S"
  if ($S -eq "STARTED") { break }
  Start-Sleep -Seconds 10
}
```

---

## Phase 5 — Submit Spark Job

```powershell
$INPUT  = "s3://$BUCKET/raw/orders/"
$OUTPUT = "s3://$BUCKET/processed/spark/"
$LOGS   = "s3://$BUCKET/logs/"

$JOB_ID = aws emr-serverless start-job-run `
  --application-id $APP_ID `
  --execution-role-arn $ROLE_ARN `
  --name "handson-order-analysis" `
  --job-driver "{`"sparkSubmit`":{`"entryPoint`":`"$SCRIPT_S3`",`"entryPointArguments`":[`"--input`",`"$INPUT`",`"--output`",`"$OUTPUT`"],`"sparkSubmitParameters`":`"--conf spark.executor.cores=2 --conf spark.executor.memory=4g`"}}" `
  --configuration-overrides "{`"monitoringConfiguration`":{`"s3MonitoringConfiguration`":{`"logUri`":`"$LOGS`"}}}" `
  --query "jobRunId" --output text

Write-Host "Job Run ID: $JOB_ID"
```

---

## Phase 6 — Monitor Job

```powershell
for ($i=0; $i -lt 40; $i++) {
  $S = aws emr-serverless get-job-run --application-id $APP_ID `
    --job-run-id $JOB_ID --query "jobRun.state" --output text
  Write-Host "[$i] State: $S"
  if ($S -eq "SUCCESS" -or $S -eq "FAILED") { break }
  Start-Sleep -Seconds 15
}
Write-Host "Final: $S"
```

---

## Phase 7 — Verify Output

```powershell
aws s3 ls "s3://$BUCKET/processed/spark/" --recursive | Select-String ".parquet"
# Expected: product_monthly + customer_clv Parquet files
```

---

## Phase 8 — Cleanup

```powershell
aws emr-serverless stop-application --application-id $APP_ID
Start-Sleep -Seconds 30
aws emr-serverless delete-application --application-id $APP_ID
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-s3-access"
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-glue-access"
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "emr-cloudwatch-access"
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] IAM role with 3 inline policies
- [ ] EMR Serverless application Status = Started
- [ ] Job run Status = Running
- [ ] Job run Status = Success + duration + vCPU-hours used
- [ ] Spark driver stdout showing "Output written to..."
- [ ] S3: product_monthly/ with year=/month= partition folders
- [ ] S3: customer_clv/ with Parquet files
