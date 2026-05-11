# Project 3.5 — Terraform CI/CD Pipeline

## What This Does
Automates Terraform plan and apply using GitHub Actions with OIDC authentication (no stored AWS credentials). Pull requests show the plan; merges to main trigger apply.

## Workflow
```
Developer opens PR
  → GitHub Actions runs: terraform fmt, validate, plan
  → Plan output posted as PR comment
  → Reviewer approves PR
  → Merge to main
  → GitHub Actions runs: terraform apply
  → Infrastructure updated automatically
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| OIDC | Passwordless auth — GitHub gets temporary AWS credentials |
| IAM Role | GitHub Actions assumes this role via OIDC |
| Plan on PR | See exactly what will change before merging |
| Apply on merge | Infrastructure changes only go in via reviewed PRs |
| Drift detection | Scheduled plan to detect manual changes |

## Files
```
project_3.5_terraform_cicd/
├── README.md
├── steps.md
├── .github/
│   └── workflows/
│       ├── terraform-pr.yml     ← plan on pull request
│       ├── terraform-apply.yml  ← apply on merge to main
│       └── terraform-drift.yml  ← scheduled drift detection
├── terraform/
│   ├── main.tf
│   └── backend.tf
└── docs/
    └── architecture.md
```

## Lessons Learned
- OIDC is the correct way to authenticate GitHub Actions to AWS — never use long-lived access keys
- `terraform plan -out=plan.tfplan` saves the exact plan; apply uses that saved plan (no surprises)
- Post plan output as PR comment so reviewers can see what will change
- Use `terraform fmt -check` in CI to enforce formatting — fail the pipeline if not formatted
- Drift detection (scheduled plan) catches manual console changes before they cause problems
