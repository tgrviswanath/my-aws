# AWS Local Dev Environment Setup — GUIDE.md

> **Stage:** 00 — Foundational Setup  
> **Project:** 0.1 — Local Development Environment  
> **Cost:** $0  
> **Time:** 30–60 minutes

---

## 1. Project Overview

### Title: AWS Local Dev Environment Setup

**Problem Statement:**  
Without a consistent local development environment, every AWS hands-on project starts with friction — wrong CLI version, missing credentials, misconfigured profiles. This project eliminates that friction once and for all.

**Objectives:**
- Install AWS CLI v2 on Windows
- Install Python 3.x, Git, and VS Code
- Configure AWS credentials via `aws configure`
- Test connectivity with `aws sts get-caller-identity`
- Understand credential chain and named profiles

**What You Will Learn:**
- How AWS CLI authenticates to AWS APIs
- IAM user vs SSO — when to use each
- The `~/.aws/credentials` and `~/.aws/config` file structure
- How to switch between AWS accounts/profiles

**Skill Level:** Beginner  
**AWS Services Used:** IAM (Identity and Access Management)  
**Tools Required:** Windows 10/11, web browser, terminal (PowerShell or CMD)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   LOCAL MACHINE (Windows)               │
│                                                         │
│  ┌───────────┐    ┌──────────────┐   ┌───────────────┐ │
│  │  VS Code  │    │  AWS CLI v2  │   │  Python 3.x   │ │
│  └───────────┘    └──────┬───────┘   └───────────────┘ │
│                          │                              │
│                  ~/.aws/credentials                     │
│                  ~/.aws/config                          │
└──────────────────────────┼──────────────────────────────┘
                           │ HTTPS (port 443)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     AWS CLOUD                           │
│                                                         │
│  ┌────────────────┐   ┌──────────────────────────────┐  │
│  │   IAM Service  │   │   AWS STS (Security Token    │  │
│  │                │   │   Service)                   │  │
│  │  - Users       │   │   - get-caller-identity      │  │
│  │  - Policies    │   │   - returns Account/ARN      │  │
│  └────────────────┘   └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. AWS CLI reads credentials from `~/.aws/credentials`
2. CLI signs the request using AWS Signature Version 4
3. Request sent over HTTPS to AWS endpoint (e.g., `sts.amazonaws.com`)
4. AWS validates the signature against IAM
5. Response returned as JSON to your terminal

**No cloud resources are deployed.** This project only configures local tooling and tests authentication. Nothing is created in your AWS account beyond the IAM user and access key.

---

## 3. Prerequisites

### System Requirements
| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 (1903+) | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk | 2 GB free | 5 GB free |
| Network | Broadband | Broadband |

### Account Requirements
- [ ] AWS account created (free tier eligible)
- [ ] Admin access to the AWS console (root user or IAM admin)
- [ ] Email address confirmed
- [ ] MFA recommended on root account

### Knowledge Prerequisites
- Basic command line familiarity (cd, mkdir, ls/dir)
- Understanding of what an API key is
- No AWS experience required

### Software to Install (covered in Section 5)
- AWS CLI v2
- Python 3.11+
- Git 2.x
- VS Code (latest)

---

## 4. Project Folder Structure

```
project_0.1_local_dev_setup/
├── GUIDE.md                    ← This file. Full implementation guide.
├── steps_awsconsoleui.md       ← Step-by-step AWS Console UI walkthrough
├── cost_estimate.md            ← Cost breakdown (all $0)
├── scripts/
│   ├── verify_setup.sh         ← Bash script to verify all tools installed
│   └── configure_profile.sh    ← Helper to set up named AWS profile
└── notes/
    └── credential_chain.md     ← Notes on AWS credential resolution order
```

> **Note:** The `scripts/` and `notes/` directories are optional. Create them as you work through the project.

---

## 5. Hands-on Implementation

### 5A. AWS Console Method

#### Prerequisites Check

Before starting the console steps, verify:
- [ ] You can log in to the AWS Management Console
- [ ] You have IAM full access (or root user access)
- [ ] You have NOT already created an IAM user for CLI access
- [ ] You are in the correct AWS region (IAM is global, but check anyway)

```
Console URL: https://console.aws.amazon.com
IAM Console:  https://console.aws.amazon.com/iam
```

---

#### Decision Point 1: IAM User vs SSO (AWS IAM Identity Center)

> This is the most important decision before creating credentials.

| Factor | IAM User + Access Key | AWS SSO / IAM Identity Center |
|--------|----------------------|-------------------------------|
| Setup complexity | Simple | Moderate |
| Best for | Learning, personal projects | Teams, organizations |
| Credential rotation | Manual | Automatic (short-lived) |
| Security risk | Higher (long-lived keys) | Lower |
| AWS recommendation | Not preferred | Preferred |
| Works offline? | Yes | No (needs browser) |

**✅ For this learning project: Use IAM User**  
Reason: Simple setup, works immediately, teaches credential fundamentals.

**❌ For production/team use: Use SSO**  
Reason: Short-lived credentials, centralized access management, no static keys to leak.

> **Decision:** We will use IAM User + Access Key for all stage_00 projects.

---

#### Step-by-Step Console Instructions

**Step 1 — Navigate to IAM**
1. Log in to AWS Console: https://console.aws.amazon.com
2. In the search bar (top), type `IAM`
3. Click **IAM** under Services
4. You are now in the IAM Dashboard

**Step 2 — Create IAM User**
1. In the left sidebar, click **Users**
2. Click the orange **Create user** button (top right)
3. Enter username: `cli-learning-user` (or your preferred name)
4. Check **"Provide user access to the AWS Management Console"** — OPTIONAL for CLI-only use
5. Click **Next**

**Step 3 — Attach Permissions**
1. Select **"Attach policies directly"**
2. In the search box, type `AdministratorAccess`
3. Check the checkbox next to **AdministratorAccess**
4. Click **Next**
5. Review and click **Create user**

> ⚠️ **Security Note:** `AdministratorAccess` is broad. For real projects, use least-privilege policies. For learning, it simplifies things.

**Step 4 — Create Access Key**
1. Click on the newly created user name
2. Click the **Security credentials** tab
3. Scroll down to **Access keys**
4. Click **Create access key**
5. Select **"Command Line Interface (CLI)"**
6. Check the acknowledgment checkbox
7. Click **Next** → **Create access key**
8. **CRITICAL:** Download the `.csv` file OR copy both keys NOW — you cannot see the secret key again

**Expected Outcome:**
```
Access key ID:     YOUR_ACCESS_KEY_ID
Secret access key: YOUR_SECRET_ACCESS_KEY
```

---

#### Troubleshooting (Console Steps)

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot create user | Insufficient permissions | Use root account or ask admin |
| AdministratorAccess not found | Searching wrong term | Search exactly "AdministratorAccess" |
| Access key won't create | Reached key limit (2 max) | Delete an existing key first |
| Lost the secret key | Closed dialog too early | Deactivate key, create new one |

---

### 5B. AWS CLI Method

#### Install AWS CLI v2 on Windows

```powershell
# Option 1: Download and install MSI (recommended)
# Visit: https://aws.amazon.com/cli/
# Direct download link:
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Option 2: Via winget
winget install -e --id Amazon.AWSCLI

# Verify installation
aws --version
# Expected output: aws-cli/2.x.x Python/3.x.x Windows/10 exe/AMD64
```

#### Install Supporting Tools

```powershell
# Install Python (via winget)
winget install -e --id Python.Python.3.11

# Verify Python
python --version
# Expected: Python 3.11.x

# Install Git
winget install -e --id Git.Git

# Verify Git
git --version
# Expected: git version 2.x.x.windows.x

# Install VS Code
winget install -e --id Microsoft.VisualStudioCode
```

#### Configure AWS CLI

```bash
# Run interactive configuration
aws configure

# You will be prompted for:
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json

# Verify the files were created
# Windows path: C:\Users\<YourUsername>\.aws\
dir %USERPROFILE%\.aws\
```

#### Test Connectivity

```bash
# This is the most important verification command
aws sts get-caller-identity

# Expected output:
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/cli-learning-user"
}

# Also test S3 list (no buckets yet, but should not error)
aws s3 ls
# Expected: (empty output, no error = success)

# Check your IAM username
aws iam get-user
```

#### Configure a Named Profile (Optional but Recommended)

```bash
# Create a named profile for this learning environment
aws configure --profile learning

# Use the named profile
aws sts get-caller-identity --profile learning

# Set as default for the session (PowerShell)
$env:AWS_PROFILE = "learning"

# Set as default for the session (CMD)
set AWS_PROFILE=learning
```

---

## 6. Code Deep Dive

### The `~/.aws/credentials` File

```ini
# C:\Users\<YourUsername>\.aws\credentials
# This file stores long-term credentials

[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY

[learning]
aws_access_key_id = YOUR_LEARNING_ACCESS_KEY_ID
aws_secret_access_key = YOUR_LEARNING_SECRET_ACCESS_KEY

[production]
aws_access_key_id = YOUR_PROD_ACCESS_KEY_ID
aws_secret_access_key = YOUR_PROD_SECRET_ACCESS_KEY
```

### The `~/.aws/config` File

```ini
# C:\Users\<YourUsername>\.aws\config
# This file stores configuration (region, output format, etc.)

[default]
region = us-east-1
output = json

[profile learning]
region = us-west-2
output = table

[profile production]
region = eu-west-1
output = json
```

> **Note:** In `credentials`, profiles use `[profile-name]`. In `config`, they use `[profile profile-name]` (with the word "profile"). The `[default]` profile is the exception — it's just `[default]` in both files.

### Environment Variable Override

Environment variables take precedence over credential files:

```powershell
# PowerShell — override for current session
$env:AWS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY = "YOUR_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:AWS_PROFILE = "learning"

# Clear overrides
Remove-Item Env:AWS_ACCESS_KEY_ID
Remove-Item Env:AWS_SECRET_ACCESS_KEY
```

### AWS Credential Chain (Resolution Order)

The CLI checks these locations in order, using the first valid credentials found:

```
1. Command line options (--profile, explicit params)
2. Environment variables (AWS_ACCESS_KEY_ID, etc.)
3. AWS SSO session credentials
4. ~/.aws/credentials file
5. ~/.aws/config file (credential_process)
6. Container credentials (ECS task role)
7. Instance profile credentials (EC2 instance role)
```

---

## 7. Verification

Run all of these commands to confirm your setup is complete:

```bash
# 1. Verify AWS CLI version
aws --version
# Expected: aws-cli/2.x.x ...

# 2. Verify identity (most important check)
aws sts get-caller-identity
# Expected: JSON with UserId, Account, Arn

# 3. Verify region is set
aws configure get region
# Expected: us-east-1 (or your chosen region)

# 4. Verify S3 access (lists nothing but should not error)
aws s3 ls
# Expected: empty output or list of buckets

# 5. Verify IAM can be queried
aws iam list-users --query 'Users[*].UserName' --output table
# Expected: table with your IAM username(s)

# 6. Verify Python
python --version && pip --version
# Expected: Python 3.x.x, pip 23.x.x

# 7. Verify Git
git --version
# Expected: git version 2.x.x.windows.x

# 8. Check credential file exists
type %USERPROFILE%\.aws\credentials
# Expected: shows your access key ID (secret is hidden in display)
```

**All 8 checks passing = environment fully configured.**

---

## 8. Observations & Key Learnings

### Credential Chain Order Matters
The credential chain means you can accidentally use the wrong credentials. Always run `aws sts get-caller-identity` at the start of any session to confirm which account/user you're operating as.

### Long-Lived Keys Are a Risk
Access keys are long-lived (they don't expire unless you delete them). If committed to Git by mistake, they can be exploited in minutes. Consider:
- Using `git-secrets` or `truffleHog` to scan for key leaks
- Rotating keys every 90 days
- Using SSO for anything beyond learning

### MFA Can Be Added to IAM Users
For stronger security, you can require MFA for CLI access:
```bash
# Get a session token with MFA
aws sts get-session-token \
  --serial-number arn:aws:iam::123456789012:mfa/cli-learning-user \
  --token-code 123456 \
  --duration-seconds 3600
```

### Profile Switching Workflow
```bash
# See which profile is active
aws configure list

# Quick switch (PowerShell)
$env:AWS_PROFILE = "production"
aws sts get-caller-identity  # verify you switched

# Switch back
$env:AWS_PROFILE = "default"
```

### VS Code Integration
Install the **AWS Toolkit** extension in VS Code for:
- Profile switching in the IDE
- Lambda function local testing
- S3 bucket browsing
- CloudFormation template validation

---

## 9. Screenshots

Document these screenshots for your portfolio/notes:

1. **IAM Users List** — shows your `cli-learning-user` in the console
2. **Security Credentials Tab** — shows the access key created with "Active" status
3. **Access Key Download Dialog** — the final screen before the secret key is hidden
4. **Terminal: `aws --version`** — confirms CLI is installed
5. **Terminal: `aws sts get-caller-identity`** — the JSON response confirming connection
6. **VS Code with AWS Toolkit** — shows profile selector in the bottom status bar

> See `steps_awsconsoleui.md` for annotated screenshots with callouts.

---

## 10. Cleanup

When you are done with this project or want to rotate credentials:

### Deactivate the Access Key (Soft Delete — Recommended First)

1. Go to IAM Console → Users → `cli-learning-user`
2. Click **Security credentials** tab
3. Find the access key
4. Click **Actions** → **Deactivate**
5. The key is disabled but can be reactivated if needed

### Delete the Access Key (Permanent)

1. Follow steps 1–3 above
2. Click **Actions** → **Delete**
3. Type the access key ID to confirm
4. Click **Delete**

### Remove Local Credentials

```powershell
# Remove the credentials file (removes ALL profiles)
Remove-Item %USERPROFILE%\.aws\credentials

# Or manually edit and remove specific profile
notepad %USERPROFILE%\.aws\credentials
```

### Keep the IAM User
The IAM user itself costs nothing. You can keep it and just rotate/delete the access key. When you resume learning, create a new access key and run `aws configure` again.

### Cleanup Checklist
- [ ] Access key deactivated or deleted in IAM console
- [ ] `.aws/credentials` file cleared of sensitive keys
- [ ] No access keys committed to any Git repository
- [ ] VS Code AWS Toolkit profile removed or updated

---

*End of GUIDE.md — Project 0.1: AWS Local Dev Environment Setup*
