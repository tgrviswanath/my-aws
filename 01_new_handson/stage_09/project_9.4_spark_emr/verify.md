# Verification & Validation — Project 9.4 Spark Processing on EMR Serverless

> Resource names from main.tf:
> EMR App: `handson-spark` | IAM Role: `handson-emr-serverless-role`
> Input: `raw/orders/` | Output: `processed/spark/`

---

## 1. AWS Console Verification

| Resource | Navigation Path | Expected State |
|----------|----------------|---------------|
| IAM Role | IAM → Roles → `handson-emr-serverless-role` | Exists with 3 inline policies |
| Trust policy | Role → Trust relationships tab | `emr-serverless.amazonaws.com` |
| S3 Script | S3 → bucket → `scripts/spark_job.py` | File present ~3 KB |
| EMR App | EMR → EMR Serverless → `handson-spark` | Status = Started or Stopped |
| EMR Release | App details | `emr-6.15.0` |
| Job Run | App → Job runs tab | `handson-order-analysis` State = **Success** |
| Job Metrics | Job run details | vCPU-hours and memory GB-hours shown |
| Spark Logs | Job run → Logs → Driver stdout | "Output written to..." message |
| S3 Output 1 | S3 → `processed/spark/product_monthly/` | year=/month= partition folders |
| S3 Output 2 | S3 → `processed/spark/customer_clv/` | Parquet files + `_SUCCESS` |

📸 Screenshot: EMR Serverless job run Status = Success with metrics
📸 Screenshot: S3 product_monthly/ showing year/month partition structure
📸 Screenshot: S3 customer_clv/ showing Parquet files

---

## 2. AWS CLI Verification (PowerShell)

```powershell
# Assumes $APP_ID, $JOB_RUN_ID, $BUCKET, $ROLE_NAME are set

# 2.1 Confirm IAM role and policies
aws iam list-role-policies --role-name $ROLE_NAME --query "PolicyNames"
# Expected: ["emr-s3-access","emr-glue-access","emr-cloudwatch-access"]

aws iam get-role --role-name $ROLE_NAME `
  --query "Role.AssumeRolePolicyDocument.Statement[0].Principal.Service"
# Expected: "emr-serverless.amazonaws.com"

# 2.2 Confirm script in S3
aws s3 ls "s3://$BUCKET/scripts/spark_job.py"
# Expected: date time size spark_job.py

# 2.3 Confirm application state
aws emr-serverless get-application --application-id $APP_ID `
  --query "application.{Name:name,State:state,Release:releaseLabel,MaxCPU:maximumCapacity.cpu}"
# Expected: Name=handson-spark, Release=emr-6.15.0, MaxCPU=20 vCPU

# 2.4 Confirm job run succeeded
aws emr-serverless get-job-run `
  --application-id $APP_ID --job-run-id $JOB_RUN_ID `
  --query "jobRun.{State:state,Name:name,CreatedAt:createdAt,UpdatedAt:updatedAt}"
# Expected: State=SUCCESS

# 2.5 Confirm product_monthly output exists
aws s3 ls "s3://$BUCKET/processed/spark/product_monthly/" --recursive |
  Select-String ".parquet"
# Expected: one or more lines with .snappy.parquet paths

# 2.6 Confirm customer_clv output exists
aws s3 ls "s3://$BUCKET/processed/spark/customer_clv/"
# Expected: part-00000-*.snappy.parquet + _SUCCESS file

# 2.7 List all job runs for the application
aws emr-serverless list-job-runs --application-id $APP_ID `
  --query "jobRuns[*].{Name:name,State:state,Id:id}" --output table
# Expected: handson-order-analysis with SUCCESS state
```

---

## 3. Health Check — End-to-End Test (PowerShell)

```powershell
Write-Host "=== EMR SERVERLESS END-TO-END TEST ===" -ForegroundColor Cyan

# 1. Verify app is in a usable state
$APP_STATE = aws emr-serverless get-application --application-id $APP_ID `
  --query "application.state" --output text
Write-Host "[1] App state: $APP_STATE"
if ($APP_STATE -ne "STARTED") {
  Write-Host "Starting application..."
  aws emr-serverless start-application --application-id $APP_ID
  Start-Sleep -Seconds 30
}

# 2. Submit a fresh job run
$NEW_JOB = aws emr-serverless start-job-run `
  --application-id $APP_ID --execution-role-arn $ROLE_ARN `
  --name "verify-run" `
  --job-driver "{`"sparkSubmit`":{`"entryPoint`":`"s3://$BUCKET/scripts/spark_job.py`",`"entryPointArguments`":[`"--input`",`"s3://$BUCKET/raw/orders/`",`"--output`",`"s3://$BUCKET/processed/spark/`"]}}" `
  --query "jobRunId" --output text
Write-Host "[2] Job submitted: $NEW_JOB"

# 3. Poll to completion
for ($i=0; $i -lt 30; $i++) {
  $S = aws emr-serverless get-job-run --application-id $APP_ID `
    --job-run-id $NEW_JOB --query "jobRun.state" --output text
  Write-Host "   State: $S"
  if ($S -eq "SUCCESS" -or $S -eq "FAILED") { break }
  Start-Sleep -Seconds 15
}
Write-Host "[3] Final state: $S"

# 4. Check output
$COUNT = (aws s3 ls "s3://$BUCKET/processed/spark/" --recursive |
          Select-String ".parquet").Count
Write-Host "[4] Parquet files in output: $COUNT"

Write-Host "=== TEST COMPLETE ===" -ForegroundColor Green
```

---

## 4. Expected Successful Outputs

**IAM role policies:**
```json
{"PolicyNames": ["emr-s3-access", "emr-glue-access", "emr-cloudwatch-access"]}
```

**EMR application:**
```json
{"Name": "handson-spark", "State": "STARTED", "Release": "emr-6.15.0", "MaxCPU": "20 vCPU"}
```

**Job run:**
```json
{"State": "SUCCESS", "Name": "handson-order-analysis"}
```

**Spark driver stdout (from S3 logs):**
```
Spark version: 3.4.x
Reading from: s3://YOUR_BUCKET/raw/orders/
Total records: 1000
Output written to: s3://YOUR_BUCKET/processed/spark/
Product monthly records: 15
Customer CLV records: 200
```

**S3 output structure:**
```
processed/spark/
  product_monthly/
    year=2024/
      month=1/  part-00000-abc.snappy.parquet
      month=2/  part-00000-abc.snappy.parquet
    _SUCCESS
  customer_clv/
    part-00000-abc.snappy.parquet
    _SUCCESS
```

---

## 5. Verification Checklist

- [ ] IAM role `handson-emr-serverless-role` exists
- [ ] Trust principal = `emr-serverless.amazonaws.com` (not `emr.amazonaws.com`)
- [ ] Role has `emr-s3-access` inline policy (s3:GetObject/PutObject on bucket)
- [ ] Role has `emr-glue-access` inline policy (glue:GetTable etc.)
- [ ] Role has `emr-cloudwatch-access` inline policy (logs:PutLogEvents etc.)
- [ ] `scripts/spark_job.py` exists in S3 bucket
- [ ] EMR Serverless application `handson-spark` exists
- [ ] Application release = `emr-6.15.0`
- [ ] Application max capacity = `20 vCPU / 40 GB`
- [ ] Auto-stop enabled with 15-minute idle timeout
- [ ] Job run `handson-order-analysis` State = SUCCESS
- [ ] `processed/spark/product_monthly/` has Parquet files with year=/month= folders
- [ ] `processed/spark/customer_clv/` has Parquet files + `_SUCCESS`
- [ ] Driver stdout shows "Output written to..."

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
