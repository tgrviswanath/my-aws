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

## How to Run
```bash
# 1. Set up OIDC role (from Project 6.2)
cd terraform && terraform init && terraform apply -auto-approve

# 2. Add GitHub secrets: AWS_ROLE_ARN, AWS_REGION
# 3. Push to a feature branch → PR triggers terraform plan
# 4. Merge to main → terraform apply runs automatically

# Trigger manually via Python
export GITHUB_TOKEN=ghp_your_token
python code/pipeline_trigger.py --repo myorg/my-repo --env dev
```

## Lessons Learned
- OIDC is the correct way to authenticate GitHub Actions to AWS — never use long-lived access keys
- `terraform plan -out=plan.tfplan` saves the exact plan; apply uses that saved plan (no surprises)
- Post plan output as PR comment so reviewers can see what will change
- Use `terraform fmt -check` in CI to enforce formatting — fail the pipeline if not formatted
- Drift detection (scheduled plan) catches manual console changes before they cause problems

## Code

### `code/pipeline_trigger.py` — Trigger and monitor GitHub Actions Terraform pipeline

```bash
pip install requests

# Set your GitHub token
export GITHUB_TOKEN=ghp_your_token_here

# Trigger the Terraform pipeline for dev environment
python code/pipeline_trigger.py --repo myorg/my-infra-repo --env dev

# Trigger for prod on a specific branch
python code/pipeline_trigger.py --repo myorg/my-infra-repo --env prod --ref main

# Use a custom workflow file name
python code/pipeline_trigger.py \
  --repo myorg/my-infra-repo \
  --env qa \
  --workflow deploy.yml
```

What it does:
- Triggers `workflow_dispatch` on the specified GitHub Actions workflow
- Polls until the new run appears in the API
- Streams status updates until the run completes
- Prints the run URL and final pass/fail result
- Exit code: `0` = success, `1` = failure

> Requires `GITHUB_TOKEN` with `actions:write` scope and the workflow must have `workflow_dispatch` trigger with an `environment` input.
