# Project 11.6 — Load Balancer Integration

## What This Does
Deploys an Application Load Balancer (ALB) in public subnets distributing traffic
to web servers in an Auto Scaling Group. Tests health checks and failover.

## Architecture
```
Internet → ALB (public subnets, AZ-a + AZ-b)
               ↓  Target Group (HTTP 80)
         EC2 Web Servers (private subnets, AZ-a + AZ-b)
               ↓
         Health Check: GET /health → 200 OK
```

## Services Used
| Service | Role |
|---------|------|
| ALB | Layer 7 load balancer in public subnets |
| Target Group | Group of EC2 instances receiving traffic |
| Listener | ALB rule: HTTP 80 → forward to target group |
| Auto Scaling Group | Manages EC2 fleet across AZs |
| Health Checks | ALB monitors instance health |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| ALB | Layer 7 (HTTP/HTTPS) — can route by path, host, headers |
| Target Group | Logical group of targets (EC2, Lambda, IP) |
| Health Check | ALB polls /health every 30s — unhealthy instances removed |
| Sticky Sessions | Optional — route same user to same instance |
| Cross-zone LB | ALB distributes evenly across all AZs (enabled by default) |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- ALB must span at least 2 AZs
- Health check path must return 200 — misconfigured health checks = all instances unhealthy
- ALB DNS name changes — use Route 53 alias record, not hardcoded IP
- Security group for ALB must allow 80/443 from internet; web SG allows only from ALB SG

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, failover test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/alb_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
