# Project 0.3 — Git Workflow

**Stage:** 00 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** $0

Set up a production-style Git workflow with AWS CodeCommit as the remote repository. Practise the feature branch model (main → develop → feature branches), write commits in conventional-commit format, create a pull request, and merge. SSH key authentication is configured for CodeCommit so no HTTPS password prompts occur.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| AWS CodeCommit | Managed Git repository hosted in AWS | Free: 5 active users, 50 GB storage, 10,000 Git requests/month |
| IAM | Upload SSH public key; attach CodeCommit access policy | Free |
| Git (local) | Version control client on Windows | Free |
| VS Code | Editor with GitLens extension | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| Local Git install | `git --version` working on Windows |
| AWS IAM user | User with `AWSCodeCommitPowerUser` policy attached |
| SSH key pair | Generated with `ssh-keygen -t rsa -b 4096` |
| IAM SSH public key | Public key uploaded to IAM → Security Credentials |

### Output
| Type | Description |
|------|-------------|
| CodeCommit repository | `my-aws-lab` repo created in AWS |
| `~/.ssh/config` entry | SSH alias `codecommit` pointing to `git-codecommit.us-east-1.amazonaws.com` |
| Feature branch | `feature/add-readme` branched from `develop` |
| Pull request | PR from `feature/add-readme` → `develop` with review and merge |
| Commit history | `git log --oneline --graph` showing branch and merge topology |

---

## Architecture

```
Local Windows machine
  │
  ├── git commit (conventional: feat: add readme)
  │
  └── git push origin feature/add-readme
        │ SSH (port 22) → git-codecommit.us-east-1.amazonaws.com
        ▼
AWS CodeCommit (us-east-1)
  └── Repository: my-aws-lab
        ├── main        ← production-ready, protected
        ├── develop     ← integration branch
        └── feature/add-readme  ← short-lived feature branch
              │ Pull Request (CodeCommit console)
              └── Merge → develop (squash or merge commit)
```

---

## Quick Start

```cmd
REM 1. Generate SSH key pair (run once)
ssh-keygen -t rsa -b 4096 -f %USERPROFILE%\.ssh\codecommit_rsa

REM 2. Upload public key in AWS Console:
REM    IAM → Users → Security credentials → SSH keys for CodeCommit → Upload
REM    Note the SSH Key ID (format: APKAX...)

REM 3. Add SSH config entry (create/edit %USERPROFILE%\.ssh\config)
REM    Host codecommit
REM      HostName git-codecommit.us-east-1.amazonaws.com
REM      User APKAX...  (your SSH Key ID)
REM      IdentityFile ~/.ssh/codecommit_rsa

REM 4. Create CodeCommit repo in AWS Console or via CLI
aws codecommit create-repository --repository-name my-aws-lab --repository-description "AWS hands-on lab"

REM 5. Clone the repo
git clone ssh://codecommit/v1/repos/my-aws-lab
cd my-aws-lab

REM 6. Create develop branch and push
git checkout -b develop
git push -u origin develop

REM 7. Create feature branch
git checkout -b feature/add-readme

REM 8. Make a commit using conventional format
echo # AWS Lab > README.md
git add README.md
git commit -m "feat: add initial README"
git push -u origin feature/add-readme

REM 9. Create pull request in CodeCommit console: feature/add-readme -> develop
REM 10. View history after merge
git fetch --all
git log --oneline --graph --all
```

---

## Data Flow

```
1. ssh-keygen creates a public/private RSA key pair on the local machine
2. Public key is uploaded to IAM — AWS stores the fingerprint, assigns an SSH Key ID
3. ~/.ssh/config maps the CodeCommit hostname to the correct key and User (SSH Key ID)
4. git clone / git push uses SSH — no username/password prompts
5. Feature work is committed locally with conventional-commit message (feat/fix/docs/chore: description)
6. git push sends packfile over SSH to CodeCommit
7. CodeCommit stores the branch and commits in managed Git infrastructure
8. Pull request is created in the console — reviewers can comment per line
9. Merge creates a merge commit on develop; feature branch can be deleted
10. git log --oneline --graph renders the branching topology in ASCII
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — workflow overview |
| `GUIDE.md` | Full walkthrough: SSH setup, repo creation, branching |
| `steps.md` | Windows CMD quick-reference for all Git commands |
| `steps_awsconsoleui.md` | CodeCommit console: create repo, PR, merge walkthrough |
| `verify.md` | Checklist: SSH works, branch exists, PR merged, history correct |
| `cost_estimate.md` | Cost breakdown ($0 under free tier) |
| `.gitignore` | Ignores `.env`, `__pycache__`, `*.pyc`, `terraform/.terraform/` |
| `code/` | Sample Python script committed as the feature branch content |
| `docs/` | Branching diagram, conventional commits reference card |

---

## Lessons Learned

- Feature branches prevent accidental commits to `main` — direct push to `main` can be blocked via CodeCommit branch protection (Approval Rule Template)
- Conventional commits format (`feat:`, `fix:`, `docs:`, `chore:`) makes `git log` machine-readable — tools like `conventional-changelog` can auto-generate release notes from it
- CodeCommit uses the IAM SSH Key ID (e.g. `APKAX...`) as the SSH username — this is different from your IAM username, which is why the `User` field in `~/.ssh/config` is not your login name
- IAM SSH public keys are separate from EC2 key pairs — one is for CodeCommit Git authentication, the other is for EC2 SSH login; they use different IAM sections
- `git log --oneline --graph --all` is the fastest way to visualize branch topology in the terminal without a GUI
- Squash merge on PR keeps `develop` history clean — one commit per feature instead of every in-progress WIP commit
- `git fetch --all` after a merge updates all remote-tracking branches locally without altering the working tree — always run it before branching off develop again
