# Stage 05 — Containers & Managed Services (7 Projects)

Hands-on containerization from local Docker through ECR, ECS Fargate, blue-green
deployments, App Runner, and ElastiCache Redis. Each project builds on the previous.

---

## Project Index

| # | Project | Key Services | Difficulty | Cost (2hr lab) |
|---|---------|-------------|-----------|----------------|
| 5.1 | [Single-service Docker App](project_5.1_single_docker_app/) | Docker, Dockerfile, multi-stage build | 🟢 Beginner | ~$0.00 |
| 5.2 | [Multi-container Application](project_5.2_multi_container/) | Docker Compose, MySQL, Redis, networking | 🟢 Beginner | ~$0.00 |
| 5.3 | [Push Containers to ECR](project_5.3_ecr/) | ECR, lifecycle policies, image scanning | 🟢 Beginner | ~$0.01 |
| 5.4 | [ECS Fargate Deployment](project_5.4_ecs_fargate/) | ECS, Fargate, ALB, CloudWatch Logs | 🟡 Intermediate | ~$0.30 |
| 5.5 | [Blue-Green Deployment](project_5.5_blue_green/) | CodeDeploy, ECS, traffic shifting | 🟡 Intermediate | ~$0.35 |
| 5.6 | [AWS App Runner](project_5.6_app_runner/) | App Runner, auto-deploy, HTTPS | 🟡 Intermediate | ~$0.10 |
| 5.7 | [ElastiCache Redis Caching](project_5.7_elasticache_redis/) | ElastiCache, Redis, cache patterns | 🔴 Advanced | ~$0.20 |

> ⚠️ Projects 5.3–5.7 depend on the Docker image built in Project 5.1. Do 5.1 first.

---

## Each Project Contains

```
project_5.x_name/
├── README.md          — what it does, architecture, skills covered, lessons learned
├── steps.md           — Build/Deploy phases + Verification & Validation section
│                        Console checks | CLI commands | Functional tests
│                        Logs/monitoring | Expected outputs | Verification checklist
├── cost_estimate.md   — per-resource cost breakdown + teardown command
├── code/              — runnable scripts, cache patterns, demos
├── terraform/         — Terraform configuration (where applicable)
└── docs/
    └── architecture.md
```

### Verification & Validation section in every steps.md covers

| Section | What it contains |
|---------|-----------------|
| AWS Console Verification | Exact navigation path, resource name, expected state |
| CLI Verification Commands | AWS CLI / Docker commands with expected outputs |
| Functional Tests | End-to-end tests confirming the feature actually works |
| Logs & Monitoring Checks | CloudWatch, Docker logs, error detection |
| Expected Successful Outputs | Table of checks and expected results |
| Verification Checklist | Pass/fail checklist to tick off as you go |

---

## Recommended Order

```
5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7
```

- **5.1 first** — builds the Docker image used by all subsequent projects
- **5.2** — adds multi-container patterns (MySQL + Redis) locally
- **5.3** — pushes the image to ECR (required for 5.4, 5.5, 5.6)
- **5.4** — deploys to ECS Fargate (required for 5.5)
- **5.5** — adds blue-green deployment on top of 5.4
- **5.6** — alternative to ECS: App Runner (simpler, no VPC needed)
- **5.7** — adds ElastiCache Redis caching to the ECS deployment

---

## Quick Cost Reference

| Project | Key cost driver | Note |
|---------|----------------|------|
| 5.1 Single Docker | None (local only) | Free |
| 5.2 Multi-container | None (local only) | Free |
| 5.3 ECR | Storage ~$0.10/GB/month | Minimal for small images |
| 5.4 ECS Fargate | Fargate + ALB + NAT | ~$0.30 for 2hr lab |
| 5.5 Blue-Green | CodeDeploy + ECS + ALB | ~$0.35 for 2hr lab |
| 5.6 App Runner | ~$0.064/vCPU-hr | ~$0.10 for 2hr lab |
| 5.7 ElastiCache | cache.t3.micro ~$0.017/hr | ~$0.04 for 2hr lab |

**Always run `terraform destroy` after each lab.**
