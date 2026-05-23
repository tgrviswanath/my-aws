# Notes — Project 11.17

## ECS Exec (Container Shell Access)
To get a shell inside a running Fargate task:
```bash
# Enable ECS Exec on the service
aws ecs update-service --cluster cluster-11-17 \
  --service svc-web-11-17 \
  --enable-execute-command

# Execute command in running task
aws ecs execute-command \
  --cluster cluster-11-17 \
  --task <task-arn> \
  --container web \
  --interactive \
  --command "/bin/sh"
```
Requires: SSM agent in container image + IAM permissions for ecs:ExecuteCommand.

## Common Issues
- Tasks stuck in PENDING: check NAT Gateway exists (tasks need to pull images from ECR)
- Tasks STOPPED immediately: check CloudWatch logs for container exit reason
- Cloud Map not registering: check task role has `servicediscovery:RegisterInstance` permission
- ALB targets unhealthy: check SG allows ALB → task on container port

## IP Exhaustion Warning
If you see "no available IPs in subnet" errors:
- Your subnet is too small for the number of tasks
- Each task needs 1 IP + 1 for the ENI warm pool
- Solution: use larger subnets (/22 or /21) for task subnets
