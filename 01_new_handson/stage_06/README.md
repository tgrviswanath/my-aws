# Stage 06 — CI/CD Pipelines & GitOps (5 Projects)

Production-grade CI/CD pipelines using GitHub Actions, OIDC authentication, Jenkins,
multi-account deployments, and Kubernetes GitOps with ArgoCD. Builds on the ECS
infrastructure from Stage 05.

---

## Project Index

| # | Project | Key Services | Difficulty | Cost (2hr lab) |
|---|---------|-------------|-----------|----------------|
| 6.1 | [GitHub Actions + ECS CI/CD](project_6.1_github_actions_ecs/) | GitHub Actions, ECR, ECS, OIDC | 🟡 Intermediate | ~$0.05 |
| 6.2 | [Secure OIDC Authentication](project_6.2_oidc_auth/) | IAM OIDC, trust policies, CloudTrail | 🟡 Intermediate | ~$0.00 |
| 6.3 | [Jenkins + Terraform Pipeline](project_6.3_jenkins_terraform/) | Jenkins, Docker, Terraform, approval gates | 🟡 Intermediate | ~$0.05 |
| 6.4 | [Multi-Account CI/CD](project_6.4_multi_account_cicd/) | AWS Organizations, cross-account IAM, GitHub Environments | 🔴 Advanced | ~$0.10 |
| 6.5 | [Kubernetes GitOps + ArgoCD](project_6.5_kubernetes_gitops_argocd/) | EKS, ArgoCD, Kustomize, self-healing | 🔴 Advanced | ~$1.50 |

> ⚠️ Projects 6.1 and 6.3–6.5 depend on the ECR/ECS setup from Stage 05. Complete Stage 05 first.

---

## Each Project Contains

```
project_6.x_name/
├── README.md          — what it does, pipeline stages, key concepts, lessons learned
├── steps.md           — Setup/Deploy phases + Verification & Validation section
│                        Console checks | CLI commands | Functional tests
│                        Logs/monitoring | Expected outputs | Verification checklist
├── cost_estimate.md   — per-resource cost breakdown + teardown command
├── code/              — runnable scripts, deploy checks, OIDC setup helpers
├── terraform/         — Terraform configuration (where applicable)
└── docs/
    └── architecture.md
```

### Verification & Validation section in every steps.md covers

| Section | What it contains |
|---------|-----------------|
| AWS Console Verification | Exact navigation path, resource name, expected state |
| CLI Verification Commands | AWS CLI / kubectl / argocd commands with expected outputs |
| Functional Tests | End-to-end tests confirming the pipeline/deployment actually works |
| Logs & Monitoring Checks | CloudTrail, CloudWatch, GitHub Actions logs, error detection |
| Expected Successful Outputs | Table of checks and expected results |
| Verification Checklist | Pass/fail checklist to tick off as you go |

---

## Recommended Order

```
6.2 → 6.1 → 6.3 → 6.4 → 6.5
```

- **6.2 first** — OIDC auth is a prerequisite for 6.1 (passwordless AWS auth)
- **6.1** — full GitHub Actions CI/CD pipeline using OIDC from 6.2
- **6.3** — alternative CI/CD with Jenkins (no GitHub dependency)
- **6.4** — extends 6.1 to deploy across multiple AWS accounts
- **6.5** — Kubernetes GitOps (most complex — do last)

---

## Key Concepts Across Stage 06

| Concept | Project | Description |
|---------|---------|-------------|
| OIDC | 6.2 | Passwordless GitHub → AWS auth via JWT tokens |
| Git SHA tagging | 6.1 | Tag ECR images with commit SHA for traceability |
| Approval gates | 6.3, 6.4 | Human approval before production deployments |
| Cross-account roles | 6.4 | Management account assumes roles in target accounts |
| GitOps | 6.5 | Git is the single source of truth for cluster state |
| Self-healing | 6.5 | ArgoCD reverts manual changes to match Git |
| Drift detection | 6.5 | ArgoCD detects and corrects configuration drift |

---

## Quick Cost Reference

| Project | Key cost driver | Note |
|---------|----------------|------|
| 6.1 GitHub Actions + ECS | ECS tasks + ALB | Reuses Stage 05 infra |
| 6.2 OIDC Auth | IAM only | Free |
| 6.3 Jenkins | Docker (local) | Free locally |
| 6.4 Multi-Account | Multiple ECS clusters | ~$0.10 for 2hr lab |
| 6.5 EKS + ArgoCD | EKS cluster + nodes | ~$1.50 for 2hr lab |

**Always run `terraform destroy` after each lab. EKS is the most expensive — destroy immediately.**
