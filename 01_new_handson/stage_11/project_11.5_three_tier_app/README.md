# Project 11.5 — Three-Tier Web Application

## What This Does
Builds a production-ready three-tier VPC: web tier (public), app tier (private),
database tier (private), across two Availability Zones for high availability.

## Architecture
```
VPC (10.0.0.0/16)
├── Public Subnets  AZ-a (10.0.1.0/24)  AZ-b (10.0.2.0/24)  → Web Tier
├── Private Subnets AZ-a (10.0.3.0/24)  AZ-b (10.0.4.0/24)  → App Tier
└── Private Subnets AZ-a (10.0.5.0/24)  AZ-b (10.0.6.0/24)  → DB Tier
         ↑ NAT Gateway in each public subnet for HA
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Isolated network |
| 6 Subnets | 2 per tier, spread across 2 AZs |
| 2 NAT Gateways | One per AZ for high availability |
| Internet Gateway | Public internet access |
| Route Tables | Public → IGW, Private → NAT (per AZ) |
| Security Groups | Per-tier access control |
| RDS (optional) | Database in DB subnets |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Multi-AZ | Resources in 2 AZs survive a single AZ failure |
| Per-AZ NAT | Each AZ has its own NAT — private instances stay in their AZ |
| DB Subnet Group | RDS requires subnets in at least 2 AZs |
| Tier isolation | Each tier only talks to adjacent tiers |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Two NAT Gateways cost double but are required for true HA
- DB subnet group needs subnets in 2+ AZs even for single-AZ RDS
- Always tag subnets with their tier — makes troubleshooting much easier
- Private subnets in different AZs need separate route tables (each pointing to their AZ's NAT)

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, AZ-affinity checks, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/three_tier_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
