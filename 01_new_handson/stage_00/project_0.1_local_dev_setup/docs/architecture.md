# Architecture — Project 0.1 Local Cloud Development Setup

## Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Your Local Machine                    │
│                                                          │
│   AWS CLI / Terraform                                    │
│   (--endpoint-url=http://localhost:4566)                 │
│              │                                           │
│              ▼                                           │
│   ┌──────────────────────────────────────────────────┐  │
│   │              Docker Desktop                       │  │
│   │                                                   │  │
│   │   ┌───────────────────────────────────────────┐  │  │
│   │   │           LocalStack  :4566               │  │  │
│   │   │                                           │  │  │
│   │   │   ┌──────┐  ┌────────┐  ┌──────────┐    │  │  │
│   │   │   │  S3  │  │ Lambda │  │ DynamoDB │    │  │  │
│   │   │   └──────┘  └────────┘  └──────────┘    │  │  │
│   │   │                                           │  │  │
│   │   │   ┌─────────────┐  ┌──────────────────┐  │  │  │
│   │   │   │ API Gateway │  │ CloudWatch Logs  │  │  │  │
│   │   │   └─────────────┘  └──────────────────┘  │  │  │
│   │   └───────────────────────────────────────────┘  │  │
│   └──────────────────────────────────────────────────┘  │
│                                                          │
│   ✅ No real AWS account needed                          │
│   ✅ No costs                                            │
│   ✅ Safe to experiment                                  │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

1. Developer writes code or Terraform
2. AWS CLI / Terraform sends requests to `localhost:4566`
3. LocalStack intercepts and emulates the AWS service
4. Response returned as if it were real AWS
5. No traffic ever leaves your machine

## Key Concepts

| Concept | Explanation |
|---------|-------------|
| LocalStack | Open-source AWS emulator running in Docker |
| Endpoint override | `--endpoint-url=http://localhost:4566` redirects CLI to local |
| Fake credentials | `test/test` — LocalStack accepts any value |
| Port 4566 | Single port for all emulated AWS services |
