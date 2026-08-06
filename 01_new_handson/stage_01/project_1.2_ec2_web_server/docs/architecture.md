# Architecture — Project 1.2 Linux Web Server on EC2

## Diagram

```
Internet
    │
    │  port 80/443
    ▼
┌─────────────────────────────────────────────────────┐
│                  AWS Region (us-east-1)              │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           Security Group: web-server-sg       │   │
│  │                                               │   │
│  │  Inbound:  80  (HTTP)   → 0.0.0.0/0          │   │
│  │            443 (HTTPS)  → 0.0.0.0/0          │   │
│  │            22  (SSH)    → YOUR_IP/32 only     │   │
│  │  Outbound: All → 0.0.0.0/0                   │   │
│  │                                               │   │
│  │  ┌─────────────────────────────────────────┐ │   │
│  │  │         EC2: t3.micro                   │ │   │
│  │  │         Amazon Linux 2023               │ │   │
│  │  │                                         │ │   │
│  │  │  ┌─────────────────────────────────┐   │ │   │
│  │  │  │  Nginx (port 80)                │   │ │   │
│  │  │  │  Reverse proxy → localhost:8080 │   │ │   │
│  │  │  └────────────────┬────────────────┘   │ │   │
│  │  │                   │                     │ │   │
│  │  │  ┌────────────────▼────────────────┐   │ │   │
│  │  │  │  Backend App (port 8080)        │   │ │   │
│  │  │  │  Python / Node.js               │   │ │   │
│  │  │  └─────────────────────────────────┘   │ │   │
│  │  └─────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
    │
    │  port 22 (SSH)
    ▼
Your Machine (key-based auth only)
```

## Traffic Flow

```
Browser → EC2 Public IP:80
  → Nginx receives request
  → Nginx proxies to localhost:8080
  → Backend app responds
  → Nginx returns response to browser
```

## Security Model

| Rule | Why |
|------|-----|
| SSH restricted to your IP | Prevents brute force from internet |
| No password SSH | Key-based auth only |
| PermitRootLogin no | Principle of least privilege |
| Outbound all allowed | Instance needs to download packages |

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
