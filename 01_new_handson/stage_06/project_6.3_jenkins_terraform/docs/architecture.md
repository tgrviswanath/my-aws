# Architecture — Project 6.3 Jenkins + Terraform Pipeline

## Pipeline Flow

```
GitHub Push/PR
    │
    │ Webhook
    ▼
Jenkins Controller (ECS Fargate or local Docker)
    │
    │ Checkout Jenkinsfile
    ▼
┌──────────────────────────────────────────────────────────┐
│                  Declarative Pipeline                     │
│                                                           │
│  Stage 1: Checkout    ← git clone                        │
│  Stage 2: Format      ← terraform fmt -check             │
│  Stage 3: Init        ← terraform init (S3 backend)      │
│  Stage 4: Validate    ← terraform validate               │
│  Stage 5: Plan        ← terraform plan -out=plan.tfplan  │
│  Stage 6: Approval    ← input() — human reviews plan     │  ← main only
│  Stage 7: Apply       ← terraform apply plan.tfplan      │  ← main only
│  Stage 8: Output      ← terraform output -json           │  ← main only
└──────────────────────────────────────────────────────────┘
    │
    │ post { success/failure/always }
    ▼
Notification (Slack/email)
```

## Branch Strategy

```
main branch:
  → Full pipeline: fmt → init → validate → plan → APPROVAL → apply

feature/* branches:
  → Partial pipeline: fmt → init → validate → plan (no apply)

PR to main:
  → Same as feature/* (plan only, no apply)
```

## Jenkins vs GitHub Actions Decision

```
Use Jenkins when:
  ✅ Self-hosted requirement (compliance, data residency)
  ✅ Complex approval workflows
  ✅ Integration with enterprise tools (LDAP, Jira, etc.)
  ✅ High volume builds (fixed cost vs per-minute)
  ✅ Existing Jenkins investment

Use GitHub Actions when:
  ✅ Modern cloud-native team
  ✅ Simple to moderate pipelines
  ✅ GitHub is your SCM
  ✅ Want minimal infrastructure to manage
  ✅ Starting fresh
```
