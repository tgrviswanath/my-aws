# Architecture — Project 7.3 AWS X-Ray Distributed Tracing

## Trace Flow

```
HTTP Request → ALB
    │
    │ X-Ray trace header injected: X-Amzn-Trace-Id
    ▼
ECS Task
  ├── Flask App Container
  │     │ aws-xray-sdk middleware
  │     │ Creates segment: "flask-api"
  │     │
  │     ├── Subsegment: "validate_input"
  │     ├── Subsegment: "DynamoDB.GetItem"  ← auto-patched
  │     └── Subsegment: "DynamoDB.PutItem"  ← auto-patched
  │
  └── X-Ray Daemon Container (sidecar)
        │ Receives UDP packets from SDK
        │ Batches and sends to X-Ray API
        ▼
    AWS X-Ray Service
        │
        ├── Service Map (visual graph)
        ├── Trace storage (30 days)
        └── Analytics (aggregated stats)
```

## ECS Task Definition with X-Ray Sidecar

```json
{
  "containerDefinitions": [
    {
      "name": "flask-api",
      "image": "ECR_URL:latest",
      "environment": [
        {"name": "AWS_XRAY_DAEMON_ADDRESS", "value": "127.0.0.1:2000"}
      ]
    },
    {
      "name": "xray-daemon",
      "image": "amazon/aws-xray-daemon:latest",
      "portMappings": [{"containerPort": 2000, "protocol": "udp"}],
      "command": ["--local-mode"]
    }
  ]
}
```

## Trace Anatomy

```
Trace ID: 1-5f84c7a2-abc123...
  │
  └── Segment: flask-api (100ms total)
        ├── Subsegment: validate_input (1ms)
        ├── Subsegment: DynamoDB.GetItem (45ms)
        │     └── Table: handson-api-items
        │     └── Operation: GetItem
        └── Subsegment: DynamoDB.PutItem (52ms)
```
