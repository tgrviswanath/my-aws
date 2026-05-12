# Architecture — Project 9.3 Real-time Streaming Pipeline

## Stream Architecture

```
Producer (Python script / app)
    │
    │ kinesis.put_record(StreamName, Data, PartitionKey)
    ▼
Kinesis Data Stream: handson-events
    ├── Shard 0: handles customer IDs C001-C500
    └── Shard 1: handles customer IDs C501-C999
    │
    │ Lambda polls shards automatically
    ▼
Lambda: handson-kinesis-consumer
    │
    ├── Decode base64 record
    ├── Parse JSON event
    ├── Aggregate by product/hour
    └── Write to DynamoDB (atomic ADD)
    │
    ▼
DynamoDB: handson-stream-aggregates
    └── {pk: "PRODUCT#Widget A", sk: "HOUR#2024-01-15T10:00:00Z",
          order_count: 42, total_revenue: 1259.58}
```

## Shard Capacity

```
1 shard = 1 MB/s ingest OR 1,000 records/s
        = 2 MB/s read

Scale shards when:
  - IncomingBytes > 800 KB/s (80% of 1 MB/s)
  - IncomingRecords > 800/s

aws kinesis update-shard-count \
  --stream-name handson-events \
  --target-shard-count 2
```

## Error Handling

```
Lambda processes batch of 100 records
    │
    ├── All succeed → batch deleted from stream
    │
    └── Some fail → bisect_batch_on_function_error = true
          ├── Split batch in half
          ├── Retry each half separately
          └── Failed records → SQS DLQ after max retries
```
