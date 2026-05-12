# Project 6.4 — Multi-account CI/CD Pipeline

## What This Does
Deploys the same application across multiple AWS accounts (dev, staging, prod) from a single CI/CD pipeline using cross-account IAM role assumption.

## Account Structure
```
Management Account (CI/CD lives here)
  ├── Dev Account     (auto-deploy on merge to develop)
  ├── Staging Account (auto-deploy on merge to main)
  └── Prod Account    (manual approval required)
```

## Cross-account Flow
```
GitHub Actions (management account)
  → AssumeRole → dev-account/deploy-role
  → Deploy to dev ECS

  → AssumeRole → staging-account/deploy-role
  → Deploy to staging ECS

  → Manual approval
  → AssumeRole → prod-account/deploy-role
  → Deploy to prod ECS
```

## Key Concepts
| Concept | Description |
|---------|-------------|
| Cross-account role | Role in target account that trusts the source account |
| Role chaining | Assume role A, then assume role B from A |
| Account isolation | Dev changes can't affect prod |
| Promotion pipeline | Code flows dev → staging → prod |

## How to Deploy
```bash
# Deploy trust roles in each target account
cd terraform/target-account
terraform init && terraform apply -var="source_account_id=MGMT_ACCOUNT_ID"

# Deploy pipeline in management account
cd ../management-account
terraform init && terraform apply
```

## Lessons Learned
- Cross-account roles: target account trusts source account's role ARN
- Use separate ECR per account OR share a central ECR with cross-account access
- Tagging strategy: tag all resources with `Account`, `Environment`, `DeployedBy`
- AWS Organizations SCPs can restrict what accounts can do — important for prod
- Never deploy directly to prod — always go through staging first

## Code

### `code/cross_account_deploy.py` — Deploy to a target AWS account via role assumption

```bash
pip install boto3

# Deploy to a target account by assuming a cross-account role
python code/cross_account_deploy.py \
  --target-account 123456789012 \
  --role DeployRole \
  --cluster prod-cluster \
  --service api \
  --image 123456789012.dkr.ecr.us-east-1.amazonaws.com/api:v3

# Use a specific source account profile
python code/cross_account_deploy.py \
  --target-account 123456789012 \
  --role DeployRole \
  --cluster prod-cluster \
  --service api \
  --image 123456789012.dkr.ecr.us-east-1.amazonaws.com/api:v3 \
  --profile ci-account
```

What it does:
- Uses STS `AssumeRole` to get temporary credentials for the target account
- Prints the assumed role ARN and credential expiry
- Registers a new ECS task definition revision with the updated image
- Updates the ECS service and polls until deployment completes
- Verifies final task counts in the target account

> The cross-account role must have a trust policy allowing the source account to assume it.
