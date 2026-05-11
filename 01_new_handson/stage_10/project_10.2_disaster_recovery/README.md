# Project 10.2 — Disaster Recovery Architecture

## What This Does
Implements cross-region disaster recovery for the production application. Covers RTO/RPO targets, automated failover, and regular DR testing.

## DR Strategies (cheapest to most expensive)
| Strategy | RTO | RPO | Cost |
|----------|-----|-----|------|
| Backup & Restore | Hours | Hours | Low |
| Pilot Light | 10-30 min | Minutes | Medium |
| Warm Standby | Minutes | Seconds | High |
| Multi-site Active/Active | Seconds | Near-zero | Very High |

## This Project: Warm Standby
```
Primary Region (us-east-1)
  ├── ECS Fargate (2 tasks)
  ├── RDS MySQL (Multi-AZ)
  └── S3 (versioned)

DR Region (us-west-2) — warm standby
  ├── ECS Fargate (1 task — scaled up on failover)
  ├── RDS Read Replica → promoted on failover
  └── S3 (cross-region replication)

Route53 Health Check → automatic DNS failover
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- RTO: Recovery Time Objective — how long can you be down?
- RPO: Recovery Point Objective — how much data can you lose?
- Test DR regularly — untested DR plans fail when you need them
- Automated failover: Route53 health checks + failover routing
- RDS promotion: read replica → primary takes ~5 minutes
- S3 CRR: cross-region replication has ~15 minute lag
