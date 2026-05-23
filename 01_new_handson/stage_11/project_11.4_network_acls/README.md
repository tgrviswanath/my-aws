# Project 11.4 — Network ACLs Implementation

## What This Does
Configures custom NACLs for public and private subnets. Demonstrates stateless behavior,
rule ordering, and how NACLs complement Security Groups for defense-in-depth.

## Architecture
```
VPC (10.0.0.0/16)
├── Public Subnet  → NACL-public  (allow HTTP/HTTPS/SSH in, ephemeral out)
└── Private Subnet → NACL-private (allow from public subnet only)
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Network boundary |
| Network ACLs (2) | Subnet-level stateless firewall |
| Subnets (2) | Public and private |
| EC2 (2) | Test connectivity |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Stateless | Must explicitly allow BOTH inbound AND return (outbound) traffic |
| Rule order | Rules evaluated lowest number first; first match wins |
| Ephemeral ports | Return traffic uses ports 1024–65535 — must allow outbound |
| Default NACL | Allows all traffic — custom NACLs deny all by default |
| Deny rules | Unlike SGs, NACLs support explicit DENY rules |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Forgetting ephemeral ports in outbound rules breaks all TCP connections
- NACLs apply to ALL traffic entering/leaving the subnet — including between instances
- Rule 100 DENY before rule 200 ALLOW means DENY wins
- Use NACLs to block specific IPs (e.g., known bad actors) — SGs can't deny

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, stateless behavior proof, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/nacl_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
