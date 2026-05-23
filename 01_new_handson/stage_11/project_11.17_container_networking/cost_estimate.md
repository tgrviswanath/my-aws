# Cost Estimate — Project 11.17 Container Networking (ECS/EKS)

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| ECS Fargate (0.25 vCPU, 0.5 GB) x4 tasks | ~2 hrs | ~$0.02 |
| ALB | ~2 hrs | ~$0.02 |
| NAT Gateway x2 | ~2 hrs | ~$0.18 |
| Cloud Map namespace | 1 | $0 |
| Cloud Map DNS queries | ~1M | $0.40 |
| **Total (2-hr lab)** | | **~$0.62** |

## Full Monthly Cost (if left running)
| Resource | Monthly Cost |
|----------|-------------|
| 4x Fargate tasks (0.25 vCPU) | ~$14 |
| ALB | ~$16 |
| 2x NAT Gateway | ~$65 |
| Cloud Map | ~$1 |
| **Total** | **~$96/month** |

## Cost Tip
Fargate is priced per vCPU-second and GB-second.
For learning, use minimal sizes: 0.25 vCPU, 0.5 GB.
Scale to 0 tasks when not in use — you only pay for running tasks.

## Teardown
```bash
# Scale services to 0 first (stops billing for tasks)
aws ecs update-service --cluster cluster-11-17 --service svc-web-11-17 --desired-count 0
aws ecs update-service --cluster cluster-11-17 --service svc-api-11-17 --desired-count 0
# Then:
terraform destroy
```
