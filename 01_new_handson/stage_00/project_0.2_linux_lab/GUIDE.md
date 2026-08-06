# Linux Lab — GUIDE.md

> **Stage:** 00 — Foundational Setup  
> **Project:** 0.2 — Linux Lab (WSL2 + CloudShell)  
> **Cost:** $0  
> **Time:** 30–45 minutes

---

## 1. Project Overview

### Title: Linux Lab — Bash Fundamentals for AWS Engineers

**Problem Statement:**  
AWS infrastructure lives on Linux. EC2 instances, containers, Lambda environments, and CloudShell all run Linux. If you are not comfortable with bash, you will constantly struggle when SSHing into instances, reading logs, writing deployment scripts, and debugging live systems. This project gives you a functional Linux environment and builds the baseline bash skills you need.

**Objectives:**
- Set up WSL2 (Windows Subsystem for Linux) with Ubuntu
- Use AWS CloudShell as a zero-setup cloud-based bash environment
- Practice essential Linux commands: `ls`, `grep`, `find`, pipes, redirection
- Write basic bash scripts
- Understand file permissions, processes, and environment variables

**What You Will Learn:**
- WSL2 installation and Ubuntu setup on Windows
- Essential bash commands for AWS work
- File system navigation and manipulation
- Process management with `ps`, `kill`, `top`
- Writing and executing bash scripts
- When to use CloudShell vs local WSL2

**Skill Level:** Beginner  
**AWS Services Used:** AWS CloudShell (free)  
**Tools Required:** Windows 10/11, web browser, WSL2

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE (Windows)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              WSL2 (Windows Subsystem for Linux)       │   │
│  │                                                       │   │
│  │  Ubuntu 22.04                                         │   │
│  │  ├── /home/username/          (your home dir)         │   │
│  │  ├── /etc/                    (config files)          │   │
│  │  ├── /var/log/                (logs)                  │   │
│  │  └── /mnt/c/                  (Windows C: drive)      │   │
│  │                                                       │   │
│  │  Tools: bash, python3, git, aws cli                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────┬───────────────────────────┘
                                   │ HTTPS (for CloudShell)
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                       AWS CLOUD                              │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │              AWS CloudShell                         │     │
│  │                                                     │     │
│  │  Amazon Linux 2023                                  │     │
│  │  ├── aws cli (pre-installed, pre-authenticated)     │     │
│  │  ├── python3, git, bash                             │     │
│  │  ├── 1 GB persistent storage (/home/cloudshell-user)│     │
│  │  └── runs in your AWS account's region              │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Key Difference:**
- **WSL2** = Linux on your local machine. Full power, full persistence, requires setup.
- **CloudShell** = Linux in AWS. Zero setup, pre-authenticated, limited to 1 GB storage.

---

## 3. Prerequisites

### System Requirements for WSL2
| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Windows 10 version 2004+ (build 19041+) | WSL2 requirement |
| RAM | 4 GB | 8 GB recommended |
| CPU | 64-bit with virtualization enabled | Check BIOS if WSL2 fails |
| Disk | 5 GB free | Ubuntu image download |

### For CloudShell
- AWS account (project 0.1 completed)
- Web browser
- No local installation needed

### Knowledge Prerequisites
- Completed Project 0.1 (AWS CLI configured)
- Comfortable with Windows file system
- No Linux experience required (this project teaches it)

### Check Virtualization Status
```powershell
# Run in PowerShell (admin)
Get-ComputerInfo -Property HyperVisorPresent
# Should return: True
```

---

## 4. Project Folder Structure

```
project_0.2_linux_lab/
├── GUIDE.md                        ← This file
├── steps_awsconsoleui.md           ← CloudShell console walkthrough
├── cost_estimate.md                ← $0 cost breakdown
├── scripts/
│   ├── linux_practice.sh           ← Practice script with common commands
│   ├── aws_linux_combo.sh          ← AWS CLI commands in bash scripts
│   └── file_ops_demo.sh            ← File operations demonstration
└── exercises/
    ├── exercise_01_navigation.md   ← Navigation exercises
    ├── exercise_02_grep_find.md    ← Search exercises
    └── exercise_03_pipes.md        ← Pipe and redirect exercises
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method — CloudShell

#### Prerequisites Check

Before opening CloudShell:
- [ ] AWS Console is accessible (project 0.1 complete)
- [ ] You are logged in to https://console.aws.amazon.com
- [ ] Your region is set (CloudShell is region-specific)
- [ ] Pop-up blocker is not blocking the CloudShell panel

---

#### Decision Point 1: WSL2 vs CloudShell — Which Linux Environment to Use?

| Factor | WSL2 (Local) | AWS CloudShell |
|--------|-------------|----------------|
| Setup required | Yes (~10 min) | None |
| Persistence | Full (your whole disk) | 1 GB only |
| AWS authentication | Must configure separately | Auto-authenticated |
| Internet access | Full | Limited (AWS APIs only) |
| Custom tool install | Yes, anything | Yes, but resets after session |
| Works offline | Yes | No |
| Best for | Development, scripting | Quick AWS CLI tasks |

**✅ Use WSL2 for:** Writing scripts, long-term work, installing custom tools, offline work.  
**✅ Use CloudShell for:** Quick AWS CLI commands, testing without local setup, demos.

> **For this project:** We use CloudShell first (fastest path to a bash prompt), then set up WSL2 for local practice.

---

#### Opening AWS CloudShell

1. Log in to https://console.aws.amazon.com
2. Look at the **top navigation bar** — find the **CloudShell icon** (looks like `>_`)
3. Click the CloudShell icon (it's to the right of the search bar, left of notifications)
4. A terminal panel opens at the bottom of the console
5. Wait 15–30 seconds for the environment to initialize

   **📸 Screenshot:** Capture the console with CloudShell panel open, showing the bash prompt

**Expected bash prompt:**
```
[cloudshell-user@ip-10-x-x-x ~]$
```

#### Verify CloudShell Environment

```bash
# Who are you in CloudShell?
whoami
# Output: cloudshell-user

# What Linux distribution?
cat /etc/os-release | grep PRETTY_NAME
# Output: Amazon Linux 2023

# AWS CLI version
aws --version
# Output: aws-cli/2.x.x ...

# Are you authenticated?
aws sts get-caller-identity
# Output: JSON with your account info (auto-authenticated!)

# What's installed?
python3 --version
git --version
```

**Expected Outcome:**  
You have a bash prompt, you're auto-authenticated to AWS, and basic tools are available.

---

#### CloudShell Exercises

```bash
# ── Navigation ──────────────────────────────────────────────
pwd                  # print working directory
ls                   # list files
ls -la               # long format with hidden files
cd ~                 # go to home directory
mkdir my-lab && cd my-lab  # create and enter directory

# ── File Operations ─────────────────────────────────────────
echo "Hello AWS" > hello.txt    # create file with content
cat hello.txt                   # print file content
cp hello.txt hello-backup.txt   # copy file
mv hello.txt renamed.txt        # rename/move file
rm hello-backup.txt             # delete file

# ── Text Search with grep ────────────────────────────────────
echo -e "apple\nbanana\ngrape" > fruits.txt
grep "an" fruits.txt            # lines containing "an"
grep -i "APPLE" fruits.txt      # case-insensitive search
grep -v "banana" fruits.txt     # lines NOT containing "banana"

# ── Find Files ───────────────────────────────────────────────
find ~ -name "*.txt"            # find all .txt files
find ~ -name "*.txt" -type f    # files only (not dirs)
find ~ -newer renamed.txt       # files newer than renamed.txt

# ── Pipes and Redirection ────────────────────────────────────
ls -la | grep ".txt"            # pipe ls into grep
cat fruits.txt | sort           # sort file contents
cat fruits.txt | wc -l          # count lines
aws iam list-users | grep UserName  # pipe AWS output into grep

# ── Environment Variables ────────────────────────────────────
echo $HOME                      # print home directory
echo $USER                      # print username
export MY_VAR="hello"           # set environment variable
echo $MY_VAR                    # use it
env | grep AWS                  # see AWS-related env vars
```

**Troubleshooting — CloudShell:**

| Problem | Solution |
|---------|----------|
| CloudShell icon not visible | Look for `>_` in top nav; try refreshing |
| "Loading" never finishes | Refresh browser; try different region |
| Session expired | CloudShell sessions timeout after 20 min idle; just reopen |
| Commands not found | CloudShell has a curated set of tools; use `sudo yum install <package>` |
| Files disappeared | CloudShell only persists files in `~/` (home dir); `/tmp` is not persistent |

---

### 5B. Local Method — WSL2 Setup

#### Install WSL2 and Ubuntu

```powershell
# Run PowerShell as Administrator

# Enable WSL and Virtual Machine Platform
wsl --install

# This command:
# 1. Enables "Windows Subsystem for Linux" feature
# 2. Enables "Virtual Machine Platform" feature
# 3. Downloads and installs Ubuntu (default distribution)
# 4. Sets WSL2 as the default version

# Restart Windows when prompted
Restart-Computer
```

After restart, Ubuntu launches automatically and asks for:
```
Enter new UNIX username: yourusername
New password: (type password - it won't show characters)
Retype new password:
```

#### Verify WSL2 Installation

```powershell
# In PowerShell (not WSL)
wsl --list --verbose
# Expected:
#   NAME      STATE   VERSION
# * Ubuntu    Running 2        ← Version 2 = WSL2 ✓

# Check WSL version
wsl --version
```

#### Basic Ubuntu Setup in WSL2

```bash
# In the Ubuntu terminal

# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install useful tools
sudo apt install -y curl wget jq tree unzip

# Install AWS CLI v2 in WSL2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version

# Configure (uses same credentials from project 0.1)
aws configure
# Enter your access key, secret, region, output format

# Test
aws sts get-caller-identity
```

#### Linux Commands Practice in WSL2

```bash
# ── File System Exploration ──────────────────────────────────
ls /                   # root filesystem contents
ls /etc | head -20     # first 20 items in /etc
ls -lh /var/log        # log files with human-readable sizes

# ── Process Management ───────────────────────────────────────
ps aux                 # all running processes
ps aux | grep aws      # filter for AWS-related processes
top                    # interactive process viewer (q to quit)
kill -l                # list all signal types

# ── Disk Usage ───────────────────────────────────────────────
df -h                  # disk free (human readable)
du -sh ~               # disk usage of home directory
du -sh ~/.*            # usage of hidden files/dirs

# ── Text Processing ──────────────────────────────────────────
# Create a sample log file
cat > sample.log << 'EOF'
2024-01-15 10:00:01 INFO  Service started
2024-01-15 10:00:05 DEBUG Config loaded
2024-01-15 10:01:00 ERROR Connection failed
2024-01-15 10:01:30 INFO  Retrying connection
2024-01-15 10:02:00 INFO  Connection restored
EOF

grep "ERROR" sample.log             # find errors
grep -c "INFO" sample.log           # count INFO lines
awk '{print $3}' sample.log         # print third column (log level)
sed 's/INFO/NOTICE/g' sample.log    # replace text

# ── Bash Script Example ──────────────────────────────────────
cat > check_aws.sh << 'EOF'
#!/bin/bash
echo "=== AWS Environment Check ==="
echo "Date: $(date)"
echo "User: $(whoami)"
echo ""
echo "AWS CLI Version:"
aws --version
echo ""
echo "Current Identity:"
aws sts get-caller-identity
echo ""
echo "=== Check Complete ==="
EOF

chmod +x check_aws.sh
./check_aws.sh
```

#### Access Windows Files from WSL2

```bash
# Your Windows C: drive is mounted at /mnt/c/
ls /mnt/c/Users/

# Navigate to Windows desktop
cd /mnt/c/Users/<YourWindowsUsername>/Desktop

# Copy files between Windows and WSL2
cp /mnt/c/Users/<User>/Downloads/somefile.txt ~/
```

---

## 6. Code Deep Dive

### Understanding the Linux File System

```
/                    Root (top of tree)
├── bin/             Essential commands (ls, cat, grep)
├── etc/             Configuration files
├── home/            User home directories
│   └── username/    Your home (~)
├── tmp/             Temporary files (cleared on reboot)
├── usr/             User programs
│   ├── bin/         Standard commands
│   └── local/       Locally installed programs (aws cli)
├── var/             Variable data
│   └── log/         Log files
└── mnt/             Mount points (Windows drives in WSL2)
    └── c/           Your Windows C: drive
```

### Bash Script Anatomy

```bash
#!/bin/bash                     # Shebang: tells OS to use bash
# This is a comment

# Variables
MY_NAME="AWS Engineer"
MY_REGION="us-east-1"

# Command substitution
CURRENT_DATE=$(date +%Y-%m-%d)
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Conditional
if [ -z "$AWS_ACCOUNT" ]; then
    echo "ERROR: Not authenticated to AWS"
    exit 1
else
    echo "Authenticated to account: $AWS_ACCOUNT"
fi

# Loop
for region in us-east-1 us-west-2 eu-west-1; do
    echo "Checking region: $region"
    aws ec2 describe-availability-zones --region $region \
        --query 'AvailabilityZones[0].State' --output text
done
```

### Essential Pipes Pattern for AWS Work

```bash
# Get all IAM user names as a clean list
aws iam list-users \
    --query 'Users[*].UserName' \
    --output text \
    | tr '\t' '\n' \
    | sort

# Find EC2 instances in running state (when you have instances)
aws ec2 describe-instances \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output text \
    | grep "running"

# Count S3 objects in a bucket (when you have buckets)
aws s3 ls s3://your-bucket/ \
    | wc -l
```

---

## 7. Verification

```bash
# Verify WSL2 is running
wsl --list --verbose
# Expected: Ubuntu with VERSION 2

# Verify bash is available
bash --version
# Expected: GNU bash, version 5.x.x

# Verify Linux commands work
echo "test" | grep "test"
# Expected: test

# Verify file operations
touch /tmp/testfile && ls /tmp/testfile && rm /tmp/testfile
# Expected: /tmp/testfile (then removed)

# Verify AWS CLI works in WSL2
aws sts get-caller-identity
# Expected: JSON with account info

# Verify pipes work
echo -e "c\na\nb" | sort
# Expected: a, b, c (sorted)

# Verify script execution
echo '#!/bin/bash
echo "Script works!"' > /tmp/test.sh
chmod +x /tmp/test.sh
/tmp/test.sh
# Expected: Script works!
```

---

## 8. Observations & Key Learnings

### WSL2 vs Native Linux Performance
WSL2 is almost as fast as native Linux for most tasks. The main performance gap is file I/O between Windows and Linux filesystems (`/mnt/c/` access is slower). Keep your projects in the Linux filesystem (`~/projects/`) for best performance.

### CloudShell Limits
- Sessions are idle-terminated after 20 minutes
- Only 1 GB of persistent storage per region
- Certain outbound network connections are restricted
- Cannot run background services or long-running processes

### Bash Scripting for AWS
Bash + AWS CLI is a powerful combination for automation. Even if you eventually use Python or Terraform, understanding bash lets you:
- Write quick one-off scripts
- Debug what Terraform or Ansible is actually running
- Read and understand deployment scripts from others

### Shell Configuration Files
```bash
# ~/.bashrc  — runs for every new interactive shell
# ~/.bash_profile — runs on login
# ~/.profile — portable (also used by sh, dash)

# Add to ~/.bashrc to set AWS profile automatically:
echo 'export AWS_PROFILE=learning' >> ~/.bashrc
echo 'export AWS_DEFAULT_REGION=us-east-1' >> ~/.bashrc
source ~/.bashrc
```

---

## 9. Screenshots

Document these for your notes:

1. **WSL2 Installation** — PowerShell showing `wsl --install` running
2. **Ubuntu First Launch** — username/password setup screen
3. **CloudShell Open** — AWS Console with CloudShell panel at bottom
4. **`aws sts get-caller-identity` in CloudShell** — JSON response
5. **`ls -la` output** — showing Linux file listing with permissions
6. **Bash script execution** — terminal showing script output

---

## 10. Cleanup

### CloudShell
- No cleanup needed — CloudShell is ephemeral
- Persistent files in `~/` will remain in your 1 GB storage
- To clear CloudShell storage: Actions → Delete AWS CloudShell home directory

### WSL2
- WSL2 itself doesn't create AWS resources
- To uninstall Ubuntu from WSL2 (if desired):
  ```powershell
  wsl --unregister Ubuntu
  ```
- To completely remove WSL2:
  ```powershell
  # In PowerShell (admin)
  dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux
  dism.exe /online /disable-feature /featurename:VirtualMachinePlatform
  ```

### AWS Resources
- No AWS resources were created in this project
- CloudShell usage is free and leaves no billable resources

### Cleanup Checklist
- [ ] Any test files in CloudShell home deleted (optional)
- [ ] No scripts committed to public repos with hardcoded credentials
- [ ] WSL2 Ubuntu is set up (keep it — you'll use it in later projects)

---

*End of GUIDE.md — Project 0.2: Linux Lab*
