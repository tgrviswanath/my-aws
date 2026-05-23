# Project 11.1 — Basic VPC with Public Subnet

## What This Does
Creates a VPC from scratch with a single public subnet, Internet Gateway, and route table.
Launches an EC2 instance with a public IP and verifies internet connectivity.

## Architecture
```
VPC (10.0.0.0/16)
└── Public Subnet (10.0.1.0/24)  →  Internet Gateway  →  Internet
        └── EC2 Instance (public IP)
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Isolated network boundary |
| Subnet | Single public subnet |
| Internet Gateway (IGW) | Connects VPC to internet |
| Route Table | Routes 0.0.0.0/0 to IGW |
| EC2 | Test instance with public IP |
| Security Group | Allow SSH + HTTP inbound |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| VPC CIDR | IP range for the whole VPC — 10.0.0.0/16 = 65,536 IPs |
| Public subnet | Subnet with a route to an IGW; instances can get public IPs |
| Internet Gateway | One per VPC; horizontally scaled, no bandwidth limit |
| Route table | Rules that say "traffic to X goes via Y" |
| Auto-assign public IP | Subnet setting that gives EC2 a public IP on launch |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Lessons Learned
- A subnet is only "public" if its route table has a 0.0.0.0/0 → IGW route
- IGW must be attached to the VPC before any public traffic flows
- Auto-assign public IP must be enabled on the subnet OR set at instance launch
- Security groups are stateful — allow inbound SSH and return traffic is automatic
- Default VPC already has all this wired up — this project shows you how to do it manually

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, health checks, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/vpc_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
