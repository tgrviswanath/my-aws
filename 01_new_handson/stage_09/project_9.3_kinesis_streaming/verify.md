# Verification & Validation — Project 9.3 Real-time Streaming Pipeline

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Kinesis Stream | Kinesis → Data Streams | `handson-events` listed, Status = **Active** |
| Shards | Stream details → Shards tab | Shard count as configured |
| Lambda Trigger | Lambda → Functions → `handson-stream-processor` → Triggers | Kinesis trigger listed |
| Lambda Function | Lambda → Functions | `handson-stream-processor` exists |
| Kinesis Firehose | Kinesis → Delivery Streams | `handson-events-delivery` Status = **Active** |
| S3 Output | S3 → data lake bucket → raw/events/ | Event files appearing after producing |
| CloudWatch Metrics | CloudWatch → Metrics → Kinesis | `IncomingRecords`, `GetRecords.IteratorAgeMilliseconds` |

📸 Screenshot: Kinesis stream Active with shard metrics  
📸 Screenshot: Lambda function with Kinesis trigger  
📸 Screenshot: S3 raw/events/ showing delivered event files

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm stream exists and is active
aws kinesis describe-stream-summary \
  --stream-name handson-events \
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount,RetentionHours:RetentionPeriodHours}"
# Expected: Status=ACTIVE, Shards>=1, RetentionHours=24

# 2.2 Produce test events
export STREAM_NAME=handson-events
python src/producer.py
# Expected: "Sent 50 events to Kinesis" (or similar)

# 2.3 Verify records in stream
SHARD_ID=$(aws kinesis list-shards \
  --stream-name handson-events \
  --query "Shards[0].ShardId" --output text)
ITERATOR=$(aws kinesis get-shard-iterator \
  --stream-name handson-events \
  --shard-id $SHARD_ID \
  --shard-iterator-type TRIM_HORIZON \
  --query "ShardIterator" --output text)
aws kinesis get-records \
  --shard-iterator $ITERATOR \
  --limit 3 \
  --query "Records[*].{PartitionKey:PartitionKey,DataSize:Data}" \
  --output table
# Expected: records listed with partition keys

# 2.4 Check Lambda trigger is active
aws lambda list-event-source-mappings \
  --function-name handson-stream-processor \
  --query "EventSourceMappings[*].{Source:EventSourceArn,State:State,BatchSize:BatchSize}"
# Expected: State=Enabled, Source contains kinesis

# 2.5 Check Lambda invocations after producing
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=handson-stream-processor \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --query "Datapoints[*].Sum"
# Expected: Sum > 0 after producing events

# 2.6 Check iterator age (lag) — should be near 0
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --dimensions Name=StreamName,Value=handson-events \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Maximum \
  --query "Datapoints[*].Maximum"
# Expected: low value (near 0 = no lag)

# 2.7 Confirm Firehose delivery to S3
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
aws s3 ls s3://$BUCKET/raw/events/ --recursive | tail -5
# Expected: event files appearing
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_kinesis_stream.events
# aws_lambda_function.stream_processor
# aws_lambda_event_source_mapping.kinesis
# aws_kinesis_firehose_delivery_stream.events
# aws_iam_role.lambda
# aws_iam_role.firehose

terraform state show aws_kinesis_stream.events
# Shows: name=handson-events, shard_count, retention_period

terraform output stream_name
# Expected: handson-events

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — End-to-End Stream Flow

```bash
export STREAM_NAME=handson-events

# Step 1: Produce events
python src/producer.py
echo "✅ Events produced"

# Step 2: Wait for Lambda to process
sleep 15

# Step 3: Check Lambda logs for processing confirmation
LOG_GROUP="/aws/lambda/handson-stream-processor"
aws logs tail $LOG_GROUP --since 5m 2>/dev/null | head -20
# Expected: log lines showing records processed

# Step 4: Check S3 for Firehose delivery (wait 60s for buffer)
sleep 60
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
FILE_COUNT=$(aws s3 ls s3://$BUCKET/raw/events/ --recursive | wc -l)
echo "Event files in S3: $FILE_COUNT"
# Expected: > 0
```

---

## 5. Expected Successful Outputs

**CLI — describe-stream-summary:**
```json
{ "Status": "ACTIVE", "Shards": 1, "RetentionHours": 24 }
```

**producer.py output:**
```
Sent event 1/50: order_id=ORD-abc123, customer_id=CUST-1, amount=29.99
Sent event 2/50: order_id=ORD-def456, customer_id=CUST-2, amount=49.99
...
✅ 50 events sent to handson-events
```

**Lambda CloudWatch log:**
```
Processing batch of 10 records from shard shardId-000000000000
Processed order ORD-abc123: amount=29.99, customer=CUST-1
✅ Batch complete: 10 records processed
```

---

## 6. Verification Checklist

- [ ] Kinesis stream `handson-events` Status = ACTIVE
- [ ] Shard count matches configuration
- [ ] Retention period = 24 hours
- [ ] Lambda function `handson-stream-processor` exists
- [ ] Lambda Kinesis trigger State = Enabled
- [ ] `producer.py` sends events without error
- [ ] Lambda invocations metric > 0 after producing
- [ ] Iterator age near 0 (no processing lag)
- [ ] Firehose delivery stream Active
- [ ] Event files appear in S3 raw/events/ after 60 seconds
- [ ] `terraform plan` shows no changes
