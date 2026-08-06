# AWS Console UI Steps — Project 0.3: Git Workflow

> **Purpose:** Step-by-step GitHub UI walkthrough + optional AWS CodeCommit console steps  
> **Time:** 25–35 minutes  
> **Cost:** $0

---

## Prerequisites Check

Before starting:
- [ ] GitHub account exists — https://github.com (free)
- [ ] Git is installed locally — `git --version` returns output
- [ ] Git identity is configured — `git config user.name` returns your name
- [ ] Completed Project 0.1 — AWS CLI configured
- [ ] Browser logged in to GitHub and AWS Console

---

## Step 1 — Create GitHub Repository

### Navigate to New Repository

1. Go to https://github.com
2. Click the **+** icon in the top-right corner
3. Select **New repository**

### Decision Point 1: Repository Visibility

| Option | Use When |
|--------|----------|
| ✅ **Public** | Portfolio work, open source, sharing with community |
| **Private** | Sensitive projects, AWS credentials might be referenced in READMEs |

> **For learning projects:** Public is recommended — it builds your portfolio and GitHub profile.

### Decision Point 2: GitHub vs AWS CodeCommit

| Factor | GitHub | AWS CodeCommit |
|--------|--------|---------------|
| ✅ Open source/portfolio | Best choice | Not indexed/discoverable |
| ✅ Team collaboration | GitHub Issues, PRs, Actions | Requires AWS IAM for each user |
| ✅ CI/CD to AWS | GitHub Actions → AWS | CodePipeline (same ecosystem) |
| ✅ Free private repos | Unlimited (GitHub free plan) | Free ≤5 active users |

> **Decision: Use GitHub for this project.** CodeCommit setup is covered as Step 4 (optional).

### Fill in Repository Details

4. Repository name: `aws-learning-projects`
5. Description: `Hands-on AWS projects - stage_00 foundations`
6. Visibility: **Public**
7. Check: ✅ **Add a README file**
8. Add .gitignore: Click dropdown → select **Python**
9. License: MIT (optional)
10. Click **Create repository**

**📸 Screenshot:** Capture the repository creation form before clicking "Create repository"

### Expected Outcome — Step 1

You land on your new repository page:
```
https://github.com/<your-username>/aws-learning-projects
```

You see:
- `README.md` with your repository name
- `.gitignore` (Python template)
- Default branch: `main`

**📸 Screenshot:** Capture the repository homepage showing the file list and README preview

### Troubleshooting — Step 1

| Problem | Solution |
|---------|----------|
| Name already taken | Add a suffix: `aws-learning-projects-2024` |
| Can't create repo | Check if GitHub account is email-verified |
| .gitignore not showing | It may be in the repo but hidden; click "Show all files" |

---

## Step 2 — Create a Feature Branch and Pull Request

### Create a Branch via GitHub UI

1. On your repository page, click the **branch dropdown** (currently shows `main`)
2. In the text field that appears, type: `feature/add-project-structure`
3. You see "Create branch: feature/add-project-structure from main"
4. Click that option

**📸 Screenshot:** Capture the branch creation dropdown mid-process

### Edit a File on the Branch

5. Confirm you're on `feature/add-project-structure` (branch dropdown shows it)
6. Click on `README.md`
7. Click the **pencil icon** (Edit this file) in the top-right of the file view
8. Replace or add content:

```markdown
# AWS Learning Projects

Hands-on AWS projects from stage_00 (foundations) onwards.

## Projects

### Stage 00 — Foundations
- [x] Project 0.1: Local Dev Environment Setup
- [x] Project 0.2: Linux Lab (WSL2 + CloudShell)
- [x] Project 0.3: Git Workflow
- [ ] Project 0.4: AWS Billing Setup

## Tools

- AWS CLI v2
- Python 3.x
- Git 2.x
- VS Code

## Repository Structure

Each project contains:
- `GUIDE.md` — Full implementation guide
- `steps_awsconsoleui.md` — Console walkthrough
- `cost_estimate.md` — Cost breakdown
```

9. Scroll down to **Commit changes** section
10. Commit message: `docs: update README with project structure`
11. Extended description: `Add project list and repository structure documentation`
12. Select: ✅ **Commit directly to `feature/add-project-structure` branch**
13. Click **Commit changes**

### Create a Pull Request

14. A yellow banner appears: "feature/add-project-structure had recent pushes"
15. Click the green **Compare & pull request** button
16. On the "Open a pull request" page:
    - Base: `main`
    - Compare: `feature/add-project-structure`
    - Title: `docs: update README with project structure`
    - Description:
      ```
      ## Summary
      Updates README to include project list and structure documentation.
      
      ## Changes
      - Add stage_00 project list with checkboxes
      - Add tools section
      - Add repository structure explanation
      
      ## Testing
      No code changes, documentation only.
      ```
17. Click **Create pull request**

**📸 Screenshot:** Capture the open pull request showing the diff (red/green changes)

### Review and Merge the PR

18. Scroll down to see the **Files changed** tab — verify your changes look correct
19. Click **Files changed** tab to see the diff view
20. Back on **Conversation** tab, click **Merge pull request**
21. Click **Confirm merge**
22. Click **Delete branch** (to keep the repo clean)

**📸 Screenshot:** Capture the merged PR showing the purple "Merged" badge

### Expected Outcome — Step 2

- Feature branch merged into `main`
- `README.md` on `main` now has the updated content
- Branch deleted
- Commit count increased by 1

### Troubleshooting — Step 2

| Problem | Solution |
|---------|----------|
| "Can't create branch" | Check you have write access to the repo |
| Merge conflicts | Click "Resolve conflicts" in PR, edit the file, mark as resolved |
| PR shows no changes | Ensure you committed to the feature branch, not main |
| "Compare & pull request" banner disappeared | Go to Pull requests tab → New pull request |

---

## Step 3 — Clone and Work Locally

### Clone to Local Machine

```bash
# Get the clone URL from GitHub:
# Click green "Code" button → HTTPS tab → copy URL

# In your terminal (WSL2 or PowerShell)
git clone https://github.com/<your-username>/aws-learning-projects.git
cd aws-learning-projects

# Verify you have the latest from the merge
git log --oneline
# Should show: two commits (initial + README update)

# Check branches
git branch -a
# Should show: main (local), remotes/origin/main
```

### Local Feature Branch Workflow

```bash
# Create local feature branch
git checkout -b feature/add-gitignore-updates

# Improve the .gitignore for AWS projects
cat >> .gitignore << 'EOF'

# AWS specific
.aws/
*.pem
*.ppk
cdk.out/
.cdk.staging/
*.tfstate
*.tfstate.backup
.terraform/

# Secrets (never commit)
.env
*.env
*secret*
*password*
*credentials*
EOF

# Stage and commit
git add .gitignore
git commit -m "chore: enhance gitignore with AWS-specific patterns"

# Push branch to GitHub
git push -u origin feature/add-gitignore-updates

# Create PR (go to GitHub UI now, or use GitHub CLI):
# gh pr create --title "chore: enhance gitignore" --body "Add AWS-specific ignore patterns"

# After merging on GitHub, sync locally:
git checkout main
git pull origin main
git branch -d feature/add-gitignore-updates
```

**📸 Screenshot:** Capture `git log --oneline --graph` showing the branch structure

---

## Step 4 — AWS CodeCommit (Optional)

### Prerequisites for CodeCommit
- AWS CLI configured (project 0.1)
- IAM user with CodeCommit permissions
- Generate HTTPS Git credentials for CodeCommit

### Navigate to CodeCommit in Console

1. Open https://console.aws.amazon.com
2. Search for `CodeCommit` in the top search bar
3. Click **CodeCommit** under Developer Tools

### Decision Point 3: CodeCommit Authentication Method

| Method | Setup | Best For |
|--------|-------|----------|
| ✅ **HTTPS + IAM Git credentials** | Generate in IAM console | Simple, Windows-friendly |
| **SSH + IAM SSH key** | Upload public key to IAM | Unix/Linux environments |
| **git-remote-codecommit** | Python-based helper | Federated users, SSO |

> **For this project: Use HTTPS + IAM Git credentials** (simplest setup).

### Create CodeCommit Repository

4. Click **Create repository**
5. Repository name: `aws-learning-private`
6. Description: `Private AWS infrastructure scripts`
7. Tags: Key=`Project` Value=`stage-00`
8. Click **Create**

**📸 Screenshot:** Capture the CodeCommit repository page after creation

9. Note the HTTPS clone URL: `https://git-codecommit.us-east-1.amazonaws.com/v1/repos/aws-learning-private`

### Generate HTTPS Credentials for CodeCommit

10. Go to IAM Console → Users → `cli-learning-user`
11. Click **Security credentials** tab
12. Scroll to **HTTPS Git credentials for AWS CodeCommit**
13. Click **Generate credentials**
14. Download the credentials CSV (username + password)

**📸 Screenshot:** Capture the Security credentials tab showing CodeCommit credentials section

### Clone and Use CodeCommit Repo

```bash
# Configure git to use credential helper
git config --global credential.helper \
    '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

# Clone the CodeCommit repo
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/aws-learning-private

cd aws-learning-private

# Create a file and commit
echo "# Private AWS Scripts" > README.md
git add README.md
git commit -m "chore: initialize repository"
git push origin main

# Verify in console: refresh the CodeCommit repo page — README.md should appear
```

---

## Console Navigation Quick Reference

### GitHub

| Task | How to Get There |
|------|-----------------|
| Create repository | GitHub.com → + icon → New repository |
| Create branch | Repo page → branch dropdown → type new name |
| Create PR | Repo → Pull requests → New pull request |
| Merge PR | Open PR → Merge pull request → Confirm merge |
| Delete branch | After merge → Delete branch |
| View all PRs | Repo → Pull requests tab |
| Revoke PAT | GitHub Settings → Developer settings → Personal access tokens |

### AWS CodeCommit Console

| Task | How to Get There |
|------|-----------------|
| Create repo | CodeCommit → Create repository |
| Browse repo | CodeCommit → [repo name] → Code |
| View commits | CodeCommit → [repo name] → Commits |
| Compare branches | CodeCommit → [repo name] → Branches → Compare |
| Create pull request | CodeCommit → [repo name] → Pull requests → Create |
| Delete repo | CodeCommit → [repo name] → Settings → Delete repository |

---

*End of steps_awsconsoleui.md — Project 0.3*
