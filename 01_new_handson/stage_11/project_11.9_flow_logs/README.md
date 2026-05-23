# Project 11.9 — VPC Flow Logs Analysis

## What This Does
Enables VPC Flow Logs to capture all network traffic metadata. Stores logs in
CloudWatch Logs and S3. Queries logs with CloudWatch Insights and Athena to
identify traffic patterns and security issues.

## Architecture
```
VPC Traffic (all ENIs)
    ↓
Flow Logs (capture accepted + rejected)
    ├── CloudWatch Log Group  → CloudWatch Insights queries
    └── S3 Bucket             → Athena queries
```

## Services Used
| Service | Role |
|---------|------|
| VPC Flow Logs | Capture network traffic metadata |
| CloudWatch Logs | Store and query flow logs in real time |
| S3 | Long-term storage for flow logs |
| CloudWatch Insights | Query language for log analysis |
| Athena | SQL queries over S3-stored flow logs |
| IAM Role | Allows VPC to write logs to CloudWatch |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Flow log record | srcaddr, dstaddr, srcport, dstport, protocol, bytes, action |
| ACCEPT vs REJECT | ACCEPT = allowed by SG/NACL; REJECT = blocked |
| Aggregation interval | 1 min or 10 min — how often records are published |
| ENI-level logs | Can log at VPC, subnet, or individual ENI level |

## How to Deploy
```bash
cd terraform && terraform init && terraform apply
```

## Lessons Learned
- Flow logs capture metadata only — not packet contents
- REJECT records are gold for security troubleshooting
- CloudWatch Insights is fast for recent logs; Athena is better for historical analysis
- Flow logs have a ~10 minute delay before appearing in CloudWatch

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + Phase 4 CLI verification + Insights queries |
| `verify.md` | Console verification table, Terraform state checks, log record format check, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration |
| `code/flowlog_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
