# Project 11.18 — Network Performance Optimization

## What This Does
Benchmarks and optimizes EC2 network performance using Enhanced Networking (ENA),
placement groups, and jumbo frames. Measures baseline vs optimized throughput
and latency using iperf3.

## Architecture
```
VPC (10.0.0.0/16)
└── Public Subnet (10.0.1.0/24)
      ├── EC2-A (c5n.large, ENA, placement group)  ← iperf3 server
      └── EC2-B (c5n.large, ENA, placement group)  ← iperf3 client
            ↕  Measure: throughput, latency, PPS
```

## Services Used
| Service | Role |
|---------|------|
| EC2 c5n.large | Network-optimized instance (up to 25 Gbps) |
| Enhanced Networking (ENA) | SR-IOV — bypasses hypervisor for lower latency |
| Placement Group (cluster) | Instances on same physical rack — lowest latency |
| Jumbo Frames (MTU 9001) | Larger packets = higher throughput |
| iperf3 | Network throughput benchmarking tool |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| ENA | Elastic Network Adapter — SR-IOV driver for high performance |
| Enhanced Networking | Enabled by default on modern instances (C5, M5, R5, etc.) |
| Placement Group (cluster) | Pack instances close together — up to 100 Gbps between them |
| Jumbo Frames | MTU 9001 vs default 1500 — reduces overhead for large transfers |
| Baseline vs burst | Some instances have baseline bandwidth + burst capability |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- ENA is enabled by default on modern instance types — no manual action needed
- Cluster placement groups give lowest latency but limit AZ flexibility
- Jumbo frames only help within a VPC — internet traffic is capped at MTU 1500
- Network performance scales with instance size — c5n.18xlarge = 100 Gbps

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, benchmark results, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/perf_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
| `notes/benchmark_results.md` | Recorded iperf3 and ping benchmark results |
