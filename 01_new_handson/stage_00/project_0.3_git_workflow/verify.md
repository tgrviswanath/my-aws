# Verification & Validation — Project 0.3 Git & GitHub Workflow

---

## 1. Git Configuration Verification

```bash
# Confirm identity is set
git config --list | grep user
# Expected:
# user.name=Your Name
# user.email=your@email.com

# Confirm default branch is main
git config --global init.defaultBranch
# Expected: main
```

---

## 2. Repository Structure Verification

```bash
cd aws-handson-projects

# Confirm .gitignore exists and has key entries
cat .gitignore | grep -E "\.terraform|\.tfstate|\.pem|credentials"
# Expected: all 4 patterns present

# Confirm initial commit exists
git log --oneline
# Expected: at least 1 commit visible

# Confirm remote is set
git remote -v
# Expected: origin  https://github.com/yourusername/aws-handson-projects.git (fetch/push)
```

📸 Screenshot: `git log --oneline` showing commit history

---

## 3. Branch Workflow Verification

```bash
# Confirm feature branch was created and merged
git log --oneline --graph --all
# Expected: graph showing feature branch merged into main

# Confirm feature branch is deleted after merge
git branch -a
# Expected: only main (and origin/main) — no leftover feature branches

# Confirm main is up to date with remote
git status
# Expected: On branch main, nothing to commit, working tree clean
```

📸 Screenshot: `git log --oneline --graph --all` showing branch and merge

---

## 4. GitHub Verification

```bash
# Confirm push succeeded
git log origin/main --oneline
# Expected: same commits as local main

# Confirm PR was merged (check GitHub UI)
# GitHub → repository → Pull requests → Closed
# Expected: merged PR visible
```

📸 Screenshot: GitHub repository showing merged PR in Closed tab

---

## 5. GitHub Actions Verification

```bash
# Confirm workflow file exists
cat .github/workflows/terraform-validate.yml
# Expected: file content with terraform validate steps

# Confirm workflow ran on the PR
# GitHub → repository → Actions
# Expected: "Terraform Validate" workflow with green checkmark
```

📸 Screenshot: GitHub Actions showing green Terraform Validate run

---

## 6. .gitignore Effectiveness Verification

```bash
# Create a test file that should be ignored
touch test.tfstate
touch test.pem

# Confirm git does NOT track them
git status
# Expected: test.tfstate and test.pem NOT listed (ignored)

git check-ignore -v test.tfstate
# Expected: .gitignore:X:*.tfstate  test.tfstate

# Clean up
rm test.tfstate test.pem
```

---

## 7. Demo Script Verification

```bash
chmod +x code/git_workflow_demo.sh
./code/git_workflow_demo.sh
```

Expected output:
```
✅ Repo initialized with main branch
✅ .gitignore created
✅ Feature branch created: feature/add-user-auth
✅ 3 commits made (feat, test, fix)
✅ Merged to main with --no-ff
✅ Tagged v1.0.0
✅ Feature branch deleted
```

📸 Screenshot: Demo script output showing all ✅

---

## 8. Verification Checklist

- [ ] `git config user.name` and `user.email` set
- [ ] `.gitignore` contains Terraform, AWS credentials, and Python patterns
- [ ] `.tfstate`, `.pem` files are ignored by git
- [ ] Initial commit exists on main
- [ ] Remote `origin` points to GitHub repository
- [ ] Feature branch created, committed, and merged
- [ ] Feature branch deleted after merge
- [ ] PR visible in GitHub Closed tab
- [ ] `.github/workflows/terraform-validate.yml` exists
- [ ] GitHub Actions ran and passed on the PR
- [ ] `git_workflow_demo.sh` runs successfully

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
