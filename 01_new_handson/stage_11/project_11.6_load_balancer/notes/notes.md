# Notes — Project 11.6

## Common Issues
- Health check fails → all instances show unhealthy → 503 from ALB
  Fix: ensure /health endpoint returns 200, check SG allows ALB → EC2 on port 80
- ALB shows "provisioning" for >5 min → check subnet has enough IPs (need /27 minimum)
- DNS not resolving → ALB takes 1-2 min to become active after creation

## Useful Commands
```bash
# Watch target health in real time
watch -n 5 'aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{ID:Target.Id,State:TargetHealth.State}"'

# Test load distribution
for i in $(seq 1 20); do curl -s http://$ALB_DNS | grep hostname; done | sort | uniq -c
```
