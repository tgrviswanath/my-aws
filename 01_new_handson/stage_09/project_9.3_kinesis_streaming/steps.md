# Steps — Project 9.3 Real-time Streaming Pipeline

## Phase 1 — Deploy

```bash
cd terraform
terraform init && terraform apply -auto-approve
STREAM=$(terraform output -raw stream_name)
echo "Stream: $STREAM"
```

---

## Phase 2 — Send Events (Producer)

```bash
pip install boto3
python3 src/producer.py
# Sends 50 events to Kinesis
```

---

## Phase 3 — Verify Lambda Processing

```bash
LAMBDA=$(terraform output -raw lambda_name)

# Tail Lambda logs
aws logs tail /aws/lambda/$LAMBDA --follow &

# Send more events
python3 src/producer.py

# Watch logs show processing
```

---

## Phase 4 — Check DynamoDB Aggregates

```bash
TABLE=$(terraform output -raw table_name)

aws dynamodb scan \
  --table-name $TABLE \
  --query "Items[*].{Product:pk.S,Hour:sk.S,Orders:order_count.N,Revenue:total_revenue.N}" \
  --output table
```

---

## Phase 5 — Monitor Stream Metrics

```bash
# Check shard iterator position
aws kinesis describe-stream-summary \
  --stream-name $STREAM \
  --query "StreamDescriptionSummary.{Shards:OpenShardCount,RetentionHours:RetentionPeriodHours}"

# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name IncomingRecords \
  --dimensions Name=StreamName,Value=$STREAM \
  --start-time $(date -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date --iso-8601=seconds) \
  --period 60 \
  --statistics Sum
```

---

## Screenshots to Take
- [ ] Kinesis stream created with 1 shard
- [ ] Producer sending events (terminal output)
- [ ] Lambda logs showing batch processing
- [ ] DynamoDB aggregates table with product totals
- [ ] CloudWatch showing IncomingRecords metric
- [ ] DLQ empty (no failed records)
