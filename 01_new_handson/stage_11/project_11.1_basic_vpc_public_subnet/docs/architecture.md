# Architecture Notes — Project 11.1

## Traffic Flow
```
User Browser
    │
    ▼
Internet Gateway (igw-11-1)
    │  route: 0.0.0.0/0 → igw
    ▼
Public Subnet 10.0.1.0/24  (us-east-1a)
    │
    ▼
EC2 Instance (public IP assigned)
    └── Security Group: allow SSH/HTTP inbound
```

## Why This Matters
This is the simplest possible VPC setup. Every more complex project builds on these four components:
VPC → Subnet → IGW → Route Table.
