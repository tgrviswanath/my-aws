# Architecture — Project 4.5 SNS/SQS Microservices

## Fan-out Pattern

```
POST /orders
    │
    ▼
Order Lambda
    │
    │ sns.publish(order_event)
    ▼
┌─────────────────────────────────────────────────────────┐
│              SNS Topic: order-events                     │
│  One message published → all subscribers receive it     │
└──────────┬──────────────────┬──────────────────┬────────┘
           │                  │                  │
           ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │  SQS Queue  │   │  SQS Queue  │   │  SQS Queue  │
    │  inventory  │   │   email     │   │  analytics  │
    │             │   │             │   │             │
    │  DLQ ←──── │   │  DLQ ←──── │   │  DLQ ←──── │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                  │                  │
           ▼                  ▼                  ▼
    Inventory Lambda   Email Lambda    Analytics Lambda
    (update stock)     (send email)    (record metrics)
```

## Message Flow

```
1. Order placed → Lambda publishes to SNS
2. SNS delivers to all 3 SQS queues simultaneously
3. Each Lambda polls its own SQS queue
4. Lambda processes message
   ├── Success → message deleted from queue
   └── Failure → message becomes visible again after visibility timeout
                 → retried up to maxReceiveCount times
                 → then moved to DLQ
```

## SQS Configuration

| Setting | Value | Why |
|---------|-------|-----|
| Visibility timeout | 60s | > Lambda timeout (30s) |
| Message retention | 4 days | Time to investigate failures |
| Max receive count | 3 | Retry 3 times before DLQ |
| DLQ retention | 14 days | Time to investigate and replay |

## SNS vs SQS

| SNS | SQS |
|-----|-----|
| Push — delivers to subscribers | Pull — consumers poll |
| Fan-out (1 → many) | Point-to-point (1 → 1) |
| No persistence | Persists until consumed |
| Use for: notifications, fan-out | Use for: work queues, decoupling |

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
