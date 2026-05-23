# Stage 00 — Prerequisites & Local Setup (4 Projects)

Foundation setup before any AWS hands-on work. No AWS costs incurred in projects 0.1–0.3.

---

## Project Index

| # | Project | Key Skills | Cost |
|---|---------|-----------|------|
| 0.1 | [Local Cloud Development Setup](project_0.1_local_dev_setup/) | Docker, LocalStack, AWS CLI, Terraform | Free |
| 0.2 | [Linux Foundations Lab](project_0.2_linux_lab/) | Linux, Nginx, permissions, cron, SSH | Free |
| 0.3 | [Git & GitHub Workflow](project_0.3_git_workflow/) | Git, branching, PRs, GitHub Actions | Free |
| 0.4 | [AWS Cost & Billing Fundamentals](project_0.4_billing/) | CloudWatch alarms, Budgets, Cost Explorer | ~$0 |

> ⚠️ Complete project 0.4 before starting any other AWS project — it sets up billing protection.

---

## Each Project Contains

```
project_0.x_name/
├── README.md        — what it does, tools used, lessons learned, file index
├── steps.md         — phase-by-phase implementation + screenshots checklist
├── verify.md        — tool/service verification, expected outputs, checklist
├── cost_estimate.md — per-resource cost breakdown
├── code/            — runnable scripts and demos
├── terraform/       — Terraform configuration (where applicable)
└── docs/
    └── architecture.md
```

### verify.md covers (present in all 4 projects)

| Section | What it contains |
|---------|------------------|
| Tool/Service Verification | Version checks, health checks, container status |
| CLI Verification | Commands with expected outputs for each resource |
| Terraform State Verification | `terraform state list`, `terraform plan` no-drift check |
| Script Verification | Expected output from demo/checker scripts |
| Verification Checklist | Final pass/fail checklist |

---

## Recommended Order

```
0.4 → 0.1 → 0.2 → 0.3
```

- Do **0.4 first** — sets up billing alerts before you spend anything
- Do **0.1** — gets your local toolchain working
- Do **0.2** — Linux skills needed for EC2 work in later stages
- Do **0.3** — Git workflow used for every project going forward

---

## Quick Cost Reference

| Project | Cost |
|---------|------|
| 0.1 Local Dev Setup | $0 — LocalStack runs locally |
| 0.2 Linux Lab | $0 — Docker only |
| 0.3 Git Workflow | $0 — Git/GitHub free |
| 0.4 Billing Setup | ~$0 — SNS + CloudWatch alarm within free tier |
