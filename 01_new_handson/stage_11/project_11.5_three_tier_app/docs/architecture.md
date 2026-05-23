# Architecture Notes — Project 11.5

## Why Per-AZ NAT Gateways?
If AZ-a fails and you only have one NAT in AZ-a, all private instances in AZ-b
lose internet access too. Per-AZ NAT Gateways ensure each AZ is self-sufficient.

## Subnet CIDR Planning
```
10.0.0.0/16  — VPC
  10.0.1.0/24  — web-public-a   (AZ-a)
  10.0.2.0/24  — web-public-b   (AZ-b)
  10.0.3.0/24  — app-private-a  (AZ-a)
  10.0.4.0/24  — app-private-b  (AZ-b)
  10.0.5.0/24  — db-private-a   (AZ-a)
  10.0.6.0/24  — db-private-b   (AZ-b)
  10.0.7-255.x — reserved for future tiers
```

## Traffic Isolation
- Web tier: internet-facing, public IPs
- App tier: internal only, outbound via NAT
- DB tier: internal only, outbound via NAT (for patches)
- App → DB: allowed on 3306 only
- Web → DB: BLOCKED (must go through app tier)
