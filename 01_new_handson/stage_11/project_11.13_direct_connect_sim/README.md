# Project 11.13 — AWS Direct Connect Simulation

## What This Does
Simulates Direct Connect concepts using VPN + BGP routing. Since actual Direct Connect
requires physical hardware, this project uses a BGP-enabled VPN to demonstrate the
same routing concepts: dedicated path, BGP route advertisement, and failover.

## Architecture
```
"On-Premises" (simulated)              AWS
  EC2 + Bird BGP daemon          Virtual Private Gateway (VGW)
  BGP ASN: 65000                 BGP ASN: 64512
       ↕  VPN + BGP (IKEv2 + BGP over tunnel)  ↕
  Advertises: 192.168.0.0/16     Advertises: 10.0.0.0/16
```

## Services Used
| Service | Role |
|---------|------|
| Virtual Private Gateway | AWS-side BGP endpoint |
| Customer Gateway | On-premises BGP router (EC2 + Bird) |
| VPN Connection (BGP mode) | Tunnel carrying BGP session |
| Bird BGP daemon | Software BGP router on EC2 |
| Route Tables | BGP-propagated routes appear automatically |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| BGP | Border Gateway Protocol — dynamic routing protocol |
| ASN | Autonomous System Number — identifies each BGP peer |
| Route advertisement | BGP peers announce which CIDRs they own |
| Route propagation | VGW auto-adds BGP-learned routes to route tables |
| Failover | BGP withdraws routes when path fails — traffic reroutes |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- BGP over VPN is the closest simulation to Direct Connect without physical hardware
- Direct Connect uses the same BGP concepts but over a dedicated fiber connection
- BGP route preferences (MED, AS-PATH) control which path traffic prefers
- Direct Connect Gateway allows one DX connection to reach multiple VPCs/regions

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform + Bird BGP config + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, BGP route withdrawal test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/bgp_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
