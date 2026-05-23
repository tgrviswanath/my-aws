# Notes — Project 11.1

## Common Mistakes
- Forgetting to attach IGW to VPC → no internet even with route
- Forgetting to enable auto-assign public IP on subnet → EC2 gets no public IP
- Route table not associated with subnet → traffic still uses default route table

## Key CLI Commands
```bash
# Quick check: does subnet have public IP auto-assign?
aws ec2 describe-subnets --subnet-ids <id> \
  --query "Subnets[0].MapPublicIpOnLaunch"

# Quick check: does route table have IGW route?
aws ec2 describe-route-tables --route-table-ids <id> \
  --query "RouteTables[0].Routes"
```
