# AWS Console UI Steps — Project 0.2: Linux Lab (CloudShell)

> **Purpose:** Step-by-step guide to accessing and using AWS CloudShell  
> **Time:** 15–20 minutes  
> **Cost:** $0

---

## Prerequisites Check

Before starting:
- [ ] Completed Project 0.1 — you have an AWS account and can log in to the console
- [ ] Browser: Chrome, Firefox, Edge, or Safari (latest versions)
- [ ] Pop-up blocker disabled for `console.aws.amazon.com`
- [ ] Stable internet connection
- [ ] No local Linux installation required for CloudShell steps

---

## Step 1 — Access AWS CloudShell

### Open the Console

1. Navigate to https://console.aws.amazon.com
2. Log in with your IAM user (`cli-learning-user`) or root account

### Find the CloudShell Icon

3. Look at the **top navigation bar** of the console
4. Find the **CloudShell icon** — it looks like this: `>_`
   - Located between the search bar and the notification bell icon
   - Hovering over it shows tooltip: "CloudShell"

   **📸 Screenshot:** Capture the top navigation bar with the CloudShell icon highlighted

### Decision Point 1: Browser-based CloudShell vs Local Terminal

| Situation | Use CloudShell | Use Local Terminal (WSL2/PowerShell) |
|-----------|---------------|--------------------------------------|
| Quick AWS command | ✅ Faster, no auth needed | Takes longer to switch apps |
| Writing a bash script | ❌ 1 GB limit, session expires | ✅ Unlimited, persistent |
| Teaching someone remotely | ✅ Screen share + browser | Depends on their setup |
| Working offline | ❌ Needs internet | ✅ Works offline |
| Long-running process | ❌ Sessions timeout in 20 min | ✅ Runs indefinitely |

> **Decision: CloudShell is perfect for this lab** — no setup, auto-authenticated, browser-only.

5. Click the CloudShell icon (`>_`)
6. A loading panel appears at the **bottom** of the console

   **📸 Screenshot:** Capture the loading state: "Creating your environment, this may take a few minutes..."

7. Wait 15–45 seconds for initialization
8. The panel turns into a bash terminal

### Verify CloudShell Environment

```bash
# Confirm you're in CloudShell
hostname
# Output: ip-10-x-x-x (an AWS IP address, not your local machine)

# Check the operating system
cat /etc/os-release
# Key line: PRETTY_NAME="Amazon Linux 2023"

# Check who you are
whoami
# Output: cloudshell-user

# Check AWS authentication
aws sts get-caller-identity
```

**📸 Screenshot:** Capture the terminal after `aws sts get-caller-identity` showing JSON output

### Expected Outcome — Step 1

```
[cloudshell-user@ip-10-134-52-21 ~]$ aws sts get-caller-identity
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/cli-learning-user"
}
```

**You are in a Linux terminal, authenticated to AWS, with zero setup.**

### Troubleshooting — Step 1

| Problem | Cause | Solution |
|---------|-------|----------|
| CloudShell icon not visible | Old browser or zoom level | Refresh page, zoom to 100%, or try different browser |
| "Your environment is loading" for >2 min | Slow region or AWS issue | Try a different region from the dropdown |
| Black screen / blank terminal | Browser compatibility | Try Chrome or Edge |
| "CloudShell not available in this region" | Not all regions support it | Switch to us-east-1 or us-west-2 |
| Terminal not accepting input | Click inside the terminal | Click directly on the terminal area |

---

## Step 2 — Run Linux Commands in CloudShell

### Navigation Commands

```bash
# Where are you?
pwd
# Output: /home/cloudshell-user

# What's here?
ls -la
# Output: list of files and directories with permissions

# Create a practice directory
mkdir linux-lab
cd linux-lab
pwd
# Output: /home/cloudshell-user/linux-lab
```

**📸 Screenshot:** Capture `ls -la` output showing permissions, owner, size columns

### File Operations

```bash
# Create a file
echo "Hello from CloudShell" > message.txt

# View it
cat message.txt

# Create a multi-line file
cat > sample_data.txt << 'EOF'
us-east-1,Virginia,active
us-west-2,Oregon,active
eu-west-1,Ireland,active
ap-southeast-1,Singapore,active
sa-east-1,SaoPaulo,inactive
EOF

# View with line numbers
cat -n sample_data.txt
```

### Decision Point 2: When to Use `cat` vs `less` vs `head`/`tail`

| Command | Use When | Example |
|---------|----------|---------|
| `cat` | Small files, pipe into other commands | `cat file.txt \| grep error` |
| `less` | Large files, interactive reading | `less /var/log/syslog` |
| `head -20` | First N lines of a file | `head -20 large_file.txt` |
| `tail -50` | Last N lines (great for logs) | `tail -50 app.log` |
| `tail -f` | Real-time log following | `tail -f /var/log/messages` |

### Search with grep

```bash
# Find active regions
grep "active" sample_data.txt

# Find US regions
grep "^us" sample_data.txt

# Count matches
grep -c "active" sample_data.txt

# Invert match (lines WITHOUT "active")
grep -v "active" sample_data.txt

# Case-insensitive
grep -i "VIRGINIA" sample_data.txt

# Show line numbers
grep -n "us-west" sample_data.txt
```

**📸 Screenshot:** Capture grep output showing matched lines highlighted

### Find Files

```bash
# Find all .txt files in home directory
find ~ -name "*.txt" -type f

# Find files larger than 1KB
find ~ -size +1k

# Find files modified in last 10 minutes
find ~ -mmin -10

# Find and display with details
find ~ -name "*.txt" -exec ls -lh {} \;
```

### Pipes and Redirection

```bash
# Pipe: send output of one command to another
cat sample_data.txt | grep "active" | cut -d',' -f1

# Sort regions alphabetically
cat sample_data.txt | cut -d',' -f1 | sort

# Count unique regions
cat sample_data.txt | cut -d',' -f1 | sort | uniq | wc -l

# Redirect output to file
aws iam list-users --output text > iam_users.txt 2>&1
cat iam_users.txt

# Append to file
echo "--- captured at $(date) ---" >> iam_users.txt

# Redirect errors to separate file
aws ec2 describe-instances 2>errors.txt
cat errors.txt
```

### Combining AWS CLI with Linux Commands

```bash
# Get all IAM user names, one per line
aws iam list-users \
    --query 'Users[*].UserName' \
    --output text \
    | tr '\t' '\n'

# Check if your account has any S3 buckets
aws s3 ls 2>&1 | grep -c "s3://" || echo "No buckets found"

# Get current region
aws configure get region
# OR
echo $AWS_DEFAULT_REGION

# Show all AWS CLI config values
aws configure list
```

**Expected Outcome — Step 2:**  
You can navigate the filesystem, create/read/search files, and combine commands with pipes.

**Troubleshooting — Step 2:**

| Problem | Solution |
|---------|----------|
| `command not found` for a tool | `sudo yum install <package>` in CloudShell |
| Pipe output is empty | Check if input command produced output first |
| `Permission denied` on file | Check permissions with `ls -la`; use `sudo` if needed |
| `grep` returns nothing | Check the pattern and case; try `grep -i` |

---

## Step 3 — Write and Run a Bash Script in CloudShell

### Create a Script

```bash
# Create the script file
cat > aws_health_check.sh << 'EOF'
#!/bin/bash
# AWS Environment Health Check Script
# Project 0.2 — Linux Lab

echo "==========================================="
echo " AWS Environment Health Check"
echo " Date: $(date)"
echo "==========================================="
echo ""

# Check AWS CLI
echo "[1] AWS CLI Version:"
aws --version
echo ""

# Check authentication
echo "[2] Current Identity:"
aws sts get-caller-identity
echo ""

# Check region
echo "[3] Default Region:"
aws configure get region
echo ""

# Check IAM users
echo "[4] IAM Users in account:"
aws iam list-users --query 'Users[*].UserName' --output table
echo ""

echo "==========================================="
echo " Health check complete!"
echo "==========================================="
EOF

# Make it executable
chmod +x aws_health_check.sh

# Verify permissions
ls -la aws_health_check.sh
# Should show: -rwxr-xr-x ... aws_health_check.sh

# Run it
./aws_health_check.sh
```

**📸 Screenshot:** Capture the script output showing all health check sections

### Understanding File Permissions

```
-rwxr-xr-x  1  cloudshell-user  cloudshell-user  512  Jan 15 10:00  aws_health_check.sh
│││││││││
│││││││││└── Other: can execute (x), can read (r), cannot write (-)
│││││││└──── Group: can execute (x), can read (r), cannot write (-)
││││└─────── Owner: can execute (x), can write (w), can read (r)
│││└──────── File type: - = regular file, d = directory, l = symlink
│
└─────────── All permissions combined
```

```bash
# chmod numeric notation:
# 7 = rwx (4+2+1), 5 = r-x (4+0+1), 4 = r-- (4+0+0)
# chmod 755 = rwxr-xr-x (owner: all; group/other: read+execute)
chmod 755 aws_health_check.sh

# chmod symbolic notation:
chmod +x aws_health_check.sh   # add execute for all
chmod -w aws_health_check.sh   # remove write for all
chmod u+x aws_health_check.sh  # add execute for owner only
```

---

## CloudShell Console Tips

### Opening Multiple Terminals
- Click **Actions** (top right of CloudShell) → **New tab** to open a second terminal
- Useful for running a command in one tab while working in another

### Uploading/Downloading Files
- Click **Actions** → **Upload file** to upload from your local machine
- Click **Actions** → **Download file** to download back to local

### Resizing the Panel
- Drag the top edge of the CloudShell panel to resize
- Or click the expand icon to make it full-screen

### Keyboard Shortcuts in CloudShell
| Shortcut | Action |
|----------|--------|
| `Ctrl + C` | Cancel running command |
| `Ctrl + L` | Clear terminal |
| `Tab` | Auto-complete |
| `↑` / `↓` | Navigate command history |
| `Ctrl + R` | Search command history |
| `!!` | Repeat last command |

---

## Console Navigation Quick Reference

| Task | How to Get There |
|------|-----------------|
| Open CloudShell | Top nav bar → `>_` icon |
| Open new CloudShell tab | CloudShell → Actions → New tab |
| Upload file to CloudShell | CloudShell → Actions → Upload file |
| Switch CloudShell region | Close CloudShell → change region → reopen |
| Clear CloudShell home directory | CloudShell → Actions → Delete AWS CloudShell home directory |

---

*End of steps_awsconsoleui.md — Project 0.2*
