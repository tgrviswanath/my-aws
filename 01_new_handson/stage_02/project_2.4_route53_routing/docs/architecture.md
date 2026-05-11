# Architecture — Project 2.4 Route53 Advanced Routing

## Routing Policies Diagram

```
DNS Query: app.yourdomain.com
         │
         ▼
    Route53 Resolver
         │
    ┌────┴──────────────────────────────────────────┐
    │           Routing Policy Applied               │
    └────┬──────────────────────────────────────────┘
         │
    ┌────▼────────────────────────────────────────────────────────┐
    │                                                              │
    │  WEIGHTED (app.yourdomain.com)                               │
    │  ├── 90% → Primary EC2 (v1)                                  │
    │  └── 10% → Secondary EC2 (v2)  ← canary/A-B test            │
    │                                                              │
    │  FAILOVER (failover.yourdomain.com)                          │
    │  ├── PRIMARY → EC2 #1 (health check: /health)                │
    │  │   └── if UNHEALTHY → automatically switch to SECONDARY    │
    │  └── SECONDARY → EC2 #2 (passive standby)                    │
    │                                                              │
    │  LATENCY (latency.yourdomain.com)                            │
    │  ├── us-east-1 → EC2 in Virginia                             │
    │  └── eu-west-1 → EC2 in Ireland                              │
    │      Route53 picks lowest latency for each user              │
    └──────────────────────────────────────────────────────────────┘
```

## Failover Flow

```
Normal:
  User → DNS → Route53 → PRIMARY (healthy) → EC2 #1

Failure:
  EC2 #1 stops responding
  → Health check fails 3 times (90 seconds)
  → CloudWatch alarm fires → SNS → Email
  → Route53 automatically switches DNS to SECONDARY
  → User → DNS → Route53 → SECONDARY → EC2 #2

Recovery:
  EC2 #1 comes back
  → Health check passes
  → Route53 switches back to PRIMARY
```

## TTL Impact on Failover

| TTL | Failover Speed | DNS Query Cost |
|-----|---------------|----------------|
| 30s | ~2 minutes | Higher |
| 60s | ~3 minutes | Medium |
| 300s | ~8 minutes | Lower |

Use TTL=30 for critical failover scenarios.
