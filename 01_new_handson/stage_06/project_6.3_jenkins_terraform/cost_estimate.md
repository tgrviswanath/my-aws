# Cost Estimate — Project 6.3 Jenkins + Terraform Pipeline

## Local Docker (learning)
| Resource | Cost |
|----------|------|
| Local Docker container | $0 |
| **Total** | **$0** |

## Jenkins on ECS Fargate (if deployed to AWS)
| Resource | Monthly Cost |
|----------|-------------|
| Fargate (0.5 vCPU, 1 GB) | ~$15 |
| EFS for Jenkins home | ~$3 |
| ALB | ~$16 |
| **Total** | **~$34/month** |

## Notes
- For learning: run Jenkins locally in Docker — free
- For team use: deploy to ECS Fargate with EFS for persistent storage
- Jenkins agents (build workers) are ephemeral — only pay when builds run
