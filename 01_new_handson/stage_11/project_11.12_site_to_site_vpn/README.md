# Project 11.12 — Site-to-Site VPN Connection

## What This Does
Simulates a hybrid cloud setup by creating a Site-to-Site VPN between an AWS VPC
and a simulated on-premises network (using a second VPC + strongSwan software VPN).

## Architecture
```
"On-Premises" (VPC-OnPrem 192.168.0.0/16)        AWS VPC (10.0.0.0/16)
  EC2 strongSwan (public IP)                         Virtual Private Gateway
       ↕  IPSec VPN Tunnel (IKEv2)  ↕
  Customer Gateway (CGW)          VPN Connection
  192.168.1.0/24                  10.0.1.0/24 (private subnet)
```

## Services Used
| Service | Role |
|---------|------|
| Virtual Private Gateway (VGW) | AWS-side VPN endpoint, attached to VPC |
| Customer Gateway (CGW) | Represents on-premises device (uses its public IP) |
| Site-to-Site VPN Connection | IPSec tunnel between VGW and CGW |
| strongSwan EC2 | Software VPN appliance simulating on-premises router |
| Route Tables | Propagate VPN routes automatically |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| VGW | AWS-managed VPN endpoint — highly available, two tunnels |
| CGW | Configuration object representing your on-premises device |
| Two tunnels | AWS always creates 2 tunnels for redundancy |
| Route propagation | VGW can auto-propagate on-premises routes to route tables |
| BGP vs Static | BGP for dynamic routing; static for simple setups |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- AWS always provides 2 VPN tunnels — configure both for HA
- VPN tunnel goes down if no traffic for 10 seconds — use DPD keepalives
- BGP is preferred over static routing for production
- strongSwan config must match AWS tunnel parameters exactly

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform + strongSwan config + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, IPSec encryption test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/vpn_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
