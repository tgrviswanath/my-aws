# Architecture Notes — Project 11.15

## Shared VPC Pattern
```
Management/Network Account
  └── VPC (owns it, manages it)
        ├── Subnet A (shared via RAM)
        └── Subnet B (shared via RAM)
              ↓ RAM share
Dev Account                    Prod Account
  └── EC2 in Subnet A            └── EC2 in Subnet B
      (Dev owns EC2,                  (Prod owns EC2,
       Mgmt owns subnet)               Mgmt owns subnet)
```

## What Participant Accounts Can/Cannot Do
| Action | Participant Can | Participant Cannot |
|--------|----------------|-------------------|
| Launch EC2 in shared subnet | ✅ | |
| Create SGs in shared VPC | ✅ | |
| See shared subnet in console | ✅ | |
| Delete shared subnet | | ❌ |
| Modify VPC CIDR | | ❌ |
| Create subnets in shared VPC | | ❌ |

## Centralized DNS Pattern
One Route 53 PHZ in the network account.
Associate it with VPCs in all accounts.
All accounts resolve `*.internal.company.com` to the same records.
