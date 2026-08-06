# Steps — Project 9.7 Data Quality Validation
# PowerShell (Windows)

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.7_data_quality

$REGION      = "us-east-1"
$ACCOUNT     = aws sts get-caller-identity --query Account --output text
$BUCKET      = "handson-data-lake-$ACCOUNT"
$LAMBDA_NAME = "handson-data-quality-check"
$ROLE_NAME   = "handson-quality-lambda-role"
$TOPIC_NAME  = "handson-data-quality-alerts"
$ALERT_EMAIL = "your-email@example.com"   # CHANGE THIS

Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
```

---

## Phase 1 — Install + Run Locally (Zero Cost)

```powershell
pip install great-expectations==0.18.12 pandas pyarrow s3fs

# Test with dirty data (should FAIL)
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002',None,'ORD-001'],
    'customer_id':['C1','C2','C3','C4'],
    'product':    ['Widget A','Widget B','Unknown','Widget C'],
    'amount':     [29.99,-5.00,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16','2024-01-16']
}).to_parquet('/tmp/dirty.parquet', index=False)"

$env:DATA_LAKE_BUCKET = "local-test"
python src\validate_orders.py
Write-Host "Exit code: $LASTEXITCODE"   # Expected: 1 (FAILED)

# Test with clean data (should PASS)
python -c "
import pandas as pd
pd.DataFrame({
    'order_id':   ['ORD-001','ORD-002','ORD-003'],
    'customer_id':['C1','C2','C3'],
    'product':    ['Widget A','Widget B','Widget C'],
    'amount':     [29.99,49.99,19.99],
    'order_date': ['2024-01-15','2024-01-15','2024-01-16']
}).to_parquet('/tmp/clean.parquet', index=False)"

python src\validate_orders.py
Write-Host "Exit code: $LASTEXITCODE"   # Expected: 0 (PASSED)
```

---

## Phase 2 — Create SNS Topic + Subscription

```powershell
$TOPIC_ARN = aws sns create-topic --name $TOPIC_NAME --query "TopicArn" --output text
Write-Host "Topic: $TOPIC_ARN"

aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint $ALERT_EMAIL
Write-Host "⚠️ Check $ALERT_EMAIL and confirm subscription!"

# Verify after confirming
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN `
  --query "Subscriptions[*].{Status:SubscriptionArn}" --output table
```

---

## Phase 3 — Create IAM Role

```powershell
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\trust.json"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query "Role.Arn" --output text

aws iam attach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

@"
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket","s3:PutObject"],"Resource":["arn:aws:s3:::$BUCKET","arn:aws:s3:::$BUCKET/*"]},{"Effect":"Allow","Action":["sns:Publish"],"Resource":"$TOPIC_ARN"}]}
"@ | Out-File "$env:TEMP\policy.json" -Encoding utf8

aws iam put-role-policy --role-name $ROLE_NAME `
  --policy-name "quality-s3-sns-access" `
  --policy-document "file://$env:TEMP\policy.json"

Write-Host "Role ARN: $ROLE_ARN"
```

---

## Phase 4 — Package + Deploy Lambda

```powershell
New-Item -ItemType Directory -Path "lambda_package" -Force
pip install great-expectations pandas pyarrow s3fs -t lambda_package\ --quiet
Copy-Item src\validate_orders.py lambda_package\
Compress-Archive -Path lambda_package\* -DestinationPath quality.zip -Force

Start-Sleep -Seconds 10  # IAM propagation

aws lambda create-function `
  --function-name $LAMBDA_NAME --runtime python3.11 `
  --role $ROLE_ARN --handler validate_orders.main `
  --zip-file "fileb://quality.zip" --timeout 300 --memory-size 512 `
  --environment "Variables={DATA_LAKE_BUCKET=$BUCKET,SNS_TOPIC_ARN=$TOPIC_ARN}"

aws lambda wait function-active --function-name $LAMBDA_NAME
Write-Host "✅ Lambda deployed"
```

---

## Phase 5 — Create EventBridge Rule

```powershell
$LAMBDA_ARN = aws lambda get-function --function-name $LAMBDA_NAME `
  --query "Configuration.FunctionArn" --output text

$RULE_ARN = aws events put-rule `
  --name "handson-glue-job-success" `
  --event-pattern '{"source":["aws.glue"],"detail-type":["Glue Job State Change"],"detail":{"jobName":["handson-etl-job"],"state":["SUCCEEDED"]}}' `
  --state ENABLED --query "RuleArn" --output text

aws events put-targets --rule "handson-glue-job-success" `
  --targets "Id=QualityCheck,Arn=$LAMBDA_ARN"

aws lambda add-permission --function-name $LAMBDA_NAME `
  --statement-id "AllowEventBridge" --action "lambda:InvokeFunction" `
  --principal "events.amazonaws.com" --source-arn $RULE_ARN

Write-Host "✅ EventBridge rule active"
```

---

## Phase 6 — Test Lambda

```powershell
aws lambda invoke --function-name $LAMBDA_NAME --payload '{}' `
  --log-type Tail response.json
Get-Content response.json
aws logs tail "/aws/lambda/$LAMBDA_NAME" --since 5m
```

---

## Phase 7 — Cleanup

```powershell
aws events remove-targets --rule "handson-glue-job-success" --ids "QualityCheck"
aws events delete-rule --name "handson-glue-job-success"
aws lambda delete-function --function-name $LAMBDA_NAME
aws sns delete-topic --topic-arn $TOPIC_ARN
aws iam delete-role-policy --role-name $ROLE_NAME --policy-name "quality-s3-sns-access"
aws iam detach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
aws iam delete-role --role-name $ROLE_NAME
aws s3 rm "s3://$BUCKET/data-quality/" --recursive
aws s3 rm "s3://$BUCKET/quarantine/" --recursive
Remove-Item quality.zip, response.json, -Recurse lambda_package -ErrorAction SilentlyContinue
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] `dbt run` / `validate_orders.py` FAILED output — 3 specific checks fail
- [ ] `validate_orders.py` PASSED output — all 10 checks green
- [ ] SNS topic created with email subscription Confirmed
- [ ] EventBridge rule JSON pattern
- [ ] Lambda function with env vars (DATA_LAKE_BUCKET, SNS_TOPIC_ARN)
- [ ] CloudWatch Logs showing validation output
- [ ] S3 data-quality/reports/ with JSON files
