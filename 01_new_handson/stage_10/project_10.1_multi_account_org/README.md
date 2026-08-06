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

## Code

### `code/org_manager.py` — Manage AWS Organizations accounts, OUs, and SCPs

```bash
pip install boto3

# List all accounts in the organization
python code/org_manager.py list-accounts

# List all SCPs and which OUs they're attached to
python code/org_manager.py list-scps

# Check compliance (required tags, Config enabled)
python code/org_manager.py check-compliance

# Use a specific profile (must have Organizations access)
python code/org_manager.py list-accounts --profile org-master
```

What it shows:
- All accounts with OU path, status, and tags
- SCP list with attachment targets
- Compliance check: required tags present, Config enabled per account
- Org tree structure

---

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription with required permissions | IAM user or role |
| Configuration | Resource settings | Region, names, sizes |
| Source Data | Files or code to deploy | Application source, data files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed and running services | AWS Console / CLI |
| Endpoints | Service URLs and connection strings | Resource overview page |
| Logs | Execution and audit logs | CloudWatch Logs |

## Quick Start
`ash
# Configure AWS CLI
aws configure

# Set region
export AWS_DEFAULT_REGION=us-east-1

# Create resource group
aws ec2 describe-regions --output table
`

## Lessons Learned
- Always tag AWS resources for cost tracking and organization
- Use IAM roles instead of access keys wherever possible
- Delete resources after learning to avoid unexpected charges
- Enable CloudWatch logging for all services in production
- Use the free tier for all lab exercises to minimize cost
