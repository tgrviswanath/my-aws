# Steps — Project 6.1 GitHub Actions + ECS CI/CD

## Phase 1 — Prerequisites

```bash
# Ensure these exist from previous projects:
# - ECR repository (Project 5.3)
# - ECS cluster + service (Project 5.4)
# - OIDC provider + IAM role (Project 3.5)
# - Remote state S3 bucket (Project 3.4)

# Get values needed for GitHub secrets
echo "AWS_ROLE_ARN:"
aws iam get-role --role-name github-actions-terraform \
  --query "Role.Arn" --output text

echo "ALB_URL:"
cd ../project_5.4_ecs_fargate/terraform && terraform output -raw alb_url
```

---

## Phase 2 — Configure GitHub Secrets

```
GitHub repo → Settings → Secrets and variables → Actions → New secret

Required secrets:
  AWS_ROLE_ARN  = arn:aws:iam::ACCOUNT_ID:role/github-actions-terraform
  ALB_URL       = http://your-alb-dns.us-east-1.elb.amazonaws.com
```

---

## Phase 3 — Configure GitHub Environment

```
GitHub repo → Settings → Environments → New environment
Name: production
Protection rules:
  ✅ Required reviewers: add yourself
  ✅ Wait timer: 0 minutes (optional delay)
```

---

## Phase 4 — Test CI Pipeline (Pull Request)

```bash
# Create a feature branch
git checkout -b feature/test-ci-pipeline

# Make a small change
echo "# CI test" >> README.md

git add . && git commit -m "test: trigger CI pipeline"
git push origin feature/test-ci-pipeline

# Open a Pull Request on GitHub
# Watch the CI workflow run:
# 1. Lint (flake8)
# 2. Security scan (bandit)
# 3. Tests (pytest)
# 4. Docker build
# 5. Trivy vulnerability scan
```

---

## Phase 5 — Test CD Pipeline (Merge to Main)

```bash
# Merge the PR to main
# Watch the CD workflow:
# 1. AWS auth via OIDC
# 2. ECR login
# 3. Docker build + push (tagged with git SHA)
# 4. Update ECS task definition
# 5. Deploy to ECS (rolling update)
# 6. Wait for service stability
# 7. Smoke test /health endpoint
# 8. Post deployment summary

# Verify new version is running
curl $ALB_URL/info | python3 -m json.tool
# Should show the new git SHA as version
```

---

## Phase 6 — Test Rollback

```bash
# Get the previous git SHA
git log --oneline -5

# Trigger rollback workflow manually:
# GitHub → Actions → Rollback Deployment → Run workflow
# Input: git_sha = abc1234 (previous commit)
# Input: reason = "Reverting due to performance regression"

# Verify rollback
curl $ALB_URL/info | python3 -m json.tool
# Should show the old git SHA
```

---

## Phase 7 — Verification & Validation

### 7.1 AWS Console Verification
1. **IAM** → **Roles** → `github-actions-terraform` → confirm OIDC trust policy
2. **ECR** → `handson-flask-api` → confirm new image tags (git SHAs) after CD run
3. **ECS** → **Services** → `handson-flask-api-service` → confirm running count = desired
4. **EC2** → **Target Groups** → confirm all targets healthy after deployment
5. **GitHub** → **Actions** → confirm all workflow steps green

### 7.2 CLI Verification Commands
```bash
# Confirm OIDC provider exists
aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[*].Arn"
# Expected: arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com

# Confirm GitHub Actions role exists with correct trust
aws iam get-role --role-name github-actions-terraform \
  --query "Role.{ARN:Arn,Trust:AssumeRolePolicyDocument}"
# Expected: trust policy references token.actions.githubusercontent.com

# Confirm latest ECR image has a git SHA tag
aws ecr list-images --repository-name handson-flask-api \
  --query "imageIds[?imageTag!='latest'].imageTag" --output table
# Expected: tags like abc1234, def5678 (git SHAs)

# Confirm ECS service is stable after deployment
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Deployments:deployments[*].{Status:status,Running:runningCount}}"
# Expected: Running == Desired, one PRIMARY deployment

# Confirm ALB targets are healthy
ALB_URL=$(cd ../project_5.4_ecs_fargate/terraform && terraform output -raw alb_url 2>/dev/null)
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ALB_URL/health)
echo "Post-deployment health: $HTTP_STATUS"
# Expected: 200
```

### 7.3 Functional Tests
```bash
# Test 1: CI pipeline passes on PR
# Create a branch, push, open PR → watch GitHub Actions
git checkout -b test/verify-ci
echo "# verify" >> README.md
git add . && git commit -m "test: verify CI pipeline"
git push origin test/verify-ci
# Expected: CI workflow runs, all steps green (lint, test, build, scan)

# Test 2: CD pipeline deploys on merge to main
git checkout main && git merge test/verify-ci && git push origin main
# Expected: CD workflow runs, ECS service updated with new image

# Test 3: Verify new git SHA is deployed
DEPLOYED_SHA=$(curl -s $ALB_URL/info | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('version','unknown'))")
LATEST_SHA=$(git rev-parse --short HEAD)
echo "Deployed: $DEPLOYED_SHA | Latest commit: $LATEST_SHA"
# Expected: both match

# Test 4: Rollback workflow works
# GitHub → Actions → Rollback Deployment → Run workflow
# Input: previous git SHA
# After rollback:
ROLLED_BACK=$(curl -s $ALB_URL/info | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('version','unknown'))")
echo "After rollback: $ROLLED_BACK"
# Expected: previous SHA

# Test 5: CD fails on feature branch (OIDC trust policy enforced)
# Push directly to a feature branch and manually trigger CD
# Expected: AWS auth step fails with AccessDenied
```

### 7.4 Logs & Monitoring Checks
```bash
# Check CloudWatch logs for deployment errors
aws logs filter-log-events \
  --log-group-name /ecs/handson-flask-api \
  --filter-pattern "ERROR" \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --query "events[*].message"
# Expected: no ERROR events after successful deployment

# Check ECS deployment events
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].events[:5].{Time:createdAt,Message:message}"
# Expected: "service reached a steady state" as most recent event
```

### 7.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| CI workflow on PR | All steps green |
| CD workflow on merge | ECS updated with new SHA |
| `curl /info` version | Matches latest git SHA |
| ALB health after deploy | HTTP 200 |
| Rollback | Previous SHA restored |
| Feature branch CD | AccessDenied (OIDC blocks) |

### 7.6 Verification Checklist
- [ ] OIDC provider exists in IAM
- [ ] GitHub Actions role has correct trust policy
- [ ] CI workflow passes on PR (lint, test, build, scan all green)
- [ ] CD workflow runs on merge to main
- [ ] New ECR image tagged with git SHA after CD
- [ ] ECS service updated and stable (running == desired)
- [ ] ALB targets healthy after deployment
- [ ] `/info` version matches latest git SHA
- [ ] Rollback workflow restores previous version
- [ ] CD blocked on feature branch (OIDC trust policy working)

---

## Screenshots to Take
- [ ] CI workflow passing on PR (all checks green)
- [ ] Trivy scan results
- [ ] CD workflow running on merge to main
- [ ] ECS deployment in progress (rolling update)
- [ ] Smoke test passing
- [ ] Deployment summary in GitHub Actions
- [ ] Rollback workflow triggered manually
- [ ] ECR showing multiple image tags (git SHAs)
