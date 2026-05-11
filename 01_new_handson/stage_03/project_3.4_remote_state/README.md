# Project 3.4 — Terraform Remote State

## What This Does
Moves Terraform state from a local file to S3 (with DynamoDB locking), enabling team collaboration, state sharing between configs, and safe concurrent operations.

## Why Remote State Matters
| Problem (local state) | Solution (remote state) |
|----------------------|------------------------|
| State file on your laptop only | Stored in S3 — accessible to whole team |
| Two people apply at same time → corruption | DynamoDB lock prevents concurrent applies |
| Config A can't read Config B's outputs | `terraform_remote_state` data source |
| State lost if laptop dies | S3 versioning keeps history |
| Secrets visible in local file | S3 encryption at rest |

## Architecture
```
terraform apply
  → acquires DynamoDB lock
  → reads/writes state in S3
  → releases DynamoDB lock
```

## Key Topics
- S3 backend configuration
- DynamoDB state locking
- State migration (local → remote)
- `terraform_remote_state` data source
- State workspace strategy
- `terraform import` for existing resources

## How to Deploy
```bash
# Step 1: Create the S3 bucket and DynamoDB table (bootstrap)
cd bootstrap
terraform init && terraform apply

# Step 2: Configure backend in your main config
cd ../main
terraform init  # will prompt to migrate state
terraform apply
```

## Lessons Learned
- Bootstrap resources (S3 + DynamoDB) must be created before configuring the backend
- `terraform init` with a new backend prompts to migrate existing local state
- DynamoDB lock table needs `LockID` as the hash key — exact name matters
- Enable S3 versioning on the state bucket — you can roll back to previous state
- Never store state in the same bucket as application data
