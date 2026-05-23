# Notes — Project 11.3

## Key Takeaways
- Always use SG references (not CIDRs) for inter-tier rules — more secure and maintainable
- SG changes are instant — no restart needed
- You can have up to 5 SGs per ENI (network interface)
- Default outbound "allow all" is fine for most cases — restrict only if compliance requires it

## Testing Commands
```bash
# Test port connectivity from one EC2 to another
nc -zv <target-ip> <port>
# Example: nc -zv 10.0.2.15 3306

# Check which SGs are attached to an instance
aws ec2 describe-instances --instance-ids <id> \
  --query "Reservations[*].Instances[*].SecurityGroups"
```
