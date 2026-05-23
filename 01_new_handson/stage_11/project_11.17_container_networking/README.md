# Project 11.17 — Container Networking (ECS/EKS)

## What This Does
Deploys an ECS Fargate cluster in a VPC and demonstrates container networking:
task-to-task communication, service discovery via Cloud Map, and ALB ingress.
Also covers EKS VPC CNI networking concepts.

## Architecture
```
VPC (10.0.0.0/16)
├── Public Subnets  → ALB (ingress)
└── Private Subnets → ECS Fargate Tasks
      ├── Service A (web)   ← ALB target group
      │     ↓ service discovery (web.local)
      └── Service B (api)   ← internal only
            ↓ Cloud Map DNS
      Service B: api.local → 10.0.x.x (task ENI)
```

## Services Used
| Service | Role |
|---------|------|
| ECS Fargate | Serverless container runtime |
| VPC CNI / awsvpc mode | Each task gets its own ENI and VPC IP |
| ALB | Ingress for web service |
| AWS Cloud Map | Service discovery (DNS-based) |
| Security Groups | Applied per-task (not per-host) |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| awsvpc network mode | Each ECS task gets its own ENI — full VPC networking |
| Task ENI | Task has a real VPC IP — SGs apply directly to the task |
| Cloud Map | Service registry — tasks register themselves, DNS resolves to task IPs |
| Service discovery | `api.local` resolves to healthy task IPs automatically |
| EKS VPC CNI | Same concept for Kubernetes — each pod gets a VPC IP |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- awsvpc mode means each task consumes a VPC IP — plan subnet size carefully
- Cloud Map health checks remove unhealthy tasks from DNS automatically
- ECS tasks in private subnets need NAT or VPC endpoints to pull images from ECR
- SGs on tasks are more granular than host-level SGs

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, service discovery test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/ecs_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
