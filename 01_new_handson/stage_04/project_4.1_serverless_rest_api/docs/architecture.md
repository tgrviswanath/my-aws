# Architecture — Project 4.1 Serverless REST API

## Diagram

```
Client (curl / browser / app)
    │
    │ HTTPS request
    ▼
┌──────────────────────────────────────────────────────────┐
│                    AWS Cloud                              │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           API Gateway (HTTP API v2)                  │ │
│  │                                                       │ │
│  │  GET    /items       ─────────────────────────────┐  │ │
│  │  GET    /items/{id}  ─────────────────────────────┤  │ │
│  │  POST   /items       ─────────────────────────────┤  │ │
│  │  PUT    /items/{id}  ─────────────────────────────┤  │ │
│  │  DELETE /items/{id}  ─────────────────────────────┤  │ │
│  └───────────────────────────────────────────────────┼──┘ │
│                                                       │    │
│                                                       ▼    │
│  ┌────────────────────────────────────────────────────┐   │
│  │              Lambda: handler.py                     │   │
│  │  - Routes by method + path                          │   │
│  │  - Validates input                                  │   │
│  │  - Calls DynamoDB                                   │   │
│  │  - Returns JSON response                            │   │
│  │  Runtime: Python 3.11 | Timeout: 30s               │   │
│  └──────────────────────────┬─────────────────────────┘   │
│                             │                              │
│                             ▼                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │           DynamoDB: handson-api-items               │   │
│  │  Partition key: id (String)                         │   │
│  │  Billing: PAY_PER_REQUEST                           │   │
│  │  No provisioned capacity needed                     │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  CloudWatch Logs: /aws/lambda/handson-api-handler          │
└────────────────────────────────────────────────────────────┘
```

## Request Flow

```
POST /items {"name": "Widget"}
  → API Gateway receives request
  → Invokes Lambda with event payload
  → Lambda parses method=POST, path=/items
  → Validates body has "name" field
  → Generates UUID for item ID
  → Writes to DynamoDB
  → Returns 201 {"id": "uuid", "name": "Widget", ...}
  → API Gateway returns response to client
```

## HTTP API vs REST API

| Feature | HTTP API (v2) | REST API (v1) |
|---------|--------------|--------------|
| Price | ~$1/million | ~$3.50/million |
| Latency | Lower | Higher |
| Features | Core routing, CORS, JWT auth | Full feature set |
| Use case | Most APIs | Complex routing, API keys, usage plans |
| Recommendation | ✅ Use this | Only if you need v1 features |

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
