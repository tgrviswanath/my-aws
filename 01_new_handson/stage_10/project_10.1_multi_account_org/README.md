# Project 10.1 — Multi-account AWS Organization

## What This Does
Sets up AWS Organizations with multiple accounts, Service Control Policies (SCPs) to enforce guardrails, and cross-account IAM for centralized access management.

## Account Structure
```
Root (Management Account)
  ├── Security OU
  │   └── Security Account (GuardDuty master, Security Hub aggregator)
  ├── Infrastructure OU
  │   └── Shared Services Account (ECR, Route53, shared VPC)
  ├── Workloads OU
  │   ├── Dev Account
  │   ├── Staging Account
  │   └── Prod Account
  └── Sandbox OU
      └── Developer Sandbox Accounts
```

## SCPs Applied
| SCP | Applies To | Effect |
|-----|-----------|--------|
| DenyRootUsage | All accounts | Block root account API calls |
| DenyRegionOutsideApproved | Workloads OU | Only us-east-1 and eu-west-1 |
| RequireEncryption | Workloads OU | Block unencrypted S3 buckets |
| DenyLeavingOrg | All accounts | Prevent accounts from leaving org |
| LimitEC2InstanceTypes | Dev OU | Only t3.micro and t3.small |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- SCPs are deny-only — they restrict what IAM policies can allow
- SCP + IAM = effective permissions (both must allow)
- Management account is exempt from SCPs — be careful with it
- AWS Control Tower: managed multi-account setup — use for enterprise
- Account vending machine: automate new account creation with Terraform
