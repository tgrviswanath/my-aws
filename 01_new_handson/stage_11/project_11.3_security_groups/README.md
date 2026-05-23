# Project 11.3 — Security Groups Deep Dive

## What This Does
Creates multiple security groups for a three-tier setup and tests connectivity rules.
Demonstrates stateful behavior, SG chaining (referencing SGs in rules), and least privilege.

## Architecture
```
Internet → ALB SG (80/443) → Web SG (from ALB SG only)
                                   → App SG (from Web SG only)
                                         → DB SG (from App SG only, port 3306)
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Network boundary |
| Security Groups (4) | alb-sg, web-sg, app-sg, db-sg |
| EC2 (3 instances) | One per tier for connectivity testing |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Stateful | Return traffic is automatically allowed — no need for outbound rules |
| SG chaining | Reference another SG as source instead of a CIDR block |
| Least privilege | Only allow exactly what is needed, nothing more |
| Default deny | All traffic is denied unless explicitly allowed |
| Inbound vs Outbound | Inbound = traffic coming in; Outbound = traffic going out |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- SGs are stateful — if you allow inbound SSH, the response is automatically allowed
- Referencing SG IDs as sources is more secure than CIDR ranges (no IP management)
- You can attach multiple SGs to one instance
- SG changes take effect immediately — no reboot needed

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, connectivity matrix, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/sg_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
