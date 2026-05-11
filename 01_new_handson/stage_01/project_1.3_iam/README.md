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

## Lessons Learned
- Never use root account for daily work — create an admin IAM user
- Attach policies to groups, not individual users
- Roles are for services (EC2, Lambda) — not for humans
- Use `aws:RequestedRegion` condition to restrict to specific regions
- IAM is global — not region-specific
