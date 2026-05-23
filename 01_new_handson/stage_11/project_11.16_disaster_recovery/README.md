# Project 11.16 — Disaster Recovery Network

## What This Does
Builds a DR network across two regions. Primary region runs full infrastructure.
DR region runs a warm standby. Route 53 health checks trigger automatic DNS failover
when the primary region becomes unhealthy.

## Architecture
```
Primary Region (us-east-1)              DR Region (us-west-2)
VPC-Primary (10.0.0.0/16)              VPC-DR (10.1.0.0/16)
  ALB + EC2 fleet                         ALB + minimal EC2
  RDS Primary                             RDS Read Replica
       ↕  Cross-region replication  ↕
Route 53 Health Check → Primary ALB
  If unhealthy → failover → DR ALB
```

## Services Used
| Service | Role |
|---------|------|
| VPC (x2, different regions) | Primary and DR networks |
| Route 53 Health Check | Monitor primary endpoint |
| Route 53 Failover Routing | Auto-switch DNS to DR on failure |
| ALB (x2) | Load balancers in each region |
| Inter-region VPC Peering | Replication traffic path |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| RTO | Recovery Time Objective — how fast you recover |
| RPO | Recovery Point Objective — how much data you can lose |
| Warm standby | DR region runs minimal resources, scales up on failover |
| Pilot light | DR region has only core services running |
| Active-active | Both regions serve traffic simultaneously |
| Health check | Route 53 polls endpoint every 10-30s |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Route 53 health checks have a ~30-60s detection time
- DNS TTL must be low (60s) for fast failover
- RDS cross-region read replica has replication lag — RPO is not zero
- Test failover regularly — DR that has never been tested will fail when needed

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, RTO measurement script, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration (dual-region) |
| `code/dr_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
