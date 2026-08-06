# Architecture — Project 5.1 Single-service Docker Application

## Multi-stage Build

```
Dockerfile
│
├── Stage 1: builder (python:3.11-slim)
│   ├── COPY requirements.txt
│   ├── pip install → /root/.local/
│   └── (discarded — not in final image)
│
└── Stage 2: runtime (python:3.11-slim)
    ├── Create non-root user (appuser)
    ├── COPY --from=builder /root/.local → /home/appuser/.local
    ├── COPY app/ → /app/
    ├── USER appuser
    └── CMD gunicorn app:app

Final image: ~120 MB (vs ~800 MB without multi-stage)
```

## Container Runtime

```
Docker Host
    │
    │ docker run -p 5000:5000
    ▼
┌──────────────────────────────────────────┐
│         Container: flask-api              │
│                                           │
│  Process: gunicorn (2 workers)            │
│  User: appuser (non-root, UID 999)        │
│  Port: 5000 (internal)                   │
│                                           │
│  /app/                                    │
│  ├── app.py                               │
│  └── requirements.txt                    │
│                                           │
│  Health: GET /health every 30s           │
└──────────────────────────────────────────┘
    │
    │ Port mapping: host:5000 → container:5000
    ▼
curl http://localhost:5000
```

## Dockerfile Best Practices Applied

| Practice | Implementation |
|----------|---------------|
| Multi-stage build | Separate builder and runtime stages |
| Non-root user | `useradd appuser`, `USER appuser` |
| Layer caching | `COPY requirements.txt` before `COPY .` |
| No secrets in image | `.dockerignore` excludes `.env` files |
| Health check | `HEALTHCHECK` instruction |
| Production server | gunicorn instead of Flask dev server |
| Pinned versions | `flask==3.0.3`, `gunicorn==22.0.0` |
| `PYTHONUNBUFFERED=1` | Logs appear immediately (no buffering) |

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
