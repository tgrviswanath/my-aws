# Architecture — Project 2.1 Custom VPC

## Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AWS Region: us-east-1                              │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    VPC: 10.0.0.0/16  (handson-vpc)                   │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────┐    │ │
│  │  │   AZ: us-east-1a            │  │   AZ: us-east-1b            │    │ │
│  │  │                             │  │                             │    │ │
│  │  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │ │
│  │  │  │ Public Subnet         │  │  │  │ Public Subnet         │  │    │ │
│  │  │  │ 10.0.1.0/24           │  │  │  │ 10.0.2.0/24           │  │    │ │
│  │  │  │ [Web Tier]            │  │  │  │ [Web Tier]            │  │    │ │
│  │  │  │ NAT GW here ◄─EIP     │  │  │  │                       │  │    │ │
│  │  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │ │
│  │  │                             │  │                             │    │ │
│  │  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │ │
│  │  │  │ Private Subnet (App)  │  │  │  │ Private Subnet (App)  │  │    │ │
│  │  │  │ 10.0.3.0/24           │  │  │  │ 10.0.4.0/24           │  │    │ │
│  │  │  │ [App Tier]            │  │  │  │ [App Tier]            │  │    │ │
│  │  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │ │
│  │  │                             │  │                             │    │ │
│  │  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │ │
│  │  │  │ Private Subnet (DB)   │  │  │  │ Private Subnet (DB)   │  │    │ │
│  │  │  │ 10.0.5.0/24           │  │  │  │ 10.0.6.0/24           │  │    │ │
│  │  │  │ [DB Tier]             │  │  │  │ [DB Tier]             │  │    │ │
│  │  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │ │
│  │  └─────────────────────────────┘  └─────────────────────────────┘    │ │
│  │                                                                        │ │
│  │  Route Tables:                                                         │ │
│  │  public-rt:  0.0.0.0/0 → Internet Gateway                             │ │
│  │  private-rt: 0.0.0.0/0 → NAT Gateway                                  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                          │                                                  │
│                   Internet Gateway                                          │
└──────────────────────────┼──────────────────────────────────────────────── ┘
                           │
                        Internet
```

## Traffic Routing

```
Public subnet resource → Internet Gateway → Internet
Private subnet resource → NAT Gateway (in public subnet) → Internet Gateway → Internet
Internet → Private subnet: BLOCKED (no inbound route)
```

## CIDR Planning

| Subnet | CIDR | Usable IPs | Purpose |
|--------|------|-----------|---------|
| VPC | 10.0.0.0/16 | 65,531 | Entire network |
| public-a | 10.0.1.0/24 | 251 | Web tier AZ-a |
| public-b | 10.0.2.0/24 | 251 | Web tier AZ-b |
| private-app-a | 10.0.3.0/24 | 251 | App tier AZ-a |
| private-app-b | 10.0.4.0/24 | 251 | App tier AZ-b |
| private-db-a | 10.0.5.0/24 | 251 | DB tier AZ-a |
| private-db-b | 10.0.6.0/24 | 251 | DB tier AZ-b |
| Reserved | 10.0.7–255.x | ~64,000 | Future growth |
