# Project 6.2 — Secure OIDC GitHub Authentication

## What This Does
Deep-dives into OIDC (OpenID Connect) for passwordless GitHub → AWS authentication. Covers trust policy conditions, least-privilege scoping, multi-environment roles, and security hardening.

## Why OIDC Matters
```
Old way (dangerous):
  GitHub Secret: AWS_ACCESS_KEY_ID = AKIAIOSFODNN7EXAMPLE
  GitHub Secret: AWS_SECRET_ACCESS_KEY = wJalrXUtnFEMI/K7MDENG/...
  Problem: Long-lived credentials, leaked = full account compromise

OIDC way (secure):
  GitHub requests a short-lived JWT from GitHub's OIDC provider
  AWS validates the JWT and issues temporary credentials (1 hour)
  No secrets stored anywhere
  Credentials expire automatically
  Scoped to specific repo + branch + environment
```

## Trust Policy Conditions Covered
| Condition | Restricts to |
|-----------|-------------|
| `repo:org/repo:*` | Any ref in specific repo |
| `repo:org/repo:ref:refs/heads/main` | Only main branch |
| `repo:org/repo:environment:production` | Only production environment |
| `repo:org/repo:pull_request` | Only PR workflows |

## Roles Created
| Role | Scope | Permissions |
|------|-------|-------------|
| `github-ci-role` | PRs only | ECR read, ECS describe |
| `github-cd-role` | main branch only | ECR push, ECS deploy |
| `github-terraform-role` | main + environments | PowerUser |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output role_arns
```

## Lessons Learned
- Always scope OIDC trust to the most specific condition possible
- Separate CI role (read-only) from CD role (deploy) — principle of least privilege
- `environment:production` condition requires GitHub Environments to be configured
- OIDC tokens are valid for 1 hour — no rotation needed
- Audit OIDC usage in CloudTrail: look for `AssumeRoleWithWebIdentity` events
