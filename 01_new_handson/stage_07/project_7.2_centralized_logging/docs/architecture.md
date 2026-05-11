# Architecture — Project 7.2 Centralized Logging Platform

## Log Flow

```
ECS Container (stdout/stderr)
    │
    │ awslogs driver
    ▼
CloudWatch Logs: /ecs/handson-flask-api
    │
    │ Subscription Filter (all logs)
    ▼
Kinesis Firehose: handson-logs-stream
    │ Buffer: 5 MB or 60 seconds
    │
    ├── Primary: OpenSearch index: ecs-logs-YYYY-MM-DD
    │
    └── Backup: S3 (GZIP compressed, expire after 30 days)
         handson-firehose-backup/YYYY/MM/DD/HH/
```

## Kibana Access

```
https://OPENSEARCH_ENDPOINT/_dashboards
  → Index pattern: ecs-logs-*
  → Discover: search and filter logs
  → Visualize: charts and graphs
  → Dashboard: combine visualizations
```

## Index Rotation

```
index_rotation_period = "OneDay"
→ Creates new index each day: ecs-logs-2024-01-15
→ Use wildcard pattern ecs-logs-* to query all days
→ Set ISM policy to delete indices older than 30 days
```
