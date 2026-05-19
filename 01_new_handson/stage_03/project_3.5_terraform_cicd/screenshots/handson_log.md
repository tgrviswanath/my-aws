# Hands-on Log — Project 3.5: Terraform CI/CD Pipeline

**Date:** 2026-05-17
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**GitHub Repo:** tgrviswanath/terraform-cicd-aws

---

## Project Description

This project automates Terraform using **GitHub Actions CI/CD with OIDC authentication** — no stored AWS credentials anywhere. Pull requests automatically run `terraform plan` and post the output as a PR comment. Merging to main automatically runs `terraform apply`. A daily scheduled workflow detects infrastructure drift.

**Why this project matters:**
In Projects 3.1–3.4, Terraform was run manually from a local machine. That doesn't scale — different team members run different versions, there's no audit trail, and secrets get stored on laptops. This project solves all of that: infrastructure changes only happen through reviewed, approved, version-controlled pull requests.

**Pipeline Flow:**
```
Developer pushes feature branch
    → PR opened
    → GitHub Actions: fmt check + validate + plan
    → Plan posted as PR comment (reviewer sees exactly what changes)
    → PR approved and merged to main
    → GitHub Actions: apply runs automatically
    → Infrastructure updated in AWS
    → Daily drift detection catches any manual console changes
```

**Resources created:**
| Category | Resource | Cost |
|----------|----------|------|
| IAM | OIDC Provider (GitHub) | $0 |
| IAM | Role: github-actions-terraform | $0 |
| S3 | App bucket: handson-cicd-demo-dev-495331821583 | $0 (free tier) |
| S3 | Versioning + encryption + public access block | $0 |
| SNS | Topic: handson-pipeline-alerts | $0 |
| Remote State | S3 + DynamoDB (from Project 3.4) | ~$0.02/month |
| **Total** | | **~$0.02/month** |

---

## File Structure

```
project_3.5_terraform_cicd/
├── .github/
│   └── workflows/
│       ├── terraform-pr.yml      ← plan on pull request
│       ├── terraform-apply.yml   ← apply on merge to main
│       └── terraform-drift.yml   ← daily drift detection
├── terraform/
│   ├── main.tf                   ← S3 bucket + SNS topic + outputs
│   └── backend.tf                ← S3 remote state (from Project 3.4)
├── code/
│   └── pipeline_trigger.py       ← Python helper to trigger workflows
├── docs/
│   └── architecture.md
├── github-trust-policy.json      ← IAM trust policy for OIDC role
├── screenshots/
│   └── handson_log.md            ← This file
├── cost_estimate.md
├── steps.md
└── README.md
```

---

## Prerequisites

### Pre-req 1 — AWS CLI Authentication

**Command run:**
```
aws sts get-caller-identity
```

**Output received:**
```json
{
    "UserId": "AIDAXGVATZAHVJ3RFFKKR",
    "Account": "495331821583",
    "Arn": "arn:aws:iam::495331821583:user/vswnth1"
}
```

**My observation:**
- Authenticated as IAM user vswnth1 — correct, not root
- Account ID 495331821583 is used in the S3 bucket name to ensure global uniqueness
- This is the last project where we run Terraform locally — after this, GitHub Actions runs it

**Verification:** OK — AWS CLI configured correctly

[Screenshot: 00_aws_cli_auth.png]
> Terminal showing aws sts get-caller-identity output

---

### Pre-req 2 — GitHub Repository Created

**Steps taken:**
```
GitHub → New repository
Name: terraform-cicd-aws
Visibility: Public
→ Created and cloned locally
```

**My observation:**
- The repo name must match exactly what is in the trust policy: `repo:tgrviswanath/terraform-cicd-aws:*`
- If the repo name does not match, GitHub Actions will get Access Denied from AWS STS
- The `.github/workflows/` folder must be at the repo root — not inside a subfolder

**Verification:** OK — Repo created at github.com/tgrviswanath/terraform-cicd-aws

[Screenshot: 00_github_repo_created.png]
> GitHub showing the new terraform-cicd-aws repository

---

### Pre-req 3 — Remote State Backend Ready (from Project 3.4)

**Backend configuration (backend.tf):**
```hcl
terraform {
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "stage-03/project-3.5/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
```

**My observation:**
- Reusing the S3 bucket and DynamoDB table from Project 3.4 bootstrap
- State key is unique: `stage-03/project-3.5/terraform.tfstate` — no collision with other projects
- Remote state is essential for CI/CD — GitHub Actions runners are ephemeral, they cannot use local state

**Verification:** OK — S3 bucket and DynamoDB table exist from Project 3.4

---

## Phase 1 — OIDC Setup (GitHub to AWS Trust)

### Step 1 — Create GitHub OIDC Provider in AWS

**Command run:**
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**Output received:**
```json
{
    "OpenIDConnectProviderArn": "arn:aws:iam::495331821583:oidc-provider/token.actions.githubusercontent.com"
}
```

**What happened:**
- AWS now trusts JWTs issued by GitHub's OIDC provider
- This is a one-time setup per AWS account — not per repo
- The thumbprint is GitHub's TLS certificate fingerprint — AWS uses it to verify the JWT

**My observation:**
- OIDC = OpenID Connect — a standard for identity federation
- GitHub acts as the Identity Provider (IdP), AWS acts as the Service Provider (SP)
- No passwords or access keys are exchanged — only cryptographically signed JWTs
- This is the AWS-recommended way to authenticate CI/CD pipelines — no long-lived secrets

**Verification:** OK — OIDC provider created in IAM console

[Screenshot: 01_oidc_provider_created.png]
> IAM Console → Identity providers showing token.actions.githubusercontent.com

---

### Step 2 — Create IAM Role with Trust Policy

**Trust policy file (github-trust-policy.json):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::495331821583:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:tgrviswanath/terraform-cicd-aws:*"
      }
    }
  }]
}
```

**Commands run:**
```bash
aws iam create-role \
  --role-name github-actions-terraform \
  --assume-role-policy-document file://github-trust-policy.json

aws iam attach-role-policy \
  --role-name github-actions-terraform \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

**Output received:**
```json
{
    "Role": {
        "RoleName": "github-actions-terraform",
        "Arn": "arn:aws:iam::495331821583:role/github-actions-terraform"
    }
}
```

**What the trust policy does:**
- `Principal.Federated` — only the GitHub OIDC provider can request this role
- `StringEquals aud` — the token must be intended for AWS STS
- `StringLike sub` — only workflows from `tgrviswanath/terraform-cicd-aws` can assume this role
- The `*` wildcard allows any branch/tag in that repo

**My observation:**
- The `sub` condition is the critical security control — without it, ANY GitHub repo could assume this role
- `PowerUserAccess` is used for learning — in production, use a custom policy with least privilege
- The role issues temporary credentials valid for 1 hour — much safer than long-lived access keys
- Role ARN: `arn:aws:iam::495331821583:role/github-actions-terraform`

**Verification:** OK — Role created with correct trust policy

[Screenshot: 02_iam_role_created.png]
> IAM Console → Roles → github-actions-terraform showing trust relationship

---

### Step 3 — Add GitHub Repository Secret

**Steps taken:**
```
GitHub → terraform-cicd-aws repo → Settings → Secrets and variables → Actions
→ New repository secret
Name:  AWS_ROLE_ARN
Value: arn:aws:iam::495331821583:role/github-actions-terraform
→ Add secret
```

**My observation:**
- The secret is encrypted and never shown again after saving
- GitHub Actions workflows reference it as `${{ secrets.AWS_ROLE_ARN }}`
- This is the ONLY secret needed — no AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
- Compare to the old way: storing long-lived access keys as secrets (risky, needs rotation)

**Verification:** OK — Secret AWS_ROLE_ARN added to repository

[Screenshot: 03_github_secret_added.png]
> GitHub → Settings → Secrets showing AWS_ROLE_ARN (value hidden)

---

## Phase 2 — GitHub Actions Workflows

### Workflow 1: terraform-pr.yml (Plan on Pull Request)

**File:** `.github/workflows/terraform-pr.yml`
**Trigger:** Any PR to `main` that changes files in `terraform/**`

**Steps in the workflow:**
```
1. Checkout code
2. Configure AWS credentials via OIDC   ← no secrets, just role ARN
3. Setup Terraform v1.7.5
4. terraform fmt -check -recursive      ← fail if code not formatted
5. terraform init                       ← initialize with S3 backend
6. terraform validate -no-color         ← check syntax
7. terraform plan -out=plan.tfplan      ← generate plan
8. Post plan output as PR comment       ← reviewer sees the diff
9. Fail if plan failed
```

**Key OIDC step in the workflow:**
```yaml
- name: Configure AWS credentials via OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ap-south-1
```

**My observation:**
- `id-token: write` permission is required in the workflow — without it, GitHub will not issue the JWT
- `pull-requests: write` permission is required to post the PR comment
- `continue-on-error: true` on fmt and plan — so we can still post the comment even if they fail
- The plan output is truncated to 60,000 characters — GitHub PR comments have a size limit

---

### Workflow 2: terraform-apply.yml (Apply on Merge)

**File:** `.github/workflows/terraform-apply.yml`
**Trigger:** Push to `main` branch that changes files in `terraform/**`

**Steps in the workflow:**
```
1. Checkout code
2. Configure AWS credentials via OIDC
3. Setup Terraform v1.7.5
4. terraform init
5. terraform plan -out=plan.tfplan     ← fresh plan (not the PR plan)
6. terraform apply -auto-approve plan.tfplan  ← apply the exact saved plan
7. Post outputs to GitHub workflow summary
```

**My observation:**
- A fresh plan is run before apply — the PR plan could be stale if main changed since the PR was opened
- `plan -out=plan.tfplan` then `apply plan.tfplan` ensures apply runs exactly what was planned
- `environment: production` in the job requires manual approval in GitHub Environments settings
- The workflow summary shows Terraform outputs — useful for seeing what was created

---

### Workflow 3: terraform-drift.yml (Daily Drift Detection)

**File:** `.github/workflows/terraform-drift.yml`
**Trigger:** Daily at 8am UTC + manual trigger

**Steps in the workflow:**
```
1. terraform init
2. terraform plan -detailed-exitcode
   Exit code 0 = no changes (no drift)
   Exit code 2 = changes detected (DRIFT!)
   Exit code 1 = error
3. Report result to workflow summary
4. Fail the workflow if drift detected
```

**My observation:**
- `-detailed-exitcode` is the key flag — without it, `terraform plan` always exits 0 even if changes exist
- `terraform_wrapper: false` must be set in setup-terraform — the wrapper intercepts exit codes
- Drift = someone made a manual change in the AWS Console that Terraform does not know about
- When drift is detected, the team must decide: import the change into Terraform, or revert it

---

## Phase 3 — Testing the Pipeline

### Step 1 — Initial terraform init (local, one-time)

**Command run:**
```bash
cd terraform
terraform init
```

**Output received:**
```
Initializing the backend...
Successfully configured the backend "s3"!

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**My observation:**
- Backend initialized to S3 — state will be stored at `stage-03/project-3.5/terraform.tfstate`
- This local init is only needed once to generate `.terraform.lock.hcl`
- The lock file must be committed to git — GitHub Actions uses it to install the exact same provider version

**Verification:** OK — Backend connected, provider downloaded

[Screenshot: 04_terraform_init_local.png]
> Terminal showing "Successfully configured the backend s3!" and "Terraform has been successfully initialized!"

---

### Step 2 — Push Feature Branch and Open PR

**Commands run:**
```bash
git checkout -b feature/test-pipeline
git add .
git commit -m "feat: add pipeline test trigger comment"
git push origin feature/test-pipeline
# Opened PR on GitHub
```

**GitHub Actions triggered automatically:**
```
Workflow: Terraform Plan (PR)
Status: Running
```

**My observation:**
- The workflow triggered within seconds of the PR being opened
- GitHub Actions runner is a fresh Ubuntu VM — it has no prior state
- The OIDC exchange happens in the `configure-aws-credentials` step — takes ~2 seconds
- `terraform init` on the runner downloads the provider fresh every time

[Screenshot: 05_pr_workflow_running.png]
> GitHub Actions showing the Terraform Plan workflow running on the PR

---

### Step 3 — terraform fmt Check

**Workflow step output:**
```
Run terraform fmt -check -recursive
```

**Result:** Passed

**My observation:**
- `fmt -check` does NOT modify files — it only checks and exits non-zero if formatting is wrong
- If this fails, the PR is blocked — enforces consistent formatting across the team
- Run `terraform fmt` locally before pushing to avoid this failure

[Screenshot: 06_fmt_check_passed.png]
> GitHub Actions step showing terraform fmt check passed

---

### Step 4 — terraform validate

**Workflow step output:**
```
Run terraform validate -no-color
Success! The configuration is valid.
```

**Result:** Passed

**My observation:**
- `validate` checks syntax and internal consistency — does NOT connect to AWS
- It catches errors like referencing a variable that does not exist
- Much faster than plan — runs in under 1 second

---

### Step 5 — terraform plan (in CI)

**Workflow step output:**
```
data.aws_caller_identity.current: Reading...
data.aws_caller_identity.current: Read complete after 0s [id=495331821583]

  # aws_s3_bucket.app will be created
  + resource "aws_s3_bucket" "app" {
      + bucket = "handson-cicd-demo-dev-495331821583"
      + tags   = { "Environment" = "dev", "ManagedBy" = "terraform-cicd", ... }
    }

  # aws_s3_bucket_public_access_block.app will be created
  # aws_s3_bucket_server_side_encryption_configuration.app will be created
  # aws_s3_bucket_versioning.app will be created
  # aws_sns_topic.pipeline_alerts will be created

Plan: 5 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + account_id    = "495331821583"
  + bucket_arn    = (known after apply)
  + bucket_name   = "handson-cicd-demo-dev-495331821583"
  + environment   = "dev"
  + sns_topic_arn = (known after apply)
```

**My observation:**
- Plan ran successfully inside GitHub Actions — OIDC authentication worked
- `data.aws_caller_identity.current` resolved to account 495331821583 — confirms AWS connection
- Bucket name includes account ID — globally unique, no random suffix needed
- 5 resources to create: S3 bucket + versioning + encryption + public access block + SNS topic

[Screenshot: 07_plan_in_ci.png]
> GitHub Actions showing terraform plan output with "Plan: 5 to add"

---

### Step 6 — Plan Posted as PR Comment

**PR comment posted automatically:**
```
#### Terraform Format   `success`
#### Terraform Init     `success`
#### Terraform Validate `success`
#### Terraform Plan     `success`

Show Plan:
  Plan: 5 to add, 0 to change, 0 to destroy.

Pushed by: @tgrviswanath, Action: pull_request
```

**My observation:**
- The reviewer can see exactly what will change without leaving GitHub
- The plan is collapsed in a details block — keeps the PR clean
- If the plan shows unexpected changes, the reviewer can reject the PR before anything touches AWS
- This is the core value of "plan on PR" — infrastructure review is now part of code review

**Verification:** OK — Plan comment visible on PR

[Screenshot: 08_plan_pr_comment.png]
> GitHub PR showing the Terraform plan posted as a comment with fmt/validate/plan status

---

### Step 7 — Merge PR to Main (triggers Apply)

**Steps taken:**
```
GitHub → PR → Approve → Merge pull request → Confirm merge
```

**Apply workflow output:**
```
Terraform Init: OK
Terraform Plan: Plan: 5 to add, 0 to change, 0 to destroy.

aws_sns_topic.pipeline_alerts: Creating...
aws_sns_topic.pipeline_alerts: Creation complete after 0s
  [id=arn:aws:sns:ap-south-1:495331821583:handson-pipeline-alerts]
aws_s3_bucket.app: Creating...
aws_s3_bucket.app: Creation complete after 2s
  [id=handson-cicd-demo-dev-495331821583]
aws_s3_bucket_versioning.app: Creation complete after 1s
aws_s3_bucket_server_side_encryption_configuration.app: Creation complete after 0s
aws_s3_bucket_public_access_block.app: Creation complete after 0s

Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
account_id    = "495331821583"
bucket_arn    = "arn:aws:s3:::handson-cicd-demo-dev-495331821583"
bucket_name   = "handson-cicd-demo-dev-495331821583"
environment   = "dev"
sns_topic_arn = "arn:aws:sns:ap-south-1:495331821583:handson-pipeline-alerts"
```

**My observation:**
- Apply ran automatically on merge — no manual `terraform apply` needed
- The entire process: push → PR → review → merge → apply took ~5 minutes
- State is stored in S3 — the ephemeral GitHub Actions runner does not need to keep it
- Outputs are posted to the GitHub workflow summary — visible in the Actions tab

**Verification:** OK — 5 resources created in AWS via CI/CD pipeline

[Screenshot: 09_apply_workflow_success.png]
> GitHub Actions showing Terraform Apply workflow completed successfully

[Screenshot: 10_apply_workflow_summary.png]
> GitHub Actions workflow summary showing Terraform outputs

---

## Phase 4 — Verify in AWS Console

### S3 Bucket

```
AWS Console → S3 → handson-cicd-demo-dev-495331821583
Versioning:    Enabled
Encryption:    AES256 (server-side)
Public access: Blocked (all 4 settings)
Tags:          ManagedBy = terraform-cicd, Pipeline = github-actions
```

**My observation:**
- The `ManagedBy = terraform-cicd` tag distinguishes CI/CD-managed resources from manually created ones
- `Pipeline = github-actions` tag provides full audit trail — you know exactly how this was created
- Public access is fully blocked — secure by default

**Verification:** OK — Bucket exists with correct configuration

[Screenshot: 11_s3_bucket_console.png]
> S3 Console showing handson-cicd-demo-dev-495331821583 with versioning enabled

[Screenshot: 12_s3_bucket_properties.png]
> S3 bucket Properties tab showing versioning enabled, encryption AES256, public access blocked

---

### SNS Topic

```
AWS Console → SNS → Topics → handson-pipeline-alerts
ARN:  arn:aws:sns:ap-south-1:495331821583:handson-pipeline-alerts
Type: Standard
```

**Verification:** OK — SNS topic created

[Screenshot: 13_sns_topic_console.png]
> SNS Console showing handson-pipeline-alerts topic

---

### Remote State in S3

```
AWS Console → S3 → handson-terraform-state-495331821583
→ stage-03/project-3.5/terraform.tfstate
Size: ~3KB
```

**My observation:**
- State file is stored in S3 — not on the GitHub Actions runner (which is destroyed after the job)
- The DynamoDB lock table prevented concurrent applies — only one pipeline can apply at a time
- State is encrypted at rest (S3 bucket has encryption enabled from Project 3.4)

**Verification:** OK — State file stored in S3 at correct key

[Screenshot: 14_remote_state_s3.png]
> S3 Console showing terraform.tfstate file at stage-03/project-3.5/ path

---

## Phase 5 — Drift Detection

### Trigger Drift Detection Manually

**Steps taken:**
```
GitHub → Actions → Terraform Drift Detection → Run workflow
```

**Drift detection output:**
```
Terraform Plan (Drift Check):
  exit_code=0

Report Drift:
  No drift detected — infrastructure matches Terraform state
```

**My observation:**
- Exit code 0 = no changes = no drift — infrastructure exactly matches Terraform state
- `-detailed-exitcode` is what makes this work — standard plan always exits 0
- `terraform_wrapper: false` is required — the Terraform wrapper intercepts exit codes and breaks this
- Drift detection only catches changes to resources Terraform manages — not new unmanaged resources

[Screenshot: 15_drift_detection_passed.png]
> GitHub Actions showing drift detection workflow with "No drift detected"

---

## Summary

### All Resources Created

| Resource | Name / ID | Status |
|----------|-----------|--------|
| IAM OIDC Provider | token.actions.githubusercontent.com | Active |
| IAM Role | github-actions-terraform | Active |
| S3 Bucket | handson-cicd-demo-dev-495331821583 | Created via CI/CD |
| S3 Versioning | Enabled | Active |
| S3 Encryption | AES256 | Active |
| S3 Public Access Block | All blocked | Active |
| SNS Topic | handson-pipeline-alerts | Active |
| Remote State | stage-03/project-3.5/terraform.tfstate | In S3 |

### Pipeline Workflow Summary

| Trigger | Workflow | Steps | Result |
|---------|----------|-------|--------|
| PR opened | terraform-pr.yml | fmt + validate + plan + PR comment | Passed |
| Merge to main | terraform-apply.yml | init + plan + apply + summary | 5 resources created |
| Manual trigger | terraform-drift.yml | init + plan -detailed-exitcode | No drift |

### Command Summary

| Command | Where | Touches AWS? | Result |
|---------|-------|-------------|--------|
| `aws iam create-open-id-connect-provider` | Local | Yes | OIDC provider created |
| `aws iam create-role` | Local | Yes | IAM role created |
| `terraform init` | Local (one-time) | Yes (S3 backend) | Lock file generated |
| `terraform fmt -check` | GitHub Actions | No | Formatting verified |
| `terraform validate` | GitHub Actions | No | Syntax verified |
| `terraform plan` | GitHub Actions | No (read-only) | Plan posted to PR |
| `terraform apply` | GitHub Actions | Yes | 5 resources created |
| `terraform plan -detailed-exitcode` | GitHub Actions | No (read-only) | No drift detected |

### Key Observations from This Project

1. **OIDC eliminates stored secrets** — no AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY anywhere
2. **Trust policy `sub` condition is critical** — without it, any GitHub repo could assume the role
3. **`plan -out` then `apply plan.tfplan`** — apply runs exactly what was planned, no surprises
4. **`id-token: write` permission is required** — GitHub will not issue the JWT without it
5. **`terraform_wrapper: false`** — required for drift detection to get real exit codes
6. **Remote state is essential for CI/CD** — ephemeral runners cannot use local state
7. **`fmt -check` enforces team standards** — PR fails if code is not formatted
8. **Drift detection exit codes**: 0 = no changes, 2 = drift, 1 = error
9. **State locking via DynamoDB** — prevents two pipeline runs from applying simultaneously
10. **`ManagedBy = terraform-cicd` tag** — distinguishes pipeline-managed from manually created resources

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| GitHub Actions (free tier) | ~10 min total | $0.00 |
| IAM OIDC + Role | Permanent | $0.00 |
| S3 bucket (empty) | ~30 min | $0.00 |
| SNS topic | ~30 min | $0.00 |
| Remote state S3 reads/writes | ~10 operations | ~$0.001 |
| **Total** | | **~$0.001** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | 00_aws_cli_auth.png | aws sts get-caller-identity output | Add screenshot |
| 2 | 00_github_repo_created.png | GitHub showing terraform-cicd-aws repository | Add screenshot |
| 3 | 01_oidc_provider_created.png | IAM → Identity providers showing GitHub OIDC | Add screenshot |
| 4 | 02_iam_role_created.png | IAM → Roles → github-actions-terraform trust policy | Add screenshot |
| 5 | 03_github_secret_added.png | GitHub → Settings → Secrets showing AWS_ROLE_ARN | Add screenshot |
| 6 | 04_terraform_init_local.png | Local terraform init with S3 backend success | Add screenshot |
| 7 | 05_pr_workflow_running.png | GitHub Actions PR workflow running | Add screenshot |
| 8 | 06_fmt_check_passed.png | terraform fmt check step passed | Add screenshot |
| 9 | 07_plan_in_ci.png | terraform plan output in GitHub Actions | Add screenshot |
| 10 | 08_plan_pr_comment.png | PR comment showing plan with fmt/validate/plan status | Add screenshot |
| 11 | 09_apply_workflow_success.png | Apply workflow completed successfully | Add screenshot |
| 12 | 10_apply_workflow_summary.png | Workflow summary showing Terraform outputs | Add screenshot |
| 13 | 11_s3_bucket_console.png | S3 Console showing handson-cicd-demo bucket | Add screenshot |
| 14 | 12_s3_bucket_properties.png | S3 Properties — versioning, encryption, public access | Add screenshot |
| 15 | 13_sns_topic_console.png | SNS Console showing handson-pipeline-alerts | Add screenshot |
| 16 | 14_remote_state_s3.png | S3 showing terraform.tfstate at project-3.5 path | Add screenshot |
| 17 | 15_drift_detection_passed.png | Drift detection workflow — no drift detected | Add screenshot |

Save all screenshots to:
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.5_terraform_cicd\screenshots\

---

*Author: Viswanath TGR*
*LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
