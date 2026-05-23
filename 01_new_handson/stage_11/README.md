# Stage 11 — AWS VPC & Networking (20 Projects)

Complete hands-on learning path for AWS VPC and networking, from beginner to expert.
Every project has: README, steps (Console + CLI + Terraform), cost estimate,
Python checker script, architecture docs, and notes.

---

## Project Index

### 🟢 Beginner (11.1 – 11.4)
| # | Project | Key Skills |
|---|---------|-----------|
| 11.1 | [Basic VPC with Public Subnet](project_11.1_basic_vpc_public_subnet/) | VPC, IGW, route tables, EC2 |
| 11.2 | [Two-Tier Architecture + NAT](project_11.2_two_tier_nat/) | NAT Gateway, private subnets |
| 11.3 | [Security Groups Deep Dive](project_11.3_security_groups/) | SG chaining, least privilege |
| 11.4 | [Network ACLs Implementation](project_11.4_network_acls/) | Stateless rules, ephemeral ports |

### 🟡 Intermediate (11.5 – 11.9)
| # | Project | Key Skills |
|---|---------|-----------|
| 11.5 | [Three-Tier Web Application](project_11.5_three_tier_app/) | Multi-AZ, HA architecture |
| 11.6 | [Load Balancer Integration](project_11.6_load_balancer/) | ALB, target groups, health checks |
| 11.7 | [VPC Peering Connection](project_11.7_vpc_peering/) | Cross-VPC routing, non-transitive |
| 11.8 | [VPC Endpoints (Gateway & Interface)](project_11.8_vpc_endpoints/) | PrivateLink, S3/DynamoDB endpoints |
| 11.9 | [VPC Flow Logs Analysis](project_11.9_flow_logs/) | CloudWatch Insights, Athena queries |

### 🔴 Advanced (11.10 – 11.14)
| # | Project | Key Skills |
|---|---------|-----------|
| 11.10 | [Multi-Region VPC Architecture](project_11.10_multi_region_vpc/) | Inter-region peering, latency |
| 11.11 | [AWS Transit Gateway Hub](project_11.11_transit_gateway/) | Transitive routing, segmentation |
| 11.12 | [Site-to-Site VPN Connection](project_11.12_site_to_site_vpn/) | IPSec, strongSwan, hybrid cloud |
| 11.13 | [Direct Connect Simulation](project_11.13_direct_connect_sim/) | BGP, dynamic routing, Bird |
| 11.14 | [Network Firewall Implementation](project_11.14_network_firewall/) | Stateful inspection, domain blocking |

### 🟣 Expert (11.15 – 11.20)
| # | Project | Key Skills |
|---|---------|-----------|
| 11.15 | [Multi-Account Network Architecture](project_11.15_multi_account_network/) | RAM, shared VPC, centralized DNS |
| 11.16 | [Disaster Recovery Network](project_11.16_disaster_recovery/) | Route 53 failover, RTO/RPO |
| 11.17 | [Container Networking (ECS/EKS)](project_11.17_container_networking/) | awsvpc, Cloud Map, Fargate |
| 11.18 | [Network Performance Optimization](project_11.18_network_performance/) | ENA, placement groups, iperf3 |
| 11.19 | [IPv6 Implementation](project_11.19_ipv6/) | Dual-stack, EIGW, IPv6 routing |
| 11.20 | [Network Automation (IaC)](project_11.20_network_automation/) | Terraform modules, CDK, CFN |

---

## Each Project Contains

```
project_11.x_name/
├── README.md          — what it does, architecture, key concepts, lessons learned
├── steps.md           — Phase 1 Console | Phase 2 CLI | Phase 3 Terraform
│                        Phase 4 Verify  | Phase 5 Test | Verification Checklist
├── verify.md          — Console verification | CLI verification | Terraform state
│                        Health checks | Expected outputs | Verification checklist
├── cost_estimate.md   — per-resource cost breakdown + teardown command
├── code/
│   └── *_checker.py   — Python boto3 script to verify the setup programmatically
├── terraform/
│   ├── main.tf        — deployable Terraform configuration
│   ├── variables.tf
│   └── outputs.tf
├── docs/
│   └── architecture.md — traffic flows, comparisons, diagrams
└── notes/
    └── notes.md        — gotchas, troubleshooting, key commands
```

### verify.md covers (present in all 20 projects)

| Section | What it contains |
|---------|------------------|
| Console Verification | Exact navigation path, resource name, expected state + screenshot markers |
| Terraform State Verification | `terraform state list`, `terraform state show`, `terraform plan` no-drift check |
| Health Checks | Project-specific failure/recovery tests (NACL stateless proof, BGP withdrawal, RTO, etc.) |
| Expected Outputs | Actual JSON/text samples for every key CLI command and connectivity test |
| Verification Checklist | Final pass/fail checklist covering all resources and connectivity |

---

## Recommended Learning Sequence

| Week | Projects | Focus |
|------|----------|-------|
| Week 1 | 11.1 – 11.4 | VPC fundamentals, security |
| Week 2 | 11.5 – 11.9 | Production patterns, monitoring |
| Week 3 | 11.10 – 11.14 | Advanced connectivity, security |
| Week 4 | 11.15 – 11.20 | Enterprise, DR, automation |

---

## Quick Cost Reference

| Project | Cost for 2-hr lab |
|---------|------------------|
| 11.1 Basic VPC | ~$0.02 |
| 11.2 NAT Gateway | ~$0.09 |
| 11.5 Three-Tier (2x NAT) | ~$0.18 |
| 11.11 Transit Gateway | ~$0.46 |
| 11.12 Site-to-Site VPN | ~$0.15 |
| 11.14 Network Firewall | ~$0.88 |
| 11.16 Disaster Recovery | ~$1.19 |

**Always run `terraform destroy` after each lab.**
