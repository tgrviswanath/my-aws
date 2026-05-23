# Notes — Project 11.7

## Most Common Mistakes
- Creating peering but forgetting to update route tables on BOTH sides → no connectivity
- Overlapping CIDRs → peering creation fails entirely
- Security groups still blocking → peering works but traffic is dropped at SG level

## Quick Checks
```bash
# Is peering active?
aws ec2 describe-vpc-peering-connections \
  --filters "Name=status-code,Values=active"

# Does VPC-A have a route to VPC-B?
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_A" \
  --query "RouteTables[*].Routes[?VpcPeeringConnectionId!=null]"
```

## When to Use Peering vs Transit Gateway
- Peering: simple, 2-3 VPCs, low cost
- Transit Gateway: 4+ VPCs, hub-and-spoke, transitive routing needed
