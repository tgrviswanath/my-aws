# Project 11.11 — AWS Transit Gateway Hub

## What This Does
Creates a Transit Gateway as a central hub connecting three VPCs. Demonstrates
transitive routing, route table segmentation, and the hub-and-spoke model.

## Architecture
```
         Transit Gateway (TGW)
        /         |          \
   VPC-A       VPC-B        VPC-C
(10.0.0.0/16)(10.1.0.0/16)(10.2.0.0/16)
   EC2-A        EC2-B        EC2-C

All VPCs can reach each other via TGW (transitive routing)
```

## Services Used
| Service | Role |
|---------|------|
| Transit Gateway | Central routing hub |
| TGW Attachments | Connect each VPC to TGW |
| TGW Route Tables | Control which VPCs can talk to which |
| VPC Route Tables | Route traffic to TGW for cross-VPC destinations |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Transitive routing | A→TGW→B and B→TGW→C means A can reach C (unlike peering) |
| TGW Attachment | Connects a VPC (or VPN/Direct Connect) to the TGW |
| TGW Route Table | Controls routing between attachments |
| Route propagation | Attachments can auto-propagate their CIDRs to TGW route tables |
| Segmentation | Use multiple TGW route tables to isolate environments |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- TGW costs $0.05/hr + $0.02/GB — more expensive than peering but scales better
- One TGW can connect up to 5,000 VPCs
- TGW route tables enable network segmentation (e.g., prod cannot reach dev)
- TGW supports VPN and Direct Connect attachments too

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, transitivity test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/tgw_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
