# Architecture — Project 1.3 IAM Security Foundations

## IAM Entity Relationships

```
AWS Account
    │
    ├── Root User (use only for billing — never for daily work)
    │
    ├── IAM Users
    │   ├── admin-yourname  → AdministratorAccess (MFA required)
    │   ├── dev-user-01     → developers group
    │   └── de-user-01      → data-engineers group
    │
    ├── IAM Groups
    │   ├── developers      → EC2ReadOnly + S3ReadOnly
    │   ├── data-engineers  → S3FullAccess + GlueConsole
    │   └── ops             → EC2FullAccess + CloudWatch
    │
    ├── IAM Roles
    │   ├── ec2-s3-read-role     → assumed by EC2 instances
    │   ├── lambda-dynamo-role   → assumed by Lambda functions
    │   └── github-actions-role → assumed via OIDC
    │
    └── IAM Policies
        ├── AWS Managed  (maintained by AWS)
        └── Customer Managed (your custom policies)
```

## Permission Evaluation

```
Request arrives
    │
    ├── Is there an explicit DENY? → DENY (SCPs, permission boundaries)
    ├── Is there an explicit ALLOW? → ALLOW
    └── Default → DENY (implicit)

Effective permissions = IAM policy AND SCP (both must allow)
```

## Least Privilege Pattern

```
Bad:  Attach AdministratorAccess to every user
Good: Grant only the specific actions needed

Example — S3 read for specific bucket only:
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::my-specific-bucket",
    "arn:aws:s3:::my-specific-bucket/*"
  ]
}
```
