# Project 8.6 — Zero Trust Security Lab

## What This Does
Implements Zero Trust security principles in AWS: never trust, always verify. Every request is authenticated and authorized regardless of network location. Replaces VPN-based perimeter security.

## Zero Trust Principles Applied
| Principle | AWS Implementation |
|-----------|-------------------|
| Verify explicitly | Cognito + JWT on every API call |
| Least privilege access | IAM roles with minimal permissions |
| Assume breach | VPC Flow Logs + GuardDuty + CloudTrail |
| Micro-segmentation | Security groups per service, not per subnet |
| Device trust | AWS IAM Identity Center + MFA |
| Continuous monitoring | CloudWatch + Security Hub |

## Components
- IAM Identity Center (SSO) — centralized identity
- AWS Verified Access — zero-trust application access (no VPN)
- VPC Lattice — service-to-service auth without VPN
- IAM Roles Anywhere — extend IAM to on-premises workloads
- Private CA — internal certificate authority

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- Zero Trust is a mindset, not a product — it's implemented across many services
- AWS Verified Access: replaces VPN for internal app access — users authenticate with SSO
- VPC Lattice: service mesh for ECS/EKS — mutual TLS between services
- Never rely on network location for security — always authenticate at the application layer
- Micro-segmentation: each ECS service has its own security group — not shared

## Code

### `code/zero_trust_checker.py` — Audit AWS account for zero trust security

```bash
pip install boto3

# Run full zero trust audit
python code/zero_trust_checker.py

# Use a specific profile
python code/zero_trust_checker.py --profile security-audit
```

Checks performed:
| Check | What it looks for |
|-------|------------------|
| Root MFA | Root account has MFA enabled |
| User MFA | No IAM users without MFA |
| Public S3 | No S3 buckets with public access enabled |
| Open SSH/RDP | No security groups with `0.0.0.0/0` on port 22 or 3389 |
| Wildcard policies | No `*` action IAM policies attached directly to users |

Prints a zero trust score (0–100) with a list of findings and remediation steps.
