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

## Phase 6 — Verification & Validation

### 6.1 AWS Console Verification
1. **IAM** → each target account → **Roles** → confirm `handson-dev-deploy-role`, `handson-staging-deploy-role`, `handson-prod-deploy-role` exist
2. **IAM** → each role → **Trust relationships** → confirm management account ID in trust policy
3. **ECS** → each account → confirm separate clusters per environment
4. **GitHub** → **Environments** → confirm `production` environment has required reviewers
5. **CloudTrail** → each account → filter `AssumeRole` → confirm cross-account role assumptions

### 6.2 CLI Verification Commands
```bash
MGMT_PROFILE=management
DEV_PROFILE=dev

# Confirm cross-account roles exist in each target account
for PROFILE in dev staging prod; do
  echo "=== $PROFILE account ==="
  aws iam get-role \
    --role-name handson-${PROFILE}-deploy-role \
    --profile $PROFILE \
    --query "Role.{Name:RoleName,ARN:Arn}" 2>/dev/null || echo "MISSING"
done
# Expected: all 3 roles found

# Confirm management account can assume dev role
aws sts assume-role \
  --role-arn $DEV_DEPLOY_ROLE_ARN \
  --role-session-name verify-test \
  --profile $MGMT_PROFILE \
  --query "AssumedRoleUser.Arn"
# Expected: arn:aws:sts::DEV_ACCOUNT:assumed-role/handson-dev-deploy-role/verify-test

# Confirm assumed role is in the correct account
CREDS=$(aws sts assume-role \
  --role-arn $DEV_DEPLOY_ROLE_ARN \
  --role-session-name verify \
  --profile $MGMT_PROFILE)
AWS_ACCESS_KEY_ID=$(echo $CREDS | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")
AWS_SECRET_ACCESS_KEY=$(echo $CREDS | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")
AWS_SESSION_TOKEN=$(echo $CREDS | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SessionToken'])")
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  aws sts get-caller-identity
# Expected: Account = DEV_ACCOUNT_ID

# Confirm GitHub secrets are set (check via GitHub CLI)
gh secret list --repo YOUR_ORG/YOUR_REPO
# Expected: MGMT_AWS_ROLE_ARN, DEV_DEPLOY_ROLE_ARN, STAGING_DEPLOY_ROLE_ARN, PROD_DEPLOY_ROLE_ARN
```

### 6.3 Functional Tests
```bash
# Test 1: Push to develop → deploys to dev automatically
git checkout develop
echo "# test" >> README.md
git add . && git commit -m "test: verify dev deployment"
git push origin develop
# Watch GitHub Actions → deploy-dev job
# Expected: job runs, assumes dev role, deploys to dev ECS

# Test 2: Verify deployment landed in dev account
aws ecs describe-services \
  --cluster handson-dev-cluster \
  --services handson-flask-api-service \
  --profile $DEV_PROFILE \
  --query "services[0].{Running:runningCount,Desired:desiredCount}"
# Expected: Running == Desired

# Test 3: Merge to main → staging deploys automatically, prod needs approval
git checkout main && git merge develop && git push origin main
# Watch GitHub Actions:
# - deploy-staging: runs automatically
# - deploy-prod: waits for manual approval in GitHub Environments

# Test 4: Prod deployment requires approval
# GitHub → Actions → deploy-prod → Review deployments → Approve
# Expected: prod deployment runs only after approval

# Test 5: Prod role cannot be assumed without approval gate
# Attempt to assume prod role directly from management account
aws sts assume-role \
  --role-arn $PROD_DEPLOY_ROLE_ARN \
  --role-session-name unauthorized-test \
  --profile $MGMT_PROFILE
# Expected: succeeds (role assumption is allowed, but GitHub environment gate
# prevents the workflow from running without approval)

# Test 6: Verify each environment has separate resources
for PROFILE in dev staging prod; do
  echo "=== $PROFILE ==="
  aws ecs list-clusters --profile $PROFILE \
    --query "clusterArns[*]" --output text
done
# Expected: different cluster ARNs in each account
```

### 6.4 Logs & Monitoring Checks
```bash
# Check CloudTrail for cross-account role assumptions
for PROFILE in dev staging prod; do
  echo "=== $PROFILE account AssumeRole events ==="
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --profile $PROFILE \
    --query "Events[*].{Time:EventTime,Who:Username}" \
    --output table
done
# Expected: events showing management account assuming deploy roles

# Check GitHub Actions workflow run status
gh run list --repo YOUR_ORG/YOUR_REPO --limit 5
# Expected: recent runs with status completed/success
```

### 6.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| Dev role assumption | Returns dev account credentials |
| Staging role assumption | Returns staging account credentials |
| Push to develop | Dev deployment runs automatically |
| Merge to main | Staging deploys auto, prod waits |
| Prod approval | Deployment runs after approval |
| CloudTrail | Cross-account AssumeRole events visible |

### 6.6 Verification Checklist
- [ ] Deploy roles exist in dev, staging, prod accounts
- [ ] Trust policies reference management account ID
- [ ] Management account can assume all 3 deploy roles
- [ ] GitHub secrets set for all 4 role ARNs
- [ ] Push to develop triggers dev deployment automatically
- [ ] Dev ECS service updated after develop push
- [ ] Merge to main triggers staging deployment automatically
- [ ] Prod deployment requires manual approval in GitHub Environments
- [ ] Each environment has separate ECS cluster
- [ ] CloudTrail shows cross-account `AssumeRole` events in each account

---

## Screenshots to Take
- [ ] Three AWS accounts in Organizations console
- [ ] Cross-account roles in each target account
- [ ] Pipeline showing dev → staging → prod stages
- [ ] Prod deployment waiting for manual approval
- [ ] CloudTrail showing `AssumeRole` cross-account events
- [ ] Different ECS clusters in different accounts
