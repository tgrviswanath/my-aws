# Architecture — Project 6.2 Secure OIDC GitHub Authentication

## OIDC Token Flow

```
GitHub Actions Job
    │
    │ 1. Request OIDC token
    ▼
GitHub OIDC Provider
(token.actions.githubusercontent.com)
    │
    │ 2. Issue JWT containing:
    │    sub: "repo:org/repo:ref:refs/heads/main"
    │    aud: "sts.amazonaws.com"
    │    iss: "https://token.actions.githubusercontent.com"
    ▼
AWS STS: AssumeRoleWithWebIdentity
    │
    │ 3. Validate JWT signature against OIDC JWKS endpoint
    │ 4. Check trust policy conditions match JWT claims
    │ 5. Issue temporary credentials (1 hour)
    ▼
GitHub Actions uses temporary credentials
    │
    │ 6. Make AWS API calls
    ▼
AWS Services (ECR, ECS, etc.)
```

## Trust Policy Conditions Comparison

```
Most permissive (avoid):
  StringLike: "repo:org/repo:*"
  → Any branch, any event, any environment

Better (CI only):
  StringLike: "repo:org/repo:pull_request"
  → Only PR workflows

Best for CD (main branch):
  StringEquals: "repo:org/repo:ref:refs/heads/main"
  → Only main branch pushes

Most restrictive (production):
  StringEquals: "repo:org/repo:environment:production"
  → Only GitHub Environment "production" workflows
```

## Role Separation

```
github-ci-role
  Trust: any ref in repo
  Permissions: ECR read, ECS describe (read-only)
  Used by: ci.yml (PR checks)

github-cd-role
  Trust: main branch only
  Permissions: ECR push, ECS deploy
  Used by: cd.yml (deployment)

github-terraform-role
  Trust: production environment only
  Permissions: PowerUserAccess
  Used by: terraform-apply.yml
```
