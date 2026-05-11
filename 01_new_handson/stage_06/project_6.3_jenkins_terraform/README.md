# Project 6.3 — Jenkins + Terraform Pipeline

## What This Does
Runs Jenkins on ECS Fargate and builds a Terraform CI/CD pipeline — the enterprise alternative to GitHub Actions. Covers Jenkinsfile declarative pipelines, shared libraries, and multi-branch pipelines.

## Architecture
```
GitHub webhook → Jenkins (ECS Fargate)
  → Checkout code
  → terraform fmt + validate
  → terraform plan (post as PR comment)
  → Manual approval gate
  → terraform apply
  → Notify Slack/email
```

## Why Jenkins (vs GitHub Actions)
| Feature | Jenkins | GitHub Actions |
|---------|---------|---------------|
| Hosting | Self-hosted (full control) | GitHub-managed |
| Cost at scale | Fixed (EC2/ECS) | Per-minute |
| Plugin ecosystem | 1,800+ plugins | Growing marketplace |
| Enterprise features | LDAP, SSO, audit logs | GitHub Enterprise |
| Customization | Unlimited | Limited to actions |
| Use case | Enterprise, regulated industries | Most modern teams |

## Key Files
```
project_6.3_jenkins_terraform/
├── README.md
├── steps.md
├── Jenkinsfile              ← declarative pipeline
├── jenkins/
│   ├── Dockerfile           ← Jenkins with Terraform + AWS CLI
│   └── plugins.txt          ← required plugins
├── terraform/
│   └── main.tf              ← Jenkins on ECS infrastructure
└── docs/
    └── architecture.md
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output jenkins_url
```

## Lessons Learned
- Jenkins on ECS Fargate: stateless Jenkins controller — jobs run in ephemeral agents
- Jenkinsfile `input` step: pauses pipeline for human approval before apply
- Shared libraries: reusable Groovy code across multiple Jenkinsfiles
- Blue Ocean: modern Jenkins UI — much better than classic UI
- Jenkins credentials store: use for AWS keys, not environment variables
