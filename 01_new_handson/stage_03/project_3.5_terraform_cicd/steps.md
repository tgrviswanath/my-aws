# Steps — Project 3.5 Terraform CI/CD Pipeline

## Phase 1 — Set Up OIDC (GitHub → AWS Trust)

### 1.1 Create OIDC Provider in AWS
```bash
# Create the GitHub OIDC provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 1.2 Create IAM Role for GitHub Actions
```bash
# Trust policy — only your repo can assume this role
cat > github-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/YOUR_REPO:*"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name github-actions-terraform \
  --assume-role-policy-document file://github-trust-policy.json

# Attach permissions (use least privilege in production)
aws iam attach-role-policy \
  --role-name github-actions-terraform \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### 1.3 Add GitHub Repository Secret
```
GitHub repo → Settings → Secrets and variables → Actions
Add secret: AWS_ROLE_ARN = arn:aws:iam::ACCOUNT_ID:role/github-actions-terraform
```

---

## Phase 2 — Configure Remote State Backend

```bash
# Use the S3 backend from Project 3.4
# Edit terraform/backend.tf with your bucket name
```

---

## Phase 3 — Test the Pipeline

```bash
# Create a feature branch
git checkout -b feature/add-s3-bucket

# Make a change to terraform/main.tf
# Add a new S3 bucket resource

git add .
git commit -m "feat: add app data S3 bucket"
git push origin feature/add-s3-bucket

# Open a Pull Request on GitHub
# Watch the GitHub Actions workflow run:
# 1. terraform fmt -check
# 2. terraform validate
# 3. terraform plan
# 4. Plan output posted as PR comment
```

---

## Phase 4 — Merge and Apply

```bash
# After PR review and approval:
# Merge the PR to main

# Watch the apply workflow:
# 1. terraform plan -out=plan.tfplan
# 2. terraform apply plan.tfplan
# 3. Outputs posted as workflow summary
```

---

## Phase 5 — Drift Detection

```bash
# The drift detection workflow runs on a schedule (daily)
# It runs terraform plan and fails if there are unexpected changes

# Simulate drift: manually create an S3 bucket in the console
# that Terraform doesn't know about

# Wait for scheduled run (or trigger manually)
# Workflow will show: "1 to add" — drift detected!
```

---

## Screenshots to Take
- [ ] OIDC provider created in IAM console
- [ ] IAM role with GitHub trust policy
- [ ] GitHub Actions workflow running on PR
- [ ] Terraform plan output as PR comment
- [ ] Successful apply workflow on merge
- [ ] Drift detection workflow showing changes
