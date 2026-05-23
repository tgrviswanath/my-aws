# Notes — Project 11.11

## TGW Creation Time
TGW takes 5-10 minutes to become available. Attachments take another 2-3 minutes.
Don't test connectivity until all attachments show "available".

## Common Mistakes
- Adding VPC routes before attachment is available → route creation fails
  Fix: use `depends_on` in Terraform or wait in console
- Forgetting to add routes in VPC route tables → TGW exists but traffic doesn't flow
- Using overlapping CIDRs across VPCs → TGW route table conflicts

## Segmentation Pattern
```bash
# Create isolated route table for VPC-C (no propagation from A/B)
aws ec2 create-transit-gateway-route-table --transit-gateway-id $TGW \
  --tag-specifications 'ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=isolated-rt}]'

# Associate VPC-C attachment with isolated RT (not default)
aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id $ISOLATED_RT \
  --transit-gateway-attachment-id $ATTACH_C
```
