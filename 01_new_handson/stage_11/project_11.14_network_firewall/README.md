# Project 11.14 — AWS Network Firewall Implementation

## What This Does
Deploys AWS Network Firewall in a dedicated firewall subnet. All traffic from
private subnets is inspected before reaching the internet. Implements stateful
rules to block specific domains and allow only approved traffic.

## Architecture
```
Internet
    ↕  IGW
Public Subnet (10.0.1.0/24)
    ↕  Route: 0.0.0.0/0 → Firewall Endpoint
Firewall Subnet (10.0.2.0/24)  ← AWS Network Firewall lives here
    ↕  Stateful inspection
Private Subnet (10.0.3.0/24)
    └── EC2 instances
```

## Services Used
| Service | Role |
|---------|------|
| AWS Network Firewall | Stateful/stateless traffic inspection |
| Firewall Policy | Container for rule groups |
| Stateless Rule Group | Fast packet filtering (5-tuple) |
| Stateful Rule Group | Deep inspection (domain filtering, Suricata rules) |
| Firewall Subnet | Dedicated subnet for firewall endpoints |
| Route Tables | Redirect traffic through firewall |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Firewall endpoint | ENI created in firewall subnet — traffic must route through it |
| Stateless rules | Fast, no connection tracking — like NACLs |
| Stateful rules | Connection-aware — like SGs but with domain filtering |
| Domain list | Block/allow specific FQDNs (e.g., block *.malware.com) |
| Suricata rules | IDS/IPS rules for deep packet inspection |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Traffic must be explicitly routed through the firewall endpoint — it doesn't intercept automatically
- Firewall endpoint ID changes per AZ — use VPC endpoint service for routing
- Domain filtering only works for HTTPS if TLS inspection is enabled
- Stateless rules are evaluated first, then stateful

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, firewall log checks, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/nfw_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
