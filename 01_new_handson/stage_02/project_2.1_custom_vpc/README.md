# Project 2.1 — Custom VPC Architecture

## What This Does
Builds a production-grade VPC from scratch with public and private subnets across two Availability Zones, Internet Gateway, NAT Gateway, and proper route tables.

## Architecture
```
VPC (10.0.0.0/16)
├── Public Subnet AZ-a  (10.0.1.0/24) → Web Tier
├── Public Subnet AZ-b  (10.0.2.0/24) → Web Tier
├── Private Subnet AZ-a (10.0.3.0/24) → App Tier
├── Private Subnet AZ-b (10.0.4.0/24) → App Tier
├── Private Subnet AZ-a (10.0.5.0/24) → DB Tier
└── Private Subnet AZ-b (10.0.6.0/24) → DB Tier
```

## Services Used
| Service | Role |
|---------|------|
| VPC | Isolated network boundary |
| Subnets | Segment network by tier and AZ |
| Internet Gateway (IGW) | Allow public subnets to reach internet |
| NAT Gateway | Allow private subnets to reach internet (outbound only) |
| Route Tables | Control traffic routing per subnet |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| CIDR | IP range notation — `10.0.0.0/16` = 65,536 IPs |
| Public subnet | Has route to IGW — resources can have public IPs |
| Private subnet | No route to IGW — resources are not directly reachable |
| NAT Gateway | Private resources can initiate outbound internet (e.g. yum update) |
| Route table | Rules that say "traffic to X goes via Y" |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Lessons Learned
- Always deploy subnets across at least 2 AZs for high availability
- NAT Gateway costs money — one per AZ for HA, or one shared for cost savings
- Default VPC is fine for learning but never use it in production
- CIDR planning matters — leave room to grow (use /16 for VPC, /24 for subnets)
- Private subnets need NAT to download packages — without it, EC2 can't reach the internet

## Code

### `code/vpc_checker.py` — Verify VPC architecture

```bash
pip install boto3

# Check a specific VPC
python code/vpc_checker.py --vpc-id vpc-0abc123def456789

# Use a specific AWS profile
python code/vpc_checker.py --vpc-id vpc-0abc123def456789 --profile my-profile
```

What it checks:
- VPC exists and is in `available` state
- Subnets classified as public (has IGW route) or private (has NAT route)
- Route tables — verifies IGW for public subnets, NAT for private
- Internet Gateway attachment status
- NAT Gateway state and subnet placement
- Security group inbound/outbound rules
- Prints a connectivity report summary
