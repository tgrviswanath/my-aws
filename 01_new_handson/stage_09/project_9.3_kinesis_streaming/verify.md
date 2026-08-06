# Verification & Validation — Project 9.3 Real-Time Streaming Pipeline

> All resource names come directly from terraform/main.tf and terraform/terraform.tfvars.
> Lambda function: `handson-kinesis-consumer` | Stream: `handson-events` | Table: `handson-stream-aggregates`

---

## 1. AWS Console Verification

| Resource | Where to Check | Expected State |
|----------|---------------|----------------|
| Kinesis Stream | Kinesis → Data Streams | `handson-events` Status = **Active** |
| Shard count | Stream → Details tab | Shard count = 1 |
| Retention | Stream → Details tab | 24 hours |
| Lambda Function | Lambda → Functions | `handson-kinesis-consumer` State = Active |
| Lambda Trigger | Lambda → `handson-kinesis-consumer` → Configuration → Triggers | Kinesis `handson-events` State = **Enabled** |
| DynamoDB Table | DynamoDB → Tables | `handson-stream-aggregates` Status = **Active** |
| DynamoDB Items | Table → Explore items | Items appear after running producer |
| SQS DLQ | SQS → Queues | `handson-kinesis-dlq` exists, 0 messages |
| CloudWatch Logs | CloudWatch → Log groups | `/aws/lambda/handson-kinesis-consumer` |
| Lambda Env Var | Lambda → Configuration → Environment variables | `TABLE_NAME` = `handson-stream-aggregates` |

📸 Screenshot: Kinesis stream `handson-events` Status = Active, shard count = 1
📸 Screenshot: Lambda `handson-kinesis-consumer` Triggers tab — Kinesis trigger Enabled
📸 Screenshot: DynamoDB `handson-stream-aggregates` Explore items — product aggregates visible

---

## 2. AWS CLI Verification (PowerShell)

```powershell
$STREAM   = "handson-events"
$TABLE    = "handson-stream-aggregates"
$FUNCTION = "handson-kinesis-consumer"
$DLQ      = "handson-kinesis-dlq"

# 2.1 Confirm stream exists and is ACTIVE
aws kinesis describe-stream-summary `
  --stream-name $STREAM `
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount,RetentionHours:RetentionPeriodHours}"
# Expected: {"Status": "ACTIVE", "Shards": 1, "RetentionHours": 24}

# 2.2 Confirm Lambda function exists and is Active
aws lambda get-function --function-name $FUNCTION `
  --query "Configuration.{State:State,Runtime:Runtime,Handler:Handler,Timeout:Timeout}"
# Expected: {"State": "Active", "Runtime": "python3.11",
#            "Handler": "consumer_lambda.handler", "Timeout": 60}

# 2.3 Confirm Kinesis trigger is Enabled on Lambda
aws lambda list-event-source-mappings `
  --function-name $FUNCTION `
  --query "EventSourceMappings[0].{State:State,BatchSize:BatchSize,StartPos:StartingPosition,Bisect:BisectBatchOnFunctionError}"
# Expected: {"State": "Enabled", "BatchSize": 100, "StartPos": "LATEST", "Bisect": true}

# 2.4 Confirm DynamoDB table is ACTIVE
aws dynamodb describe-table --table-name $TABLE `
  --query "Table.{Status:TableStatus,HashKey:KeySchema[0].AttributeName,RangeKey:KeySchema[1].AttributeName}"
# Expected: {"Status": "ACTIVE", "HashKey": "pk", "RangeKey": "sk"}

# 2.5 Confirm SQS DLQ exists with 0 messages
$DLQ_URL = aws sqs get-queue-url --queue-name $DLQ --query "QueueUrl" --output text
aws sqs get-queue-attributes --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages"
# Expected: "0"

# 2.6 Produce test events
python src/producer.py
# Expected output from producer.py:
# Sending 50 events to stream: handson-events
#   [1/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537...
#   ...
# Done. Sent 50 events.

# 2.7 Wait for Lambda to process, then verify records in stream
$SHARD_ID = aws kinesis list-shards `
  --stream-name $STREAM `
  --query "Shards[0].ShardId" --output text

$ITERATOR = aws kinesis get-shard-iterator `
  --stream-name $STREAM `
  --shard-id $SHARD_ID `
  --shard-iterator-type TRIM_HORIZON `
  --query "ShardIterator" --output text

aws kinesis get-records `
  --shard-iterator $ITERATOR `
  --limit 3 `
  --query "Records[*].{PartitionKey:PartitionKey,Seq:SequenceNumber}" `
  --output table
# Expected: 3 records listed with CUST-xxx partition keys

# 2.8 Check Lambda invocations (last 5 minutes)
Start-Sleep -Seconds 10
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Invocations `
  --dimensions Name=FunctionName,Value=$FUNCTION `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Sum `
  --query "Datapoints[*].Sum"
# Expected: [1.0] or more (Lambda was invoked)

# 2.9 Check iterator age — should be near 0 (Lambda keeping up)
aws cloudwatch get-metric-statistics `
  --namespace AWS/Kinesis `
  --metric-name "GetRecords.IteratorAgeMilliseconds" `
  --dimensions Name=StreamName,Value=$STREAM `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Maximum `
  --query "Datapoints[*].Maximum"
# Expected: low value near 0 (no lag)

# 2.10 Check DynamoDB has aggregates after producing
aws dynamodb scan `
  --table-name $TABLE `
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" `
  --output table
# Expected: rows like PRODUCT#Widget A | HOUR#2024-... | 10 | 45670
# Note: Revenue is in CENTS — divide by 100 for dollars
```

---

## 3. Terraform State Verification

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming\terraform

# List all managed resources (exactly 9 expected)
terraform state list
# Expected:
# aws_dynamodb_table.aggregates
# aws_iam_role.lambda
# aws_iam_role_policy.lambda_kinesis_dynamo
# aws_iam_role_policy_attachment.lambda_basic
# aws_kinesis_stream.events
# aws_lambda_event_source_mapping.kinesis
# aws_lambda_function.consumer
# aws_sqs_queue.dlq
# data.archive_file.lambda

# Inspect the Kinesis stream resource
terraform state show aws_kinesis_stream.events
# Look for: name="handson-events", shard_count=1, retention_period=24

# Inspect Lambda event source mapping
terraform state show aws_lambda_event_source_mapping.kinesis
# Look for: starting_position="LATEST", batch_size=100, bisect_batch_on_function_error=true

# Confirm outputs
terraform output stream_name     # handson-events
terraform output lambda_name     # handson-kinesis-consumer
terraform output table_name      # handson-stream-aggregates
terraform output dlq_url         # https://sqs.us-east-1.amazonaws.com/...
terraform output tail_logs       # aws logs tail ... --follow

# Confirm no config drift
terraform plan -var-file="terraform.tfvars"
# Expected: No changes. Your infrastructure matches the configuration.
```

---

## 4. Health Check — End-to-End Pipeline Test (PowerShell)

```powershell
Write-Host "=== END-TO-END PIPELINE TEST ===" -ForegroundColor Cyan

# Step 1: Verify all resources exist before testing
$STREAM   = "handson-events"
$TABLE    = "handson-stream-aggregates"
$FUNCTION = "handson-kinesis-consumer"
$DLQ      = "handson-kinesis-dlq"

$STREAM_STATUS = aws kinesis describe-stream-summary `
  --stream-name $STREAM `
  --query "StreamDescriptionSummary.StreamStatus" --output text
Write-Host "[1] Stream status: $STREAM_STATUS" # Expected: ACTIVE

$LAMBDA_STATE = aws lambda get-function --function-name $FUNCTION `
  --query "Configuration.State" --output text
Write-Host "[2] Lambda state: $LAMBDA_STATE" # Expected: Active

$TRIGGER_STATE = aws lambda list-event-source-mappings `
  --function-name $FUNCTION `
  --query "EventSourceMappings[0].State" --output text
Write-Host "[3] Trigger state: $TRIGGER_STATE" # Expected: Enabled

# Step 2: Produce 50 events
Write-Host "`n[4] Sending 50 events..."
python src/producer.py

# Step 3: Wait for Lambda processing (< 5 seconds normally)
Write-Host "[5] Waiting 15s for Lambda to process..."
Start-Sleep -Seconds 15

# Step 4: Verify DynamoDB was updated
$ITEM_COUNT = aws dynamodb scan --table-name $TABLE `
  --query "Count" --output text
Write-Host "[6] DynamoDB aggregate items: $ITEM_COUNT" # Expected: > 0 (up to 5 products)

# Step 5: Check CloudWatch logs for success
$LOG_GROUP = "/aws/lambda/$FUNCTION"
Write-Host "[7] Recent Lambda logs:"
aws logs tail $LOG_GROUP --since 2m 2>$null | Select-Object -Last 5
# Expected: "Batch complete: 50 records, 0 errors"

# Step 6: Verify DLQ is empty (no failures)
$DLQ_URL = aws sqs get-queue-url --queue-name $DLQ --query "QueueUrl" --output text
$DLQ_COUNT = aws sqs get-queue-attributes --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages" --output text
Write-Host "[8] DLQ message count: $DLQ_COUNT" # Expected: 0

Write-Host "`n=== TEST COMPLETE ===" -ForegroundColor Green
```

---

## 5. Expected Successful Outputs

**`producer.py` terminal output:**
```
Sending 50 events to stream: handson-events
  [1/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537014...
  [2/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537015...
  ...
  [50/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537063...

Done. Sent 50 events.
```

**CloudWatch Logs for Lambda (`/aws/lambda/handson-kinesis-consumer`):**
```
Processing batch of 50 records
  Processed: ORDER_PLACED | Product: Widget A | Amount: $45.23
  Processed: ORDER_PLACED | Product: Widget B | Amount: $31.10
  Processed: ORDER_PLACED | Product: Gadget X | Amount: $72.50
  ...
Batch complete: 50 records, 0 errors
```

**`describe-stream-summary` output:**
```json
{ "Status": "ACTIVE", "Shards": 1, "RetentionHours": 24 }
```

**`list-event-source-mappings` output:**
```json
{ "State": "Enabled", "BatchSize": 100, "StartPos": "LATEST", "Bisect": true }
```

**DynamoDB scan output (example):**
```
-----------------------------------------------------------------------
| Product              | Hour                    | Orders | Revenue   |
+----------------------+-------------------------+--------+-----------+
| PRODUCT#Gadget X     | HOUR#2024-01-15T14:00Z  | 10     | 72500     |
| PRODUCT#Gadget Y     | HOUR#2024-01-15T14:00Z  | 8      | 48320     |
| PRODUCT#Widget A     | HOUR#2024-01-15T14:00Z  | 15     | 45670     |
| PRODUCT#Widget B     | HOUR#2024-01-15T14:00Z  | 12     | 37440     |
| PRODUCT#Widget C     | HOUR#2024-01-15T14:00Z  | 5      | 24980     |
-----------------------------------------------------------------------
Note: Revenue is stored in CENTS — divide by 100 to get dollars
```

---

## 6. Verification Checklist

- [ ] Kinesis stream `handson-events` Status = **ACTIVE**, Shards = 1, Retention = 24h
- [ ] Lambda `handson-kinesis-consumer` State = **Active**, Runtime = python3.11
- [ ] Lambda handler = `consumer_lambda.handler`
- [ ] Lambda env var `TABLE_NAME` = `handson-stream-aggregates`
- [ ] Lambda trigger: Kinesis `handson-events`, State = **Enabled**, BatchSize = 100
- [ ] Lambda trigger: StartingPosition = LATEST, BisectBatchOnFunctionError = true
- [ ] DynamoDB `handson-stream-aggregates` Status = **ACTIVE**, pk+sk key schema
- [ ] SQS `handson-kinesis-dlq` exists with 0 messages
- [ ] `producer.py` sends 50 events without error — shows ShardId + SequenceNumber per event
- [ ] CloudWatch Logs group `/aws/lambda/handson-kinesis-consumer` has log streams
- [ ] Lambda invocations metric > 0 after producing events
- [ ] DynamoDB has aggregate items (up to 5 — one per product) after producing
- [ ] IteratorAgeMilliseconds drops to near 0 (Lambda caught up)
- [ ] DLQ has 0 messages (no permanent failures)
- [ ] `terraform state list` shows exactly 9 resources
- [ ] `terraform plan` shows **No changes**

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
