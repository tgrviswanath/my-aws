# Kinesis — Real-World Use Cases

## Use Case 1: Real-Time Clickstream Analytics

**Business Problem**: Track every user click on the website in real-time. Detect trending products, user journeys, and anomalies within seconds.

```bash
# 1. Create Kinesis Data Stream
aws kinesis create-stream \
  --stream-name "clickstream" \
  --shard-count 4 \
  --stream-mode-details StreamMode=PROVISIONED

# Wait for stream to be active
aws kinesis wait stream-exists --stream-name "clickstream"

# 2. Get stream ARN
STREAM_ARN=$(aws kinesis describe-stream-summary \
  --stream-name "clickstream" \
  --query 'StreamDescriptionSummary.StreamARN' --output text)

echo "Stream ARN: $STREAM_ARN"
```

```python
# Producer: send click events from web app
import boto3
import json
import time

kinesis = boto3.client('kinesis', region_name='us-east-1')

def track_click(user_id: str, product_id: str, action: str, page: str):
    """Send click event to Kinesis."""
    event = {
        'userId':    user_id,
        'productId': product_id,
        'action':    action,       # 'view', 'add_to_cart', 'purchase'
        'page':      page,
        'timestamp': time.time(),
        'sessionId': get_session_id(),
    }

    kinesis.put_record(
        StreamName='clickstream',
        Data=json.dumps(event),
        PartitionKey=user_id  # Same user → same shard (ordered per user)
    )

# Batch producer (more efficient)
def track_clicks_batch(events: list[dict]):
    """Send multiple events in one API call (up to 500 records)."""
    records = [
        {'Data': json.dumps(e), 'PartitionKey': e['userId']}
        for e in events
    ]

    # Split into batches of 500
    for i in range(0, len(records), 500):
        batch = records[i:i+500]
        response = kinesis.put_records(
            StreamName='clickstream',
            Records=batch
        )
        failed = response['FailedRecordCount']
        if failed > 0:
            print(f"Warning: {failed} records failed to send")
```

```python
# Consumer: process clicks in real-time
import boto3
import json
import time

kinesis = boto3.client('kinesis')

def process_clickstream():
    """Read and process click events from all shards."""
    # Get all shards
    shards = kinesis.list_shards(StreamName='clickstream')['Shards']

    for shard in shards:
        shard_id = shard['ShardId']

        # Get iterator (LATEST = only new records)
        iterator = kinesis.get_shard_iterator(
            StreamName='clickstream',
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )['ShardIterator']

        while True:
            response = kinesis.get_records(
                ShardIterator=iterator,
                Limit=100
            )

            for record in response['Records']:
                event = json.loads(record['Data'])
                process_event(event)

            iterator = response['NextShardIterator']
            if not response['Records']:
                time.sleep(1)  # No records, wait before polling

def process_event(event: dict):
    """Aggregate clicks for trending products."""
    if event['action'] == 'view':
        # Increment view count in Redis
        r.zincrby('trending:products', 1, event['productId'])
        r.expire('trending:products', 3600)  # Reset hourly
```

**What you learn**: Kinesis producers/consumers, partition keys for ordering, batch puts, shard iterators.

---

## Use Case 2: Kinesis Firehose → S3 Data Lake

**Business Problem**: Ingest 1GB/hour of application logs into S3 automatically, with compression and partitioning by date.

```bash
# 1. Create Firehose delivery stream
aws firehose create-delivery-stream \
  --delivery-stream-name "app-logs-to-s3" \
  --delivery-stream-type DirectPut \
  --extended-s3-destination-configuration "{
    \"RoleARN\": \"arn:aws:iam::123456789:role/firehose-role\",
    \"BucketARN\": \"arn:aws:s3:::my-data-lake\",
    \"Prefix\": \"logs/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/\",
    \"ErrorOutputPrefix\": \"errors/logs/\",
    \"BufferingHints\": {
      \"SizeInMBs\": 128,
      \"IntervalInSeconds\": 300
    },
    \"CompressionFormat\": \"GZIP\",
    \"DataFormatConversionConfiguration\": {
      \"Enabled\": false
    },
    \"ProcessingConfiguration\": {
      \"Enabled\": true,
      \"Processors\": [{
        \"Type\": \"Lambda\",
        \"Parameters\": [{
          \"ParameterName\": \"LambdaArn\",
          \"ParameterValue\": \"arn:aws:lambda:us-east-1:123456789:function:log-transformer\"
        }]
      }]
    }
  }"

# 2. Send logs to Firehose (from application)
aws firehose put-record \
  --delivery-stream-name "app-logs-to-s3" \
  --record Data=$(echo '{"level":"ERROR","message":"DB connection failed","timestamp":"2024-01-15T10:30:00Z"}' | base64)

# 3. Batch send (more efficient)
aws firehose put-record-batch \
  --delivery-stream-name "app-logs-to-s3" \
  --records '[
    {"Data": "'"$(echo '{"level":"INFO","msg":"Request processed"}' | base64)"'"},
    {"Data": "'"$(echo '{"level":"ERROR","msg":"Timeout"}' | base64)"'"}
  ]'
```

```python
# Lambda transformer for Firehose (enrich/filter records)
import base64
import json

def handler(event, context):
    output = []
    for record in event['records']:
        # Decode
        payload = json.loads(base64.b64decode(record['data']))

        # Filter out DEBUG logs (reduce storage cost)
        if payload.get('level') == 'DEBUG':
            output.append({'recordId': record['recordId'], 'result': 'Dropped'})
            continue

        # Enrich with environment
        payload['environment'] = 'production'
        payload['service'] = 'order-api'

        # Re-encode
        output.append({
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(
                (json.dumps(payload) + '\n').encode()
            ).decode()
        })

    return {'records': output}
```

**What you learn**: Firehose buffering, dynamic partitioning, Lambda transformation, compression.

---

## Use Case 3: Change Data Capture (CDC) with Kinesis

**Business Problem**: Sync production PostgreSQL changes to a data warehouse in near-real-time (< 5 min lag).

```bash
# 1. Enable logical replication on RDS PostgreSQL
aws rds modify-db-parameter-group \
  --db-parameter-group-name "prod-postgres-params" \
  --parameters "ParameterName=rds.logical_replication,ParameterValue=1,ApplyMethod=pending-reboot"

# 2. Create Kinesis stream for CDC events
aws kinesis create-stream \
  --stream-name "db-changes" \
  --shard-count 2

# 3. Use Debezium (via MSK Connect or self-hosted) to capture changes
# Debezium produces events like:
# {
#   "op": "u",  // u=update, c=create, d=delete, r=read(snapshot)
#   "before": {"id": 1, "status": "pending"},
#   "after":  {"id": 1, "status": "shipped"},
#   "source": {"table": "orders", "ts_ms": 1705312245000}
# }

# 4. Lambda consumer: apply changes to Redshift
import boto3
import json
import psycopg2

def handler(event, context):
    for record in event['Records']:
        change = json.loads(record['kinesis']['data'])
        op = change['op']
        table = change['source']['table']
        after = change.get('after', {})
        before = change.get('before', {})

        if op == 'c':  # Create
            insert_to_redshift(table, after)
        elif op == 'u':  # Update
            upsert_to_redshift(table, after)
        elif op == 'd':  # Delete
            soft_delete_in_redshift(table, before['id'])
```

**What you learn**: CDC pattern, Debezium events, Kinesis as CDC transport, near-real-time sync.

---

## Use Case 4: Kinesis Analytics for Real-Time Aggregations

```sql
-- Kinesis Data Analytics (SQL) — count orders per minute
CREATE OR REPLACE STREAM "DESTINATION_SQL_STREAM" (
    window_start TIMESTAMP,
    window_end   TIMESTAMP,
    category     VARCHAR(50),
    order_count  INTEGER,
    total_revenue DOUBLE
);

CREATE OR REPLACE PUMP "STREAM_PUMP" AS
INSERT INTO "DESTINATION_SQL_STREAM"
SELECT STREAM
    STEP("SOURCE_SQL_STREAM".ROWTIME BY INTERVAL '1' MINUTE) AS window_start,
    STEP("SOURCE_SQL_STREAM".ROWTIME BY INTERVAL '1' MINUTE) + INTERVAL '1' MINUTE AS window_end,
    category,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue
FROM "SOURCE_SQL_STREAM"
WHERE status = 'completed'
GROUP BY
    category,
    STEP("SOURCE_SQL_STREAM".ROWTIME BY INTERVAL '1' MINUTE);
```

**What you learn**: Kinesis Analytics SQL, tumbling windows, real-time aggregations.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Too few shards | Throttling at high throughput | 1 shard = 1MB/s write, 2MB/s read |
| Using same partition key for all records | Hot shard, throttling | Use high-cardinality partition key (userId, orderId) |
| Not handling `ProvisionedThroughputExceededException` | Data loss | Implement retry with exponential backoff |
| Reading from TRIM_HORIZON always | Reprocesses all old data | Use LATEST for real-time, TRIM_HORIZON for backfill |
| Not monitoring `GetRecords.IteratorAgeMilliseconds` | Silent consumer lag | Alert when iterator age > 5 minutes |
| Firehose buffer too small | Too many S3 files | Set buffer to 128MB or 5 minutes |
