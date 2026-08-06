# Project 0.1 — Local Dev Setup

**Stage:** 00 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** $0

Install and configure a full AWS development environment on Windows. Covers AWS CLI v2, Python 3, Git, and VS Code — then wires up IAM credentials so `aws sts get-caller-identity` returns a real Account ID and ARN. Everything subsequent projects depend on starts here.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| AWS CLI v2 | Interact with AWS from CMD | Free |
| IAM | Create access keys for programmatic access | Free |
| STS | Verify credential identity (`get-caller-identity`) | Free |
| Python 3.x | Run boto3 scripts in later projects | Free |
| Git | Version control | Free |
| VS Code | Editor with AWS Toolkit extension | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| Windows machine | No AWS tooling installed yet |
| AWS account | Root or IAM user with AdministratorAccess |
| IAM access key | Access Key ID + Secret Access Key pair |
| Default region | e.g. `us-east-1` |

### Output
| Type | Description |
|------|-------------|
| `~/.aws/credentials` | Named profile with access key stored locally |
| `~/.aws/config` | Default region and output format |
| `aws sts get-caller-identity` | Returns `Account`, `UserId`, `Arn` — confirms working creds |
| `python --version` | Confirms Python 3.x on PATH |
| `git --version` | Confirms Git installed |

---

## Architecture

```
Windows CMD
  │
  ├── aws configure
  │     └── writes ~/.aws/credentials  (access key + secret)
  │     └── writes ~/.aws/config       (region = us-east-1, output = json)
  │
  ├── aws sts get-caller-identity
  │     └── HTTPS → AWS STS endpoint
  │           └── returns Account / UserId / Arn
  │
  └── python / git / code — local tools on PATH
```

---

## Quick Start

```cmd
REM 1. Install AWS CLI v2 (download MSI from aws.amazon.com/cli)
REM    After install, verify:
aws --version

REM 2. Configure credentials (enter Access Key ID, Secret, region, json)
aws configure

REM 3. Verify identity — should return your Account ID and ARN
aws sts get-caller-identity

REM 4. Create a named profile for this project (optional but recommended)
aws configure --profile myaws

REM 5. Test named profile
aws sts get-caller-identity --profile myaws

REM 6. Verify Python
python --version

REM 7. Verify Git
git --version

REM 8. Install boto3 for upcoming projects
pip install boto3
```

---

## Data Flow

```
1. aws configure prompts for Access Key ID, Secret Access Key, region, output format
2. Credentials written to %USERPROFILE%\.aws\credentials under [default] or named profile
3. Region/output written to %USERPROFILE%\.aws\config
4. aws sts get-caller-identity sends a signed HTTPS request to sts.amazonaws.com
5. STS validates the HMAC-SHA256 signature against the stored IAM access key
6. STS returns JSON: { "UserId": "AIDAX...", "Account": "123456789012", "Arn": "arn:aws:iam::..." }
7. CLI prints the JSON — confirms credentials are valid and identity is known
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — setup overview |
| `GUIDE.md` | Step-by-step installation walkthrough |
| `steps.md` | Windows CMD quick-reference commands |
| `steps_awsconsoleui.md` | Console UI walkthrough for creating IAM access keys |
| `verify.md` | Verification checklist for all tools |
| `cost_estimate.md` | Cost breakdown ($0) |
| `code/` | Sample scripts for testing the setup |
| `docs/` | Credential chain diagram, profile notes |

---

## Lessons Learned

- AWS CLI credential chain order: env vars (`AWS_ACCESS_KEY_ID`) → `~/.aws/credentials` → IAM instance role — CLI checks in this exact order, so an env var always wins over the credentials file
- Named profiles (`aws configure --profile name`) let you switch between dev/staging/prod accounts without overwriting `[default]`
- `~/.aws/credentials` stores the raw keys; `~/.aws/config` stores region and output format — they are separate files by design
- IAM users get long-lived access keys; IAM roles use STS to issue short-lived temporary credentials — prefer roles in production
- `aws sts assume-role` returns `AccessKeyId`, `SecretAccessKey`, and a `SessionToken` — all three are required when using temporary creds
- MFA adds a `--serial-number` (ARN of the MFA device) and `--token-code` flag to `assume-role` — essential for sensitive accounts
- Never commit `~/.aws/credentials` to Git — add it to `.gitignore` and use IAM roles or environment variables in CI/CD instead
