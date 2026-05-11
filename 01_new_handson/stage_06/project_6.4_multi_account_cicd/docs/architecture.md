# Architecture — Project 6.4 Multi-account CI/CD Pipeline

## Account Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                  AWS Organizations                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Management Account (CI/CD)                              │   │
│  │  - GitHub Actions runs here                              │   │
│  │  - ECR registry (shared)                                 │   │
│  │  - github-cd-role (OIDC)                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Dev Account  │  │Staging Acct  │  │  Prod Account        │  │
│  │              │  │              │  │                       │  │
│  │ ECS cluster  │  │ ECS cluster  │  │  ECS cluster         │  │
│  │ deploy-role  │  │ deploy-role  │  │  deploy-role         │  │
│  │ (trusts mgmt)│  │ (trusts mgmt)│  │  (trusts mgmt)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Cross-account Role Assumption

```
GitHub Actions (management account)
    │
    │ 1. OIDC → assume github-cd-role (management account)
    ▼
github-cd-role (management account)
    │
    │ 2. sts:AssumeRole → handson-dev-deploy-role (dev account)
    │    ExternalId: "handson-dev-deploy"
    ▼
handson-dev-deploy-role (dev account)
    │
    │ 3. Deploy to dev ECS
    ▼
Dev ECS Cluster
```

## Promotion Flow

```
develop branch push
    └── Auto-deploy to Dev

main branch push
    └── Auto-deploy to Staging
          └── Manual approval
                └── Deploy to Production
```

## Security Controls

| Control | Implementation |
|---------|---------------|
| Least privilege | Each deploy role has only ECS/ECR permissions |
| ExternalId | Prevents confused deputy attacks |
| Account isolation | Dev changes can't affect prod resources |
| Manual approval | Production requires human sign-off |
| Audit trail | CloudTrail logs all cross-account assumptions |
