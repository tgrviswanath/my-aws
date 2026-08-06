# Steps — Project 9.3 Real-Time Streaming Pipeline
# PowerShell commands (Windows). Run from project root.

---

## Phase 0 — Setup Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming

$STREAM   = "handson-events"
$TABLE    = "handson-stream-aggregates"
$FUNCTION = "handson-kinesis-consumer"
$DLQ      = "handson-kinesis-dlq"
$REGION   = "us-east-1"
$ACCOUNT  = aws sts get-caller-identity --query Account --output text
Write-Host "Account: $ACCOUNT | Region: $REGION"
```

---

## Phase 1 — Deploy with Terraform

```powershell
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
# Type: yes

# Confirm outputs
terraform output stream_name     # handson-events
terraform output lambda_name     # handson-kinesis-consumer
terraform output table_name      # handson-stream-aggregates
terraform output tail_logs       # aws logs tail ... --follow
terraform output cost_per_hour   # $0.015/hr for 1 shard(s)
cd ..
```

---

## Phase 2 — Send Events (Producer)

```powershell
pip install boto3
python src/producer.py
# Sends 50 ORDER_PLACED events to handson-events
# Output: [1/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 4953...
```

---

## Phase 3 — Watch Lambda Logs in Real-Time

```powershell
# In a SEPARATE terminal — runs continuously until Ctrl+C
aws logs tail /aws/lambda/handson-kinesis-consumer --follow

# Then in original terminal, send more events:
python src/producer.py
# Watch logs appear: "Processing batch of 50 records" → "Batch complete: 50 records, 0 errors"
```

---

## Phase 4 — Check DynamoDB Aggregates

```powershell
aws dynamodb scan `
  --table-name $TABLE `
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" `
  --output table
# Revenue is in CENTS — divide by 100 for dollars
# Expected: up to 5 rows (Widget A/B/C, Gadget X/Y)
```

---

## Phase 5 — Read Directly from Kinesis Shard

```powershell
# Get shard ID
$SHARD_ID = aws kinesis list-shards `
  --stream-name $STREAM `
  --query "Shards[0].ShardId" --output text
Write-Host "Shard: $SHARD_ID"

# Get iterator (TRIM_HORIZON = read from beginning of 24h window)
$ITERATOR = aws kinesis get-shard-iterator `
  --stream-name $STREAM `
  --shard-id $SHARD_ID `
  --shard-iterator-type TRIM_HORIZON `
  --query "ShardIterator" --output text

# Read up to 10 records and decode the first one
$RESPONSE = aws kinesis get-records `
  --shard-iterator $ITERATOR `
  --limit 10 | ConvertFrom-Json

$RECORD = $RESPONSE.Records[0]
[System.Text.Encoding]::UTF8.GetString(
  [System.Convert]::FromBase64String($RECORD.Data)
) | ConvertFrom-Json | ConvertTo-Json
# Expected: {"event_id":"...","event_type":"ORDER_PLACED","product":"Widget A",...}
```

---

## Phase 6 — Monitor Stream Metrics

```powershell
# Stream summary
aws kinesis describe-stream-summary `
  --stream-name $STREAM `
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount,RetentionHours:RetentionPeriodHours}"
# Expected: ACTIVE, 1, 24

# IncomingRecords last 5 minutes
aws cloudwatch get-metric-statistics `
  --namespace AWS/Kinesis `
  --metric-name IncomingRecords `
  --dimensions Name=StreamName,Value=$STREAM `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Sum `
  --query "Datapoints[*].Sum"
# Expected: [50.0] after one producer run

# IteratorAge (should be near 0 = Lambda keeping up)
aws cloudwatch get-metric-statistics `
  --namespace AWS/Kinesis `
  --metric-name "GetRecords.IteratorAgeMilliseconds" `
  --dimensions Name=StreamName,Value=$STREAM `
  --start-time (Get-Date).AddMinutes(-5).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 300 --statistics Maximum `
  --query "Datapoints[*].Maximum"
# Expected: low value near 0
```

---

## Phase 7 — Verify DLQ (Should be Empty)

```powershell
$DLQ_URL = aws sqs get-queue-url --queue-name $DLQ --query "QueueUrl" --output text
aws sqs get-queue-attributes --queue-url $DLQ_URL `
  --attribute-names ApproximateNumberOfMessages `
  --query "Attributes.ApproximateNumberOfMessages"
# Expected: "0" — no failed records
```

---

## Phase 8 — Destroy (Always do this after learning)

```powershell
cd terraform
terraform destroy -var-file="terraform.tfvars"
# Type: yes
# Expected: Destroy complete! Resources: 9 destroyed.
cd ..
Remove-Item consumer.zip -ErrorAction SilentlyContinue
```

---

## Screenshots to Take

- [ ] Kinesis stream `handson-events` Active with shard count = 1
- [ ] Lambda `handson-kinesis-consumer` Triggers tab showing Kinesis trigger Enabled
- [ ] Terminal: `producer.py` sending 50 events with ShardId + SequenceNumber
- [ ] CloudWatch Logs: "Batch complete: 50 records, 0 errors"
- [ ] DynamoDB Explore items: product aggregates with order_count and total_revenue
- [ ] CloudWatch Kinesis metrics: IncomingRecords spike
- [ ] DLQ showing 0 messages
- [ ] `terraform apply` output — 9 resources created
- [ ] `terraform destroy` output — 9 resources destroyed
