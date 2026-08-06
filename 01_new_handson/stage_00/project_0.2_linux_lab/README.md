# Project 0.2 — Linux Lab

**Stage:** 00 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** $0

Practice Linux fundamentals directly in AWS using CloudShell — a browser-based shell that requires no EC2 instance and no SSH key. Covers file system navigation, bash scripting, file permissions, process management, and networking commands (`curl`, `ping`, `netstat`), plus text processing with `grep`, `awk`, and `sed`. Everything runs inside the browser against a real Linux environment backed by AWS.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| AWS CloudShell | Browser-based Linux shell with pre-installed AWS CLI | Free |
| EC2 (optional) | Amazon Linux 2023 instance for SSH practice | Free tier: 750 h/month t2.micro |
| IAM | Execution role attached to CloudShell session | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| AWS Console login | Browser access to console.aws.amazon.com |
| CloudShell session | Launched from console toolbar (>_ icon) |
| Bash scripts | Written in-session or uploaded via CloudShell Actions → Upload |

### Output
| Type | Description |
|------|-------------|
| Working bash scripts | `hello.sh`, `sys_info.sh` saved in `/home/cloudshell-user/` |
| AWS CLI output | `aws s3 ls`, `aws ec2 describe-instances` returning real data |
| Text processing results | `grep`, `awk`, `sed` transformations on log-format files |
| Persistent files | Scripts survive session restarts (1 GB persistent storage) |

---

## Architecture

```
Browser
  │ HTTPS → console.aws.amazon.com
  ▼
AWS CloudShell (us-east-1)
  ├── 1 vCPU, 2 GB RAM, Amazon Linux 2
  ├── /home/cloudshell-user/  ← 1 GB persistent storage
  ├── AWS CLI v2 pre-installed
  ├── Python 3, Git, jq pre-installed
  └── IAM execution role (no access keys needed)
        └── AWS API calls go directly via role — no ~/.aws/credentials
```

---

## Quick Start

```cmd
REM Open CloudShell from AWS Console toolbar (>_ icon, top-right)
REM All commands below are entered inside the CloudShell terminal

REM -- File system navigation --
REM pwd, ls, cd, mkdir, cp, mv, rm
ls -la ~
mkdir ~/lab && cd ~/lab

REM -- Write and run a bash script --
REM echo script content then chmod and run
echo '#!/bin/bash' > hello.sh
echo 'echo "Hello from CloudShell on $(date)"' >> hello.sh
chmod 755 hello.sh
./hello.sh

REM -- File permissions --
REM chmod 644 = owner rw, group r, other r
chmod 644 hello.sh

REM -- Text processing --
REM grep filters lines, awk splits fields, sed substitutes text
aws ec2 describe-regions --query "Regions[].RegionName" --output text > regions.txt
grep "us-" regions.txt
awk '{print NR, $1}' regions.txt
sed 's/us-east/US-EAST/g' regions.txt

REM -- Networking --
curl -s https://checkip.amazonaws.com
ping -c 3 amazon.com
```

---

## Data Flow

```
1. Browser launches CloudShell — AWS provisions an ephemeral container (Amazon Linux 2)
2. /home/cloudshell-user/ is mounted from persistent EFS-backed storage — survives reboots
3. Session inherits an IAM execution role — AWS CLI calls work without any credentials file
4. bash scripts run directly in the container — output appears in the terminal
5. AWS CLI commands (aws ec2 describe-instances) go via the attached IAM role → AWS APIs
6. Files written to /home/cloudshell-user/ persist; files outside that path are lost on session end
7. CloudShell session times out after ~20 min of inactivity — scripts and data in home dir remain
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — lab overview |
| `GUIDE.md` | Full walkthrough of each Linux command group |
| `steps.md` | Quick-reference bash commands for CloudShell |
| `steps_awsconsoleui.md` | How to open CloudShell and upload files via the UI |
| `verify.md` | Checklist: scripts run, permissions set, CLI commands work |
| `cost_estimate.md` | Cost breakdown ($0) |
| `scripts/` | Sample bash scripts (`hello.sh`, `sys_info.sh`, `aws_info.sh`) |
| `docs/` | Linux permissions cheatsheet, CloudShell limitations |

---

## Lessons Learned

- CloudShell provides 1 GB persistent storage at `/home/cloudshell-user/` — anything written outside this path (e.g. `/tmp/`) is lost when the session ends
- CloudShell uses an IAM execution role attached to your console session, not your local `~/.aws/credentials` — API calls succeed without any key configuration
- Linux file permissions: `chmod 755` = owner can execute, group and others can read/execute; `chmod 644` = owner read/write, others read-only — scripts need the execute bit (`+x`) to run
- Process management: `ps aux` lists all processes, `kill -9 PID` force-kills, `&` runs in background, `jobs` lists background processes
- Pipe (`|`) and redirect (`>`, `>>`) operators are the backbone of shell scripting — `aws ec2 describe-instances | jq '.[]'` is far more useful than raw JSON output
- `grep -v` (invert match), `awk '{print $2}'` (print second field), `sed 's/old/new/g'` (global substitute) are the three most-used text tools for parsing AWS CLI output
- CloudShell is region-scoped — open it in the same region your resources live in to avoid cross-region latency on CLI calls
