# Architecture — Project 7.2 Centralized Logging Platform

## Log Pipeline

```
ECS Container (stdout/stderr)
    │ awslogs driver
    ▼
CloudWatch Logs: /ecs/handson-flask-api
    │ Subscription Filter (all logs, no filter pattern)
    ▼
Kinesis Firehose: handson-logs-stream
    │ Buffer: 5 MB or 60 seconds (whichever comes first)
    │
    ├── Primary destination: OpenSearch
    │   └── Index: ecs-logs-YYYY-MM-DD (daily rotation)
    │
    └── Backup: S3 (GZIP compressed, expire after 30 days)
          └── handson-firehose-backup/YYYY/MM/DD/HH/
```

## Kibana Query Examples

```
# Find all ERROR logs
@message: "ERROR" OR @message: "Exception"

# Find slow requests (> 1 second)
@message: "duration" AND duration_ms > 1000

# Find 5xx responses
@message: "500" OR @message: "502" OR @message: "503"

# Count by status code (aggregation)
terms aggregation on: status_code.keyword
```

## Index Lifecycle Management

```
ecs-logs-2024-01-15 (today — hot)
ecs-logs-2024-01-14 (yesterday — warm)
...
ecs-logs-2023-12-15 (30 days ago — delete)

ISM Policy:
  Day 0-7:   hot (frequent queries)
  Day 7-30:  warm (less frequent)
  Day 30+:   delete
```
