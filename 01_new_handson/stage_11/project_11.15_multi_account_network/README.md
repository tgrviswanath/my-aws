# Project 11.15 — Multi-Account Network Architecture

## What This Does
Implements enterprise-scale networking across multiple AWS accounts using AWS
Organizations, Resource Access Manager (RAM) for shared VPCs, and centralized
DNS with Route 53 private hosted zones.

## Architecture
```
AWS Organizations
├── Management Account
│     └── Shared Services VPC (10.0.0.0/16)
│           ├── Shared via RAM → Dev Account
│           └── Shared via RAM → Prod Account
├── Dev Account
│     └── Uses shared subnets from Management VPC
└── Prod Account
      └── Uses shared subnets from Management VPC

Route 53 Private Hosted Zone: internal.company.com
  → Associated with all VPCs across accounts
```

## Services Used
| Service | Role |
|---------|------|
| AWS Organizations | Group accounts, enable RAM sharing |
| Resource Access Manager (RAM) | Share VPC subnets across accounts |
| Shared VPC | Central VPC whose subnets are used by other accounts |
| Route 53 Private Hosted Zone | Centralized DNS across accounts |
| Transit Gateway (shared) | Cross-account connectivity hub |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Shared VPC | Owner account creates VPC; participant accounts launch resources in it |
| RAM | AWS Resource Access Manager — share resources across accounts |
| Participant account | Uses shared subnets but cannot modify the VPC itself |
| Centralized DNS | One Route 53 PHZ associated with VPCs in multiple accounts |
| Network account pattern | Dedicated account owns all networking; app accounts use it |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Shared VPC reduces VPC sprawl — one VPC serves many accounts
- Participant accounts see shared subnets in their console but cannot modify them
- Route 53 PHZ association across accounts requires authorization from the VPC owner
- Transit Gateway can also be shared via RAM for cross-account routing

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, cross-account DNS test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration (dual-provider) |
| `code/multiaccnt_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
