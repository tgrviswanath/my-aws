# Steps — Project 6.4 Multi-account CI/CD Pipeline

## Phase 1 — Account Setup (Simulate with Single Account)

```bash
# For learning, simulate multiple accounts using different IAM roles
# in the same account with different resource prefixes

# Or use AWS Organizations to create actual sub-accounts (free)
# AWS Console → Organizations → Add account → Create account
```

---

## Phase 2 — Deploy Cross-account Roles

```bash
# In each target account (dev, staging, prod):
cd terraform/target-account

# Dev account
terraform init
terraform apply \
  -var="source_account_id=MGMT_ACCOUNT_ID" \
  -var="environment=dev"

# Staging account (switch AWS profile)
AWS_PROFILE=staging terraform apply \
  -var="source_account_id=MGMT_ACCOUNT_ID" \
  -var="environment=staging"

# Prod account
AWS_PROFILE=prod terraform apply \
  -var="source_account_id=MGMT_ACCOUNT_ID" \
  -var="environment=prod"
```

---

## Phase 3 — Configure GitHub Secrets

```
MGMT_AWS_ROLE_ARN     = arn:aws:iam::MGMT_ACCOUNT:role/github-cd-role
DEV_DEPLOY_ROLE_ARN   = arn:aws:iam::DEV_ACCOUNT:role/handson-dev-deploy-role
STAGING_DEPLOY_ROLE_ARN = arn:aws:iam::STAGING_ACCOUNT:role/handson-staging-deploy-role
PROD_DEPLOY_ROLE_ARN  = arn:aws:iam::PROD_ACCOUNT:role/handson-prod-deploy-role
```

---

## Phase 4 — Test the Pipeline

```bash
# Push to develop → deploys to dev automatically
git checkout develop
echo "# dev change" >> README.md
git add . && git commit -m "feat: test dev deployment"
git push origin develop

# Watch: GitHub Actions → deploy-dev job runs

# Merge to main → deploys to staging automatically, prod needs approval
git checkout main
git merge develop
git push origin main

# Watch: deploy-staging runs automatically
# Then: deploy-prod waits for manual approval in GitHub Environments
```

---

## Phase 5 — Verify Cross-account Deployment

```bash
# Verify which account each ECS cluster is in
aws sts get-caller-identity  # management account

# After assuming dev role
aws sts assume-role \
  --role-arn $DEV_DEPLOY_ROLE_ARN \
  --role-session-name test-session \
  --external-id handson-dev-deploy

# Use the temporary credentials to verify you're in the dev account
AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=... \
  aws sts get-caller-identity
```

---

## Screenshots to Take
- [ ] Three AWS accounts in Organizations console
- [ ] Cross-account roles in each target account
- [ ] Pipeline showing dev → staging → prod stages
- [ ] Prod deployment waiting for manual approval
- [ ] CloudTrail showing `AssumeRole` cross-account events
- [ ] Different ECS clusters in different accounts
