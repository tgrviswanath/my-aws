# Project 11.8 — VPC Endpoints (Gateway & Interface)

## What This Does
Creates Gateway endpoints for S3 and DynamoDB, and an Interface endpoint for SSM.
Demonstrates private AWS service access without traffic leaving the AWS network.

## Architecture
```
VPC (10.0.0.0/16)
├── Private Subnet (no NAT Gateway)
│       └── EC2 Instance
│             ↓ (private traffic only)
├── Gateway Endpoint → S3 (free, route-table based)
├── Gateway Endpoint → DynamoDB (free, route-table based)
└── Interface Endpoint → SSM (ENI in subnet, costs money)
```

## Services Used
| Service | Role |
|---------|------|
| VPC Gateway Endpoint | Private access to S3 and DynamoDB |
| VPC Interface Endpoint | Private access to SSM (Systems Manager) |
| Route Table | Gateway endpoint adds a prefix list route automatically |
| ENI | Interface endpoint creates a private IP in your subnet |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Gateway Endpoint | Free; works via route table prefix list; only S3 + DynamoDB |
| Interface Endpoint | Paid (~$7/mo/AZ); creates ENI; works for most AWS services |
| PrivateLink | Technology behind interface endpoints |
| Prefix List | AWS-managed list of S3/DynamoDB IP ranges used in route tables |
| No NAT needed | With endpoints, private instances reach S3/DynamoDB without NAT |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Gateway endpoints are free — always use them for S3/DynamoDB in private subnets
- Interface endpoints cost ~$7/month per AZ — only create what you need
- Without an endpoint, S3 traffic from a private subnet goes through NAT (costs money)
- Endpoint policies can restrict which S3 buckets are accessible

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, no-internet proof, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/endpoint_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
