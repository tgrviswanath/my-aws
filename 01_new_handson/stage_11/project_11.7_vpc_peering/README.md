# Project 11.7 — VPC Peering Connection

## What This Does
Creates two VPCs and connects them via VPC Peering. Configures route tables on both
sides so instances in each VPC can communicate as if on the same network.

## Architecture
```
VPC-A (10.0.0.0/16)          VPC-B (10.1.0.0/16)
  Subnet-A (10.0.1.0/24)  ←→  Subnet-B (10.1.1.0/24)
  EC2-A                         EC2-B
        ↕  VPC Peering Connection  ↕
  Route: 10.1.0.0/16 → pcx-xxx   Route: 10.0.0.0/16 → pcx-xxx
```

## Services Used
| Service | Role |
|---------|------|
| VPC x2 | Two isolated networks |
| VPC Peering Connection | Private link between VPCs |
| Route Tables (both VPCs) | Must be updated on BOTH sides |
| Security Groups | Must allow traffic from the other VPC's CIDR |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| VPC Peering | Non-transitive private connection between 2 VPCs |
| Non-transitive | A↔B and B↔C does NOT mean A↔C — need separate peering |
| CIDR overlap | Peered VPCs cannot have overlapping CIDRs |
| Route tables | Must add routes on BOTH sides — peering alone is not enough |
| Same/cross region | Works within a region and across regions |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Peering connection alone does nothing — you must update route tables on both sides
- Security groups must allow the other VPC's CIDR (or use SG references for same-account)
- CIDRs must not overlap — plan your CIDR ranges before creating VPCs
- Peering is not transitive — for hub-and-spoke use Transit Gateway instead

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, non-transitivity test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/peering_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
