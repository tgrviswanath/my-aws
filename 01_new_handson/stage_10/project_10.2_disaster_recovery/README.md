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

## Code

### `code/dr_failover.py` — Trigger and verify disaster recovery failover

```bash
pip install boto3

# Test DR readiness (non-destructive — checks replica lag, S3 replication)
python code/dr_failover.py test \
  --primary us-east-1 \
  --dr us-west-2

# Trigger failover (promotes RDS replica, updates Route53)
# WARNING: This redirects live traffic to the DR region!
python code/dr_failover.py failover \
  --primary us-east-1 \
  --dr us-west-2

# Failback after primary is restored
python code/dr_failover.py failback \
  --primary us-east-1 \
  --dr us-west-2
```

Actions:
| Action | What it does |
|--------|-------------|
| `test` | Checks RDS replica lag, S3 replication status, DR region readiness |
| `failover` | Promotes RDS read replica → primary, updates Route53 failover record |
| `failback` | Reverses failover after primary region is restored |

All actions are logged with timestamps for audit trail.
