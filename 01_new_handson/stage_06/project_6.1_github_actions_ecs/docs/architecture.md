# Architecture — Project 6.1 GitHub Actions + ECS CI/CD

## Full Pipeline Flow

```
Developer
    │
    │ git push feature/my-change
    ▼
GitHub Repository
    │
    │ Pull Request opened
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  CI Workflow (ci.yml)                         │
│                                                               │
│  1. flake8 lint          ← fail on style errors              │
│  2. bandit security scan ← fail on HIGH severity             │
│  3. pytest + coverage    ← fail if tests fail                │
│  4. docker build         ← fail if build fails               │
│  5. trivy scan           ← fail on CRITICAL CVEs             │
└─────────────────────────────────────────────────────────────┘
    │
    │ PR approved + merged to main
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  CD Workflow (cd.yml)                         │
│                                                               │
│  1. OIDC → AWS temp credentials (no stored keys)             │
│  2. ECR login                                                 │
│  3. docker build --cache-from=gha (fast rebuild)             │
│  4. docker push :git-sha + :latest                           │
│  5. Update ECS task definition with new image                │
│  6. aws ecs deploy (rolling update)                          │
│  7. wait-for-service-stability (blocks until done)           │
│  8. curl /health × 5 (smoke test)                            │
│  9. Post summary to GitHub                                    │
└─────────────────────────────────────────────────────────────┘
    │
    │ If smoke test fails → manual rollback
    ▼
┌─────────────────────────────────────────────────────────────┐
│              Rollback Workflow (rollback.yml)                 │
│              Triggered manually with git SHA input           │
│                                                               │
│  1. Verify image exists in ECR                               │
│  2. Update task definition with old image                    │
│  3. Deploy (rolling update back to old version)              │
└─────────────────────────────────────────────────────────────┘
```

## Image Tagging Strategy

```
ECR: ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/handson-flask-api

Tags pushed on every merge:
  :abc1234  ← git SHA (immutable, used for rollback)
  :latest   ← always points to newest (mutable)

Never use :latest for rollback — use the git SHA tag.
```

## GitHub Secrets Required

| Secret | Value | Where to get |
|--------|-------|-------------|
| `AWS_ROLE_ARN` | IAM role ARN | `aws iam get-role --role-name github-actions-terraform` |
| `ALB_URL` | ALB DNS name | `terraform output alb_url` |
