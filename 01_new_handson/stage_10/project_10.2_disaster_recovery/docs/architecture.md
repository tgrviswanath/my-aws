# Architecture — Project 10.2 Disaster Recovery Architecture

## Warm Standby Architecture

```
Primary Region (us-east-1)          DR Region (us-west-2)
─────────────────────────           ──────────────────────
ECS Fargate (2 tasks)               ECS Fargate (1 task — scaled up on failover)
RDS MySQL (Multi-AZ)  ──async──►   RDS Read Replica
S3 (versioned)        ──CRR──────► S3 (cross-region replica)
ALB                                 ALB (pre-configured)
Route53 health check                Route53 failover record
```

## Failover Sequence

```
Normal operation:
  Route53 → Primary (us-east-1) → ECS → RDS Primary

Failure detected:
  1. Route53 health check fails (3 consecutive failures × 30s = 90s)
  2. Route53 DNS switches to DR record (us-west-2)
  3. Traffic flows to DR region
  4. RDS read replica promoted to standalone primary (~5 min)
  5. ECS desired count scaled from 1 → 2 in DR region
  6. Service restored

Total RTO: ~10 minutes
RPO: ~60 seconds (RDS replication lag)
```

## RTO vs RPO Targets

| Strategy | RTO | RPO | Monthly Cost |
|----------|-----|-----|-------------|
| Backup & Restore | 4-8 hours | 24 hours | Low |
| Pilot Light | 30-60 min | Minutes | Medium |
| Warm Standby | 5-15 min | Seconds | High |
| Multi-site Active/Active | < 1 min | Near-zero | Very High |
