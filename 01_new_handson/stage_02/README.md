# Stage 02 — Networking & High Availability (5 Projects)

Production-grade VPC architecture, multi-tier applications, load balancer comparison, advanced DNS routing, and failure simulation. Builds directly on the VPC from Project 2.1.

---

## Project Index

| # | Project | Key Services | Difficulty | Cost (2hr lab) |
|---|---------|-------------|-----------|----------------|
| 2.1 | [Custom VPC Architecture](project_2.1_custom_vpc/) | VPC, Subnets, IGW, NAT, Route Tables | 🟢 Beginner | ~$0.09 |
| 2.2 | [Multi-Tier Web Application](project_2.2_multi_tier_app/) | ALB, ASG, EC2, RDS, CloudFront | 🟡 Intermediate | ~$0.25 |
| 2.3 | [ALB vs NLB Comparison Lab](project_2.3_alb_vs_nlb/) | ALB, NLB, Target Groups | 🟡 Intermediate | ~$0.10 |
| 2.4 | [Route53 Advanced Routing](project_2.4_route53_routing/) | Route53, Health Checks, CloudWatch | 🟡 Intermediate | ~$0.05 |
| 2.5 | [Failure Simulation Lab](project_2.5_failure_simulation/) | VPC Flow Logs, SSM, CloudTrail, ASG | 🔴 Advanced | ~$0.20 |

> ⚠️ Projects 2.2–2.5 depend on the VPC created in Project 2.1. Do 2.1 first.

---

## Each Project Contains

```
project_2.x_name/
├── README.md        — what it does, services used, lessons learned, file index
├── steps.md         — Console | CLI | Terraform phases + screenshots checklist
├── verify.md        — Console verification | CLI checks | Terraform state
│                      Health checks | Expected outputs | Verification checklist
├── cost_estimate.md — per-resource cost breakdown
├── code/            — runnable scripts and demos
├── terraform/       — Terraform configuration
└── docs/
    └── architecture.md
```

### verify.md covers (present in all 5 projects)

| Section | What it contains |
|---------|------------------|
| Console Verification | Table with exact navigation path, resource name, expected state + screenshot markers |
| CLI Verification | Commands with expected JSON/text outputs for each resource |
| Terraform State Verification | `terraform state list`, `terraform state show`, `terraform plan` no-drift check |
| Health Checks | Project-specific tests (NAT internet test, ASG recovery, failover timing, chaos scenarios) |
| Expected Outputs | Actual JSON/text samples for every key command |
| Verification Checklist | Final pass/fail checklist per scenario |

---

## Recommended Order

```
2.1 → 2.2 → 2.3 → 2.4 → 2.5
```

- **2.1 first** — all other projects use this VPC
- **2.2** — deploys the full app stack into the VPC
- **2.3** — compare ALB vs NLB side by side (uses same VPC)
- **2.4** — add DNS routing on top of the deployed endpoints
- **2.5** — break and fix the environment from 2.2 (do last)

---

## Quick Cost Reference

| Project | Key cost driver | Note |
|---------|----------------|------|
| 2.1 Custom VPC | NAT Gateway ~$0.045/hr | Destroy after lab |
| 2.2 Multi-Tier App | ALB + EC2 + RDS | All free tier eligible |
| 2.3 ALB vs NLB | 2× LB hours | ~$0.008/hr each |
| 2.4 Route53 | Health checks ~$0.50/month | Delete after lab |
| 2.5 Failure Simulation | Reuses 2.2 resources | No extra cost |

**Always run `terraform destroy` after each lab.**
