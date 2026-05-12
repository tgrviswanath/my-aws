# Architecture — Project 7.3 AWS X-Ray Distributed Tracing

## Trace Collection

```
ECS Task
    ├── Flask App Container
    │     │ aws-xray-sdk (Python)
    │     │ patch_all() → auto-instruments boto3, requests
    │     │
    │     │ Creates segment: "flask-api"
    │     │ Creates subsegments: DynamoDB.GetItem, DynamoDB.PutItem
    │     │
    │     │ Sends UDP packets to 127.0.0.1:2000
    │     ▼
    └── X-Ray Daemon Container (sidecar)
          │ Receives UDP packets
          │ Batches traces
          │ Sends to X-Ray API (HTTPS)
          ▼
    AWS X-Ray Service
          ├── Service Map (visual graph)
          ├── Trace storage (30 days)
          └── Analytics (aggregated stats)
```

## Trace Anatomy

```
Trace ID: 1-5f84c7a2-abc123...
  │
  └── Segment: flask-api (total: 120ms)
        ├── Subsegment: validate_input (2ms)
        ├── Subsegment: DynamoDB.GetItem (45ms)
        │     └── Table: handson-api-items
        │     └── Operation: GetItem
        │     └── Status: 200
        └── Subsegment: DynamoDB.PutItem (71ms)
              └── Table: handson-api-items
              └── Operation: PutItem
```

## Sampling Rules

```
Default: 5% of requests traced
  → 1,000 req/s → 50 traces/s

Custom rule (high-value endpoints):
  URLPath: /orders/*
  Rate: 100%  ← trace all order requests

Custom rule (health checks):
  URLPath: /health
  Rate: 0%    ← don't trace health checks (noise)
```
