# Project 9.3 — Real-time Streaming Pipeline

## What This Does
Builds a real-time data streaming pipeline: producers send events to Kinesis Data Streams, Lambda processes each event, and results land in S3 and Redshift for analysis.

## Architecture
```
Producer (app/script)
  → Kinesis Data Streams (buffer, 24h retention)
    → Lambda (process each record)
      → S3 (raw events, Parquet)
      → DynamoDB (real-time aggregates)
    → Kinesis Firehose (batch delivery)
      → S3 (compressed, partitioned)
      → Redshift (analytics)
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| Shard | Unit of capacity: 1 MB/s in, 2 MB/s out |
| Partition key | Routes records to specific shards |
| Sequence number | Unique ID per record within a shard |
| Checkpoint | Lambda tracks position in stream |
| Enhanced fan-out | Dedicated 2 MB/s per consumer |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output stream_name
```

## Lessons Learned
- Kinesis vs SQS: Kinesis = ordered, replay-able, multiple consumers; SQS = simpler, cheaper
- Shard capacity: 1 shard = 1,000 records/s or 1 MB/s — scale shards for throughput
- Lambda trigger: processes records in batches (up to 10,000 records per invocation)
- Bisect on error: Lambda splits failed batches to isolate bad records
- Enhanced fan-out: each consumer gets dedicated throughput — no sharing
