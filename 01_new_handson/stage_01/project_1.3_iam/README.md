# Project 1.3 — IAM Security Foundations

## What This Does
Sets up IAM users, groups, roles, and policies following the principle of least privilege. Enables MFA.

## Services Used
- IAM (Users, Groups, Roles, Policies)
- STS (AssumeRole)

## Key Concepts
| Concept | Description |
|---------|-------------|
| User | A person or service with long-term credentials |
| Group | Collection of users sharing the same permissions |
| Role | Temporary credentials assumed by services or users |
| Policy | JSON document defining what actions are allowed/denied |
| Least privilege | Grant only the minimum permissions needed |

## Tasks Covered
- Create IAM users and groups
- Attach policies to groups (not users directly)
- Create EC2 instance role with S3 read access
- Restrict S3 access to specific bucket
- Enable MFA for admin user
- Test permission boundaries

## How to Run
```bash
cd terraform && terraform init && terraform apply -auto-approve

# Or use the automation script
pip install boto3
python code/iam_setup.py --dry-run   # preview changes
python code/iam_setup.py             # apply
```

## Lessons Learned
- Never use root account for daily work — create an admin IAM user
- Attach policies to groups, not individual users
- Roles are for services (EC2, Lambda) — not for humans
- Use `aws:RequestedRegion` condition to restrict to specific regions
- IAM is global — not region-specific

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + permission boundary tests |
| `verify.md` | Console verification table, CLI checks, permission denied tests, Terraform state, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — users, groups, roles, policies, instance profile |
| `code/iam_setup.py` | Python script — creates users, groups, roles via boto3 |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `code/iam_setup.py` — Automate IAM users, groups, and roles

```bash
# Install dependencies
pip install boto3

# Dry run first — see what will be created without making changes
python code/iam_setup.py --dry-run

# Apply changes
python code/iam_setup.py

# Use a specific AWS profile
python code/iam_setup.py --profile admin-profile
```

What it creates:
| Resource | Name | Permissions |
|----------|------|-------------|
| Group | `developers` | S3 ReadOnly + EC2 ReadOnly |
| Group | `readonly` | AWS ReadOnlyAccess |
| User | `dev-user-1` | Added to developers group |
| User | `dev-user-2` | Added to developers group |
| User | `readonly-user-1` | Added to readonly group |
| Role | `ec2-s3-access-role` | S3 FullAccess (for EC2 instances) |
| Instance Profile | `ec2-s3-access-role-profile` | Wraps the EC2 role |
