# Architecture — Project 0.2 Linux Foundations Lab

## Diagram

```
┌──────────────────────────────────────────────────┐
│                 Docker Host                       │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         ubuntu:22.04 Container              │ │
│  │                                             │ │
│  │  ┌──────────────────────────────────────┐  │ │
│  │  │  Nginx                               │  │ │
│  │  │  :80  → /var/www/html                │  │ │
│  │  │  :8080 → /opt/myapp/data             │  │ │
│  │  └──────────────────────────────────────┘  │ │
│  │                                             │ │
│  │  /opt/myapp/                                │ │
│  │  ├── config/  (appuser:appgroup, 640)       │ │
│  │  ├── data/    (web root)                    │ │
│  │  ├── logs/    (nginx + cron logs)           │ │
│  │  └── scripts/                               │ │
│  │                                             │ │
│  │  Users: root, appuser                       │ │
│  │  Groups: appgroup                           │ │
│  │  Cron: running every minute                 │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  ssh-server Container (Phase 8)             │ │
│  │  openssh-server running                     │ │
│  │  Key-based auth only                        │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Linux Permission Model

```
File: /opt/myapp/config/app.conf
Owner: appuser
Group: appgroup
Mode:  640

6 = rw-  (owner can read and write)
4 = r--  (group can read only)
0 = ---  (others have no access)
```

## Key Directories

| Path | Purpose |
|------|---------|
| `/etc/nginx/` | Nginx configuration |
| `/var/www/html/` | Default web root |
| `/var/log/nginx/` | Nginx access and error logs |
| `/opt/myapp/` | Custom application directory |
| `/etc/cron.d/` | System cron jobs |

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
