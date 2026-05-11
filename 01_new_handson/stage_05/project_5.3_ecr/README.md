# Project 5.3 — Push Containers to ECR

## What This Does
Tags and pushes Docker images to Amazon ECR (Elastic Container Registry) — AWS's private container registry. Sets up lifecycle policies to manage image storage costs.

## Concepts Covered
| Concept | Description |
|---------|-------------|
| ECR repository | Private registry for your Docker images |
| Image tagging | `latest`, semantic versions, git SHA |
| ECR authentication | `aws ecr get-login-password` |
| Lifecycle policy | Auto-delete old images to save storage costs |
| Image scanning | ECR scans for CVEs on push |
| Cross-account access | Share images between AWS accounts |

## Tagging Strategy
```
ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPO:TAG

Tags used:
  :latest          ← always points to newest
  :1.0.0           ← semantic version
  :git-abc1234     ← git commit SHA (immutable)
  :2024-01-15      ← date-based
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output ecr_url
```

## Lessons Learned
- ECR authentication tokens expire after 12 hours — re-authenticate in CI/CD
- Use git SHA tags in production — `latest` is mutable and can cause confusion
- Lifecycle policies are critical — unmanaged ECR can accumulate thousands of images
- ECR image scanning is free and catches known CVEs — always enable it
- Use `--platform linux/amd64` when building on Apple Silicon (M1/M2) for Lambda/ECS compatibility
