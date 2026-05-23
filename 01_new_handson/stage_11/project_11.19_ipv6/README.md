# Project 11.19 — IPv6 Implementation

## What This Does
Creates a dual-stack VPC (IPv4 + IPv6), configures IPv6 subnets and routing,
launches EC2 instances with IPv6 addresses, and tests IPv6 connectivity.
Also implements an Egress-Only Internet Gateway for private IPv6 outbound traffic.

## Architecture
```
VPC (10.0.0.0/16 + 2600:1f18:xxxx::/56)
├── Public Subnet  (10.0.1.0/24 + ::/64)
│     └── EC2 with IPv4 + IPv6
│           ↕ IPv6 via Internet Gateway (bidirectional)
└── Private Subnet (10.0.2.0/24 + ::/64)
      └── EC2 with IPv4 + IPv6
            ↕ IPv6 via Egress-Only IGW (outbound only)
```

## Services Used
| Service | Role |
|---------|------|
| Dual-stack VPC | Both IPv4 and IPv6 CIDR blocks |
| IPv6 Subnet | /64 block assigned from VPC /56 |
| Internet Gateway | IPv6 bidirectional for public subnet |
| Egress-Only IGW | IPv6 outbound-only for private subnet |
| Route Tables | Separate IPv6 routes (::/0) |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Dual-stack | VPC has both IPv4 and IPv6 CIDRs simultaneously |
| /56 VPC block | AWS assigns a /56 IPv6 CIDR to the VPC |
| /64 subnet block | Each subnet gets a /64 from the VPC /56 |
| Egress-Only IGW | Like NAT for IPv6 — outbound only, no inbound |
| No NAT for IPv6 | IPv6 addresses are globally unique — no NAT needed |
| Link-local | fe80::/10 — auto-assigned, not routable |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- IPv6 addresses are globally unique — no NAT, no private ranges
- Every IPv6-enabled instance gets a public IPv6 address — control access via SGs
- Egress-Only IGW replaces NAT Gateway for IPv6 private subnets (and it's free)
- AWS assigns the IPv6 CIDR — you cannot choose your own /56

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, EIGW inbound-block test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/ipv6_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
