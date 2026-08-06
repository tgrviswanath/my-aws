# Git Workflow — GUIDE.md

> **Stage:** 00 — Foundational Setup  
> **Project:** 0.3 — Git Workflow  
> **Cost:** $0  
> **Time:** 45–60 minutes

---

## 1. Project Overview

### Title: Git Workflow for AWS Projects

**Problem Statement:**  
Every real AWS project involves code — infrastructure scripts, Lambda functions, CloudFormation templates, CI/CD pipelines. Without Git, you have no version history, no collaboration, and no way to track what changed when something breaks. This project establishes a professional Git workflow that carries through all subsequent projects.

**Objectives:**
- Initialize local Git repositories
- Connect to remote repositories (GitHub or AWS CodeCommit)
- Implement a feature-branch workflow: branch → commit → push → PR
- Understand merge strategies
- Set up Git for use with AWS projects

**What You Will Learn:**
- Core Git commands: `init`, `clone`, `add`, `commit`, `push`, `pull`, `branch`, `merge`
- Feature branch workflow
- Creating pull requests on GitHub
- Using AWS CodeCommit as an alternative to GitHub
- `.gitignore` patterns for AWS projects (never commit `.aws/credentials`)

**Skill Level:** Beginner–Intermediate  
**AWS Services Used:** AWS CodeCommit (optional), IAM (for CodeCommit credentials)  
**Tools Required:** Git, GitHub account (free), VS Code (optional)

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Local Git Repository                                  │  │
│  │                                                        │  │
│  │  main branch ──────────────────────────────────────►  │  │
│  │                          │                            │  │
│  │  feature/my-feature ─────┘ (merge via PR)             │  │
│  │                                                        │  │
│  │  Working Tree → Staging (Index) → Local Commits        │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                 │
│                    git push / git pull                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
              ┌──────────────┴───────────────┐
              │                              │
              ▼                              ▼
┌─────────────────────┐          ┌─────────────────────────┐
│   GitHub.com         │          │   AWS CodeCommit        │
│                      │          │                         │
│   - Public/Private   │          │   - Private repos       │
│   - Pull Requests    │          │   - IAM auth            │
│   - Actions (CI/CD)  │          │   - AWS ecosystem       │
│   - Free for teams   │          │   - Free for 5 users    │
└─────────────────────┘          └─────────────────────────┘
```

**Git Data Flow:**
```
Untracked → git add → Staged → git commit → Local repo → git push → Remote repo
```

---

## 3. Prerequisites

### Software Requirements
| Tool | Version | How to Verify |
|------|---------|---------------|
| Git | 2.x+ | `git --version` |
| AWS CLI | 2.x | `aws --version` |
| VS Code | Latest | Optional |

### Account Requirements
- GitHub account (free) — https://github.com
- AWS account with CLI configured (project 0.1 complete)
- For CodeCommit: IAM user with CodeCommit permissions

### Knowledge Prerequisites
- Completed Project 0.1 (AWS CLI)
- Completed Project 0.2 (Linux/bash basics)
- Understand concept of version control (what a commit is)

### Git Initial Setup
```bash
# Set your identity (required for every commit)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Set default branch name to main
git config --global init.defaultBranch main

# Set preferred editor (VS Code)
git config --global core.editor "code --wait"

# Verify settings
git config --list
```

---

## 4. Project Folder Structure

```
project_0.3_git_workflow/
├── GUIDE.md                        ← This file
├── steps_awsconsoleui.md           ← GitHub UI + CodeCommit console steps
├── cost_estimate.md                ← $0 cost breakdown
├── demo-repo/                      ← Practice repository created during project
│   ├── .gitignore                  ← AWS-specific ignores
│   ├── README.md                   ← Repository documentation
│   └── scripts/
│       └── hello_aws.sh            ← Sample script to commit
└── cheatsheet/
    └── git_commands.md             ← Quick reference for common Git commands
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method — GitHub UI + CodeCommit

#### Prerequisites Check

Before starting the GitHub/console steps:
- [ ] GitHub account exists and you are logged in
- [ ] Git is installed locally (`git --version`)
- [ ] AWS CLI is configured (`aws sts get-caller-identity`)
- [ ] You know your GitHub username

---

#### Decision Point 1: GitHub vs AWS CodeCommit

| Factor | GitHub | AWS CodeCommit |
|--------|--------|----------------|
| Cost | Free (public/private repos) | Free (up to 5 active users) |
| Authentication | HTTPS + PAT or SSH | IAM credentials or SSH |
| CI/CD integration | GitHub Actions (powerful) | AWS CodePipeline |
| Community/ecosystem | Huge (open source, PRs) | AWS-only |
| Visibility | Public or private | Private only |
| Best for | Open source, portfolio, teams | AWS-integrated private repos |
| Learning value | Industry standard | AWS certification path |

**✅ Use GitHub for:** Open source projects, portfolio work, collaboration, most real-world teams.  
**✅ Use CodeCommit for:** Fully private AWS-integrated repos, compliance environments, teams already in AWS ecosystem.

> **For this project:** We use GitHub as the primary workflow. CodeCommit is covered as an optional addition.

---

#### GitHub Console — Create Repository

1. Go to https://github.com
2. Click the **+** icon (top right) → **New repository**
3. Fill in:
   - Repository name: `aws-learning-projects`
   - Description: `AWS hands-on projects from stage_00 onwards`
   - Visibility: **Public** (good for portfolio) or Private
   - Check: **Add a README file**
   - Add `.gitignore`: select **Python** template (we'll customize it)
4. Click **Create repository**

   **📸 Screenshot:** Capture the repository creation form and the resulting repo homepage

5. You now have a remote repository at: `https://github.com/<your-username>/aws-learning-projects`

---

#### GitHub Console — Create a Branch and Pull Request

6. On your repository page, click the **branch dropdown** (shows "main")
7. Type: `feature/add-aws-scripts`
8. Click **Create branch: feature/add-aws-scripts from main**
9. You are now on the feature branch

   **📸 Screenshot:** Capture the branch dropdown showing your new branch

10. Click on the `README.md` file
11. Click the **pencil icon** to edit
12. Add a line: `## Projects\n- Project 0.1: Local Dev Setup`
13. At the bottom, enter commit message: `docs: add project list to README`
14. Select: "Commit directly to `feature/add-aws-scripts` branch"
15. Click **Commit changes**

16. GitHub prompts: "Compare & pull request" — click it
17. On the PR page:
    - Title: `Add project list to README`
    - Description: `Adds initial project list. Part of stage_00 setup.`
18. Click **Create pull request**
19. Click **Merge pull request** → **Confirm merge**

   **📸 Screenshot:** Capture the open pull request ready to merge

---

#### AWS Console — CodeCommit (Optional)

If you want to explore CodeCommit:

1. Open AWS Console → search "CodeCommit"
2. Click **Create repository**
   - Repository name: `aws-learning-projects`
   - Description: `Private AWS projects repository`
3. Click **Create**
4. Set up HTTPS credentials:
   - IAM Console → Users → `cli-learning-user`
   - Security credentials tab → HTTPS Git credentials for CodeCommit
   - Click **Generate credentials** → Download CSV

---

### 5B. AWS CLI / Git CLI Method

#### Initialize a Local Repository

```bash
# Navigate to your projects folder
cd ~/projects   # WSL2 or
cd C:\projects  # Windows

# Create project directory
mkdir aws-learning-projects
cd aws-learning-projects

# Initialize Git repository
git init

# Check the status
git status
# Output: On branch main, No commits yet

# Create a .gitignore (CRITICAL for AWS projects)
cat > .gitignore << 'EOF'
# AWS credentials — NEVER commit these
.aws/
*.pem
*.key
*_credentials*
credentials

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
env/

# Node.js
node_modules/
npm-debug.log

# Terraform (used in later projects)
*.tfstate
*.tfstate.backup
.terraform/
*.tfvars

# OS files
.DS_Store
Thumbs.db
*.log

# IDE
.vscode/settings.json
.idea/
EOF

# Create README
cat > README.md << 'EOF'
# AWS Learning Projects

Hands-on AWS projects from stage_00 (foundations) onwards.

## Projects

- Project 0.1: Local Dev Environment Setup
- Project 0.2: Linux Lab (WSL2 + CloudShell)
- Project 0.3: Git Workflow
- Project 0.4: AWS Billing Setup

## Tools Used

- AWS CLI v2
- Python 3.x
- Git
- VS Code
EOF

# Check what's ready to commit
git status
# Shows README.md and .gitignore as "Untracked files"
```

#### Stage and Commit Files

```bash
# Stage specific files (preferred over git add .)
git add README.md .gitignore

# Verify what's staged
git status
# Shows both files as "Changes to be committed"

# Make the first commit
git commit -m "chore: initial project setup with README and gitignore"

# View the commit log
git log --oneline
# Output: abc1234 chore: initial project setup with README and gitignore
```

#### Connect to GitHub Remote

```bash
# Add GitHub remote (replace with your URL)
git remote add origin https://github.com/<your-username>/aws-learning-projects.git

# Verify remote was added
git remote -v
# Output:
# origin  https://github.com/<username>/aws-learning-projects.git (fetch)
# origin  https://github.com/<username>/aws-learning-projects.git (push)

# Push to GitHub (first time: -u sets upstream tracking)
git push -u origin main

# You may be prompted for GitHub credentials:
# Username: your GitHub username
# Password: your GitHub Personal Access Token (not your GitHub password)
```

#### Feature Branch Workflow

```bash
# Create and switch to a feature branch
git checkout -b feature/add-hello-aws-script
# Equivalent to:
# git branch feature/add-hello-aws-script
# git checkout feature/add-hello-aws-script

# Verify you're on the new branch
git branch
# Output:
# * feature/add-hello-aws-script
#   main

# Create a new file on this branch
mkdir -p scripts
cat > scripts/hello_aws.sh << 'EOF'
#!/bin/bash
# hello_aws.sh — Verify AWS connection
echo "Hello from $(whoami) on $(hostname)"
echo "AWS Account: $(aws sts get-caller-identity --query Account --output text)"
echo "AWS Region:  $(aws configure get region)"
echo "Date:        $(date)"
EOF

chmod +x scripts/hello_aws.sh

# Stage and commit on the feature branch
git add scripts/hello_aws.sh
git commit -m "feat: add hello_aws verification script"

# Push the feature branch to GitHub
git push -u origin feature/add-hello-aws-script

# Now create PR on GitHub UI, merge it, then:
git checkout main
git pull origin main   # get the merged changes locally

# Clean up the feature branch
git branch -d feature/add-hello-aws-script
git push origin --delete feature/add-hello-aws-script
```

#### Connect to AWS CodeCommit (Optional)

```bash
# Configure Git to use AWS credential helper for CodeCommit
git config --global credential.helper \
    '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

# Clone your CodeCommit repo
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/aws-learning-projects

# From here, all standard git commands work the same
cd aws-learning-projects
git log
git branch
```

---

## 6. Code Deep Dive

### The Three Trees of Git

```
Working Directory    →    Staging Area (Index)    →    Repository (.git)
                    git add                       git commit
                    ◄──────────────────────────────────────────  git reset
                    ◄───────────────────────────  git restore --staged
```

### Commit Message Convention (Conventional Commits)

```
<type>: <subject>

types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation only
  chore:    Build/tooling changes
  refactor: Code refactor (no feature/fix)
  test:     Adding tests
  ci:       CI/CD changes

Examples:
  feat: add S3 bucket creation script
  fix: correct region in aws configure
  docs: update README with project list
  chore: add .gitignore for Python projects
```

### Essential `.gitignore` for AWS Projects

```gitignore
# Credentials — the most critical ignore rule
.aws/credentials
.env
*.env
*.pem
*.ppk
*.key
*secret*
*password*

# AWS service artifacts
cdk.out/
.cdk.staging/
*.tfstate
*.tfstate.backup
.terraform/

# Python virtual environments
.venv/
venv/
env/
__pycache__/
```

### Git Aliases for Efficiency

```bash
# Add useful aliases to ~/.gitconfig
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.lg "log --oneline --graph --decorate --all"

# Usage:
git st      # git status
git co main # git checkout main
git br      # git branch
git lg      # pretty log graph
```

---

## 7. Verification

```bash
# 1. Verify Git identity is set
git config user.name && git config user.email
# Expected: Your Name, your@email.com

# 2. Verify default branch is main
git config init.defaultBranch
# Expected: main

# 3. Verify local repo exists
git status
# Expected: "On branch main, nothing to commit"

# 4. Verify remote is connected
git remote -v
# Expected: origin URL shown for fetch and push

# 5. Verify commit history exists
git log --oneline
# Expected: at least one commit

# 6. Verify .gitignore is working
echo "test_secret=abc123" > test_creds.env
git status
# Expected: test_creds.env should NOT appear (if .env is in .gitignore)
rm test_creds.env

# 7. Verify branch operations work
git checkout -b test-branch
git checkout main
git branch -d test-branch
# Expected: no errors, clean branch created and deleted

# 8. Verify push works
git push origin main
# Expected: "Everything up-to-date" or push confirmation
```

---

## 8. Observations & Key Learnings

### The Golden Rule: Never Commit Credentials
The most important Git rule for AWS work: never commit `.aws/credentials`, `.env` files, or any file containing access keys. If you accidentally commit a key:
1. Immediately deactivate/delete the key in IAM console
2. Rotate to a new key
3. Use `git filter-branch` or BFG Repo Cleaner to purge it from history
4. AWS monitors public GitHub repos and notifies you within minutes of an exposed key

### Branch Naming Conventions
```
feature/short-description    ← new functionality
fix/issue-description        ← bug fixes
docs/what-was-updated        ← documentation
chore/tooling-task           ← maintenance
hotfix/critical-fix          ← emergency production fix
```

### GitHub vs CodeCommit: Practical Differences
- **Auth:** GitHub uses Personal Access Tokens or SSH keys. CodeCommit uses IAM HTTPS credentials or SSH keys from IAM.
- **PR experience:** GitHub has a richer PR interface with inline comments and review workflows.
- **IAM integration:** CodeCommit uses IAM policies directly — same `aws configure` credentials can work.
- **Pricing:** GitHub free tier is unlimited for public repos and has generous private repo limits. CodeCommit is free for up to 5 active users.

### Git for Infrastructure Code
```bash
# Always review before committing infrastructure changes
git diff                    # see unstaged changes
git diff --staged           # see staged changes

# Tag releases for infrastructure
git tag -a v1.0.0 -m "Initial infrastructure baseline"
git push origin v1.0.0
```

---

## 9. Screenshots

Document these for your notes:

1. **GitHub repo creation** — the new repository homepage
2. **Branch creation** — dropdown showing both `main` and `feature/` branch
3. **Pull request open** — showing the diff and merge options
4. **Merged PR** — the purple "Merged" badge on GitHub
5. **`git log --oneline`** — terminal showing commit history
6. **`git branch`** — showing all local branches
7. **CodeCommit repo** (optional) — AWS console showing repository

---

## 10. Cleanup

### GitHub Cleanup
The GitHub repository is free and can stay. If you want to delete the test repository:
1. GitHub → repository → Settings (gear icon)
2. Scroll to "Danger Zone"
3. Click **Delete this repository**
4. Type the repository name to confirm

### CodeCommit Cleanup (if created)
```bash
# Delete CodeCommit repository
aws codecommit delete-repository --repository-name aws-learning-projects

# Remove Git credential helper config
git config --global --unset credential.helper
git config --global --unset credential.UseHttpPath
```

### Local Cleanup (Optional)
```bash
# Remove the local repository (all history deleted)
# In WSL2/bash:
rm -rf ~/projects/aws-learning-projects

# In PowerShell:
Remove-Item -Recurse -Force C:\projects\aws-learning-projects
```

### IAM Cleanup (CodeCommit only)
1. IAM Console → Users → `cli-learning-user`
2. Security credentials tab
3. HTTPS Git credentials for CodeCommit → **Delete**

### Cleanup Checklist
- [ ] No AWS credentials committed to any repository
- [ ] `.gitignore` is in place with credential patterns
- [ ] GitHub PAT revoked if no longer needed (GitHub → Settings → Developer settings → Tokens)
- [ ] CodeCommit repository deleted if you created one
- [ ] Local repositories removed if you want a clean workspace

---

*End of GUIDE.md — Project 0.3: Git Workflow*

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
