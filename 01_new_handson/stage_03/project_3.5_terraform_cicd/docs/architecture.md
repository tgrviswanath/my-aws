# Architecture — Project 3.5 Terraform CI/CD Pipeline

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
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions: terraform-pr.yml            │
│                                                          │
│  1. terraform fmt -check    ← fail if not formatted      │
│  2. terraform validate      ← fail if syntax error       │
│  3. terraform plan          ← show what will change      │
│  4. Post plan as PR comment ← reviewer sees the diff     │
└─────────────────────────────────────────────────────────┘
    │
    │ PR reviewed and approved
    │ Merge to main
    ▼
┌─────────────────────────────────────────────────────────┐
│             GitHub Actions: terraform-apply.yml          │
│                                                          │
│  1. terraform init                                       │
│  2. terraform plan -out=plan.tfplan                      │
│  3. terraform apply plan.tfplan  ← exact saved plan      │
│  4. Post outputs to workflow summary                     │
└─────────────────────────────────────────────────────────┘
    │
    │ Infrastructure updated in AWS
    ▼
┌─────────────────────────────────────────────────────────┐
│             GitHub Actions: terraform-drift.yml          │
│             (runs daily at 8am UTC)                      │
│                                                          │
│  1. terraform plan -detailed-exitcode                    │
│     exit 0 = no changes (no drift)                       │
│     exit 2 = changes detected (DRIFT!)                   │
│  2. Alert if drift detected                              │
└─────────────────────────────────────────────────────────┘
```

## OIDC Authentication Flow

```
GitHub Actions Job
    │
    │ Request JWT token from GitHub OIDC provider
    ▼
GitHub OIDC Provider (token.actions.githubusercontent.com)
    │
    │ Issues JWT: "repo:user/repo:ref:refs/heads/main"
    ▼
AWS STS AssumeRoleWithWebIdentity
    │
    │ Validates JWT against OIDC provider
    │ Checks trust policy conditions (repo name match)
    │ Issues temporary credentials (1 hour)
    ▼
GitHub Actions uses temporary credentials
    │
    │ No long-lived access keys stored anywhere
    ▼
AWS API calls succeed
```

## Why OIDC Over Access Keys

| Access Keys | OIDC |
|-------------|------|
| Long-lived (never expire) | Short-lived (1 hour) |
| Stored as GitHub secrets | No secrets stored |
| Risk if leaked | Useless if intercepted |
| Manual rotation needed | Automatic |
| Can be used from anywhere | Tied to specific repo/branch |
