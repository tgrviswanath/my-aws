# Architecture Notes — Project 11.2

## Traffic Flows
```
Outbound from private EC2:
  Private EC2 → private-rt (0.0.0.0/0 → NAT) → NAT GW → IGW → Internet

Inbound to web EC2:
  Internet → IGW → public-rt → public subnet → Web EC2

Private EC2 from internet:
  BLOCKED — no public IP, no IGW route
```

## NAT Gateway vs NAT Instance
| | NAT Gateway | NAT Instance |
|--|--|--|
| Managed | Yes | No |
| Cost | ~$32/mo | ~$3/mo (t3.nano) |
| Bandwidth | Up to 100 Gbps | Limited by instance |
| HA | Built-in | Manual |
| Use case | Production | Learning/dev |
