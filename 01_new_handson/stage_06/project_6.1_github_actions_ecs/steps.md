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

## Screenshots to Take
- [ ] CI workflow passing on PR (all checks green)
- [ ] Trivy scan results
- [ ] CD workflow running on merge to main
- [ ] ECS deployment in progress (rolling update)
- [ ] Smoke test passing
- [ ] Deployment summary in GitHub Actions
- [ ] Rollback workflow triggered manually
- [ ] ECR showing multiple image tags (git SHAs)
