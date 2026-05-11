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
