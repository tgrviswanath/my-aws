# Project 11.10 — Multi-Region VPC Architecture

## What This Does
Creates VPCs in two AWS regions (us-east-1 and us-west-2), connects them via
inter-region VPC peering, and tests cross-region private connectivity and latency.

## Architecture
```
us-east-1                          us-west-2
VPC-East (10.0.0.0/16)   ←→   VPC-West (10.1.0.0/16)
  Subnet (10.0.1.0/24)           Subnet (10.1.1.0/24)
  EC2-East                         EC2-West
       ↕  Inter-Region VPC Peering  ↕
  Route: 10.1.0.0/16 → pcx        Route: 10.0.0.0/16 → pcx
```

## Services Used
| Service | Role |
|---------|------|
| VPC (x2, different regions) | One per region |
| Inter-Region VPC Peering | Cross-region private connectivity |
| Route Tables (both regions) | Updated on both sides |
| EC2 (x2) | One per region for latency testing |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Inter-region peering | Same as same-region peering but crosses AWS backbone |
| Data transfer cost | Cross-region peering charges per GB (~$0.02/GB) |
| Latency | ~60-80ms between us-east-1 and us-west-2 |
| DNS resolution | Private DNS hostnames don't resolve across regions by default |
| No transitive routing | Same non-transitive rules apply |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Inter-region peering uses AWS backbone — more reliable than internet
- Data transfer costs apply — factor into architecture decisions
- For latency-sensitive workloads, consider Global Accelerator instead
- Route 53 private hosted zones don't span regions by default

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, cross-region latency test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/multiregion_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
