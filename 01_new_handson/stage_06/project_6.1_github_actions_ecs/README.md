# Project 6.1 — GitHub Actions + ECS CI/CD

## What This Does
Builds a complete CI/CD pipeline using GitHub Actions that automatically tests, builds, pushes to ECR, and deploys to ECS Fargate on every merge to main.

## Pipeline Stages
```
Push to main branch
  → CI: lint + test + security scan
  → Build Docker image
  → Push to ECR (tagged with git SHA)
  → Deploy to ECS (rolling update)
  → Smoke test deployed service
  → Notify on success/failure
```

## Workflows
| File | Trigger | Purpose |
|------|---------|---------|
| `ci.yml` | Pull Request | Lint, test, build (no deploy) |
| `cd.yml` | Push to main | Build, push ECR, deploy ECS |
| `rollback.yml` | Manual trigger | Roll back to previous image |

## Key Concepts
| Concept | Description |
|---------|-------------|
| OIDC auth | Passwordless AWS auth (from Project 3.5) |
| Image tagging | Tag with git SHA for traceability |
| ECS force deploy | `--force-new-deployment` pulls latest image |
| Smoke test | Verify deployment succeeded before marking done |
| Rollback | Re-deploy previous git SHA on failure |

## How to Set Up
```bash
# 1. Create ECR repo and ECS cluster (from Projects 5.3 and 5.4)
# 2. Set up OIDC (from Project 3.5)
# 3. Add GitHub secrets (see steps.md)
# 4. Push to main — pipeline runs automatically
```

## Lessons Learned
- Tag images with git SHA, not just `latest` — enables precise rollbacks
- `aws ecs wait services-stable` blocks until deployment completes — use in CD pipeline
- Smoke tests after deploy catch issues before users do
- Use GitHub Environments for production deployments — adds manual approval gate
- Cache Docker layers in GitHub Actions using `cache-from` — speeds up builds significantly
