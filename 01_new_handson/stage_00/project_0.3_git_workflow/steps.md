# Steps — Project 0.3 Git & GitHub Workflow

## Phase 1 — Initialize Repository

```bash
mkdir aws-handson-projects
cd aws-handson-projects

git init
git config user.name "Your Name"
git config user.email "your@email.com"

# Verify
git config --list
```

---

## Phase 2 — Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Terraform state and cache
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl
terraform.tfvars
override.tf
override.tf.json

# AWS credentials — NEVER commit these
.aws/
*.pem
*.key
credentials

# LocalStack data
localstack-data/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp

# Python
__pycache__/
*.pyc
.env
venv/

# Logs
*.log
EOF

git add .gitignore
git commit -m "chore: add .gitignore for AWS/Terraform projects"
```

---

## Phase 3 — Create Repository Structure

```bash
# Create stage folders
mkdir -p stage_00/project_0.1_local_dev_setup/{terraform,docs,scripts}
mkdir -p stage_00/project_0.2_linux_lab/{docs,scripts}
mkdir -p stage_00/project_0.3_git_workflow

# Create placeholder READMEs
touch stage_00/project_0.1_local_dev_setup/README.md
touch stage_00/project_0.2_linux_lab/README.md

git add .
git commit -m "chore: scaffold stage_00 project structure"
```

---

## Phase 4 — Connect to GitHub

```bash
# Create repo on GitHub first (github.com → New repository)
# Name: aws-handson-projects
# Visibility: Public (for portfolio)
# Do NOT initialize with README (we already have one)

git remote add origin https://github.com/yourusername/aws-handson-projects.git
git branch -M main
git push -u origin main
```

---

## Phase 5 — Feature Branch Workflow

```bash
# For each new project, create a feature branch
git checkout -b feature/project-0.1-local-dev-setup

# Do your work...
# Add files, write code, take screenshots

git add stage_00/project_0.1_local_dev_setup/
git commit -m "feat: add project 0.1 local dev setup with LocalStack"

# Push branch
git push -u origin feature/project-0.1-local-dev-setup

# On GitHub: create Pull Request
# Title: "feat: Project 0.1 — Local Cloud Development Setup"
# Description: use the PR template below

# After review, merge to main
git checkout main
git pull origin main
git branch -d feature/project-0.1-local-dev-setup
```

---

## Phase 6 — Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Project
<!-- e.g. Project 0.1 — Local Cloud Development Setup -->

## What This Does
<!-- Brief description -->

## Services / Tools Used
<!-- List AWS services or tools -->

## Architecture
<!-- Link to architecture diagram or paste ASCII diagram -->

## How to Test
<!-- Steps to verify this works -->

## Cost Estimate
<!-- Monthly cost -->

## Screenshots
<!-- Attach screenshots -->

## Checklist
- [ ] README.md updated
- [ ] Architecture diagram added
- [ ] Steps documented
- [ ] Cost estimate included
- [ ] Screenshots taken
```

---

## Phase 7 — GitHub Actions Terraform Validation

Create `.github/workflows/terraform-validate.yml`:

```yaml
name: Terraform Validate

on:
  pull_request:
    paths:
      - '**/terraform/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Find Terraform directories
        id: find
        run: |
          dirs=$(find . -name "*.tf" -not -path "*/.terraform/*" | xargs -I{} dirname {} | sort -u)
          echo "dirs=$dirs" >> $GITHUB_OUTPUT

      - name: Terraform Init and Validate
        run: |
          for dir in ${{ steps.find.outputs.dirs }}; do
            echo "Validating $dir"
            cd $dir
            terraform init -backend=false
            terraform validate
            cd -
          done
```

---

## Screenshots to Take
- [ ] GitHub repository created and visible
- [ ] `.gitignore` committed
- [ ] Feature branch created (`git branch -a` output)
- [ ] Pull request open on GitHub
- [ ] GitHub Actions workflow running on PR
- [ ] Merged PR on main branch

# AWS CLI Quick Reference

`ash
# Verify setup
aws sts get-caller-identity
aws configure list

# Common commands
aws ec2 describe-instances --output table
aws s3 ls
aws lambda list-functions --output table
`
