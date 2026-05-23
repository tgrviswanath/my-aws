# Architecture Notes — Project 11.7

## Non-Transitivity Explained
```
VPC-A ←→ VPC-B ←→ VPC-C
A cannot reach C — peering is point-to-point only.
For hub-and-spoke: use Transit Gateway (Project 11.11).
```

## CIDR Planning for Peering
Always plan CIDRs before creating VPCs:
- VPC-A: 10.0.0.0/16
- VPC-B: 10.1.0.0/16
- VPC-C: 10.2.0.0/16
- etc.
Overlapping CIDRs = peering impossible.

## Cross-Account Peering
Same process but the accepter must be in a different account.
The requester sends the request; the accepter logs in and accepts it.
