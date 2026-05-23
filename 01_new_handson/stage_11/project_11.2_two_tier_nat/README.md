# Project 11.2 — Two-Tier Architecture with NAT Gateway

## What This Does
Adds a private subnet to the VPC. A NAT Gateway in the public subnet lets private
instances reach the internet for updates while remaining unreachable from outside.

## Architecture
```
VPC (10.0.0.0/16)
├── Public Subnet  (10.0.1.0/24)  → IGW → Internet
│       └── NAT Gateway (Elastic IP)
│       └── Web Server EC2
└── Private Subnet (10.0.2.0/24)  → NAT GW → Internet (outbound only)
        └── Database / App EC2
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Isolated network |
| Public Subnet | Hosts web tier and NAT Gateway |
| Private Subnet | Hosts database / app tier |
| Internet Gateway | Public internet access |
| NAT Gateway | Outbound-only internet for private subnet |
| Route Tables | Public → IGW, Private → NAT |
| Security Groups | Tier-level access control |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| NAT Gateway | Translates private IPs to its own public IP for outbound traffic |
| Private subnet | No route to IGW — instances are not directly reachable |
| Outbound-only | Private instances can pull updates; internet cannot initiate connections |
| Elastic IP | Static public IP attached to NAT Gateway |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- NAT Gateway must live in a PUBLIC subnet (it needs IGW access)
- NAT Gateway costs ~$0.045/hr — destroy after learning
- Private subnet instances have no public IP — access via bastion or SSM
- One NAT Gateway can serve multiple private subnets

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, health checks, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/nat_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
