# Architecture — Project 5.2 Multi-container Application

## Container Network Diagram

```
Browser
    │
    │ :3000
    ▼
┌──────────────────────────────────────────────────────────────┐
│                    Docker Network: app-network                │
│                                                               │
│  ┌──────────────┐    :3000    ┌──────────────────────────┐  │
│  │   Frontend   │ ──────────► │  Nginx serving React app  │  │
│  │  (node:20)   │             └──────────────────────────┘  │
│  └──────────────┘                                            │
│                                                               │
│  ┌──────────────┐    :4000    ┌──────────────────────────┐  │
│  │   Backend    │ ──────────► │  Express REST API         │  │
│  │  (node:20)   │             │  GET/POST /items          │  │
│  └──────┬───────┘             └──────────────────────────┘  │
│         │                                                     │
│    ┌────┴────┐                                               │
│    │         │                                               │
│    ▼         ▼                                               │
│  ┌──────┐  ┌───────┐                                        │
│  │  db  │  │ redis │                                        │
│  │MySQL │  │ Cache │                                        │
│  │:3306 │  │ :6379 │                                        │
│  └──────┘  └───────┘                                        │
│                                                               │
│  Volumes:                                                     │
│  mysql-data → /var/lib/mysql  (persistent)                   │
│  redis-data → /data           (persistent)                   │
└──────────────────────────────────────────────────────────────┘
```

## Caching Strategy

```
GET /items request
    │
    ├── Check Redis: GET items:all
    │       │
    │       ├── HIT  → return cached JSON (fast, ~1ms)
    │       │
    │       └── MISS → query MySQL
    │                   → store in Redis (TTL: 60s)
    │                   → return result
    │
POST /items (write)
    └── Insert to MySQL
        → DEL items:all from Redis (invalidate cache)
        → next GET will re-fetch from MySQL
```

## Service Dependencies

```
frontend
  depends_on: backend (healthy)

backend
  depends_on: db (healthy), redis (healthy)

db
  healthcheck: mysqladmin ping

redis
  healthcheck: redis-cli ping
```

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
