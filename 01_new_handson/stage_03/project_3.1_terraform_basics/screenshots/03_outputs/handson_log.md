# Hands-on Log — Project 3.1 Phase 3: Terraform Outputs

**Date:** 2026-05-12
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\03_outputs\`

---

## Phase Description

After `terraform apply`, you need to know what was created — the bucket name, ARN, URL, or a password. Terraform **outputs** export these values. This phase demonstrates 4 output types and 3 ways to read them.

**Why this phase matters:**
In real projects, outputs are how Terraform communicates results to humans, scripts, and CI/CD pipelines. Without outputs, you'd have to manually look up resource IDs in the AWS Console after every apply.

**What you will learn:**
- 4 output types: simple string, sensitive, object, computed URL
- 3 ways to read outputs: `terraform output`, `-raw` (for scripts), `-json` (reveals sensitive)
- How `sensitive = true` protects passwords in ALL terminal output
- How SSM SecureString encrypts values with KMS automatically

**Resources created in this phase:**
| Resource | Name | Cost |
|----------|------|------|
| `random_id.suffix` | hex = `e63a1b07` | $0 |
| `aws_s3_bucket.app` | `outputs-demo-e63a1b07` | $0 |
| `aws_ssm_parameter.db_password` | `/handson/db/password` (SecureString) | $0 |

**Total cost: $0.00**

---

## The main.tf File

```hcl
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
}

provider "aws" { region = "ap-south-1" }

resource "aws_s3_bucket" "app" {
  bucket = "outputs-demo-${random_id.suffix.hex}"
  tags   = { Project = "handson", Stage = "stage-03" }
}

resource "random_id" "suffix" { byte_length = 4 }

resource "aws_ssm_parameter" "db_password" {
  name  = "/handson/db/password"
  type  = "SecureString"
  value = "super-secret-password-123"
}

# Output 1: Simple string
output "bucket_name" {
  value = aws_s3_bucket.app.bucket
}

# Output 2: Sensitive — hidden in terminal
output "db_password" {
  value     = aws_ssm_parameter.db_password.value
  sensitive = true
}

# Output 3: Object — multiple values grouped
output "bucket_info" {
  value = {
    name   = aws_s3_bucket.app.bucket
    arn    = aws_s3_bucket.app.arn
    region = aws_s3_bucket.app.region
  }
}

# Output 4: Computed URL — built from resource values
output "bucket_console_url" {
  value = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.app.bucket}"
}
```

---

## Hands-on Steps

### Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
- Installing hashicorp/random v3.8.1...
- Installing hashicorp/aws v5.100.0...
Terraform has been successfully initialized!
```

**My observation:**
- Both providers needed: `aws` for S3 + SSM, `random` for bucket name suffix
- Same versions as previous phases — lock file ensures consistency

**Verification:** ✅ Both providers downloaded

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of terminal showing "Terraform has been successfully initialized!"

---

### Step 2 — terraform plan

**Command run:**
```bash
terraform plan
```

**Key output:**
```
# aws_ssm_parameter.db_password will be created
  + value = (sensitive value)    ← hidden even at plan stage!

Plan: 3 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + bucket_console_url = (known after apply)
  + bucket_info        = { arn, name, region }
  + bucket_name        = (known after apply)
  + db_password        = (sensitive value)    ← hidden in plan too!
```

**My observation:**
- `db_password` shows as `(sensitive value)` even in the plan — before anything is created
- This is `sensitive = true` working — Terraform never reveals sensitive values in any output
- `bucket_info` shows as an object with 3 fields — you can see the structure before apply
- All 4 outputs are visible in the plan — useful for reviewing what will be exported

**Verification:** ✅ Plan shows 3 resources + 4 outputs, sensitive value already hidden

📸 **Screenshot:** `02_terraform_plan.png`
> Take screenshot showing all 4 outputs in "Changes to Outputs", especially `db_password = (sensitive value)`

---

### Step 3 — terraform apply

**Command run:**
```bash
terraform apply
# typed: yes
```

**Output received:**
```
random_id.suffix: Creation complete after 0s [id=5jobBw]
aws_ssm_parameter.db_password: Creation complete after 1s [id=/handson/db/password]
aws_s3_bucket.app: Creation complete after 3s [id=outputs-demo-e63a1b07]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

Outputs:
bucket_console_url = "https://s3.console.aws.amazon.com/s3/buckets/outputs-demo-e63a1b07"
bucket_info = {
  "arn"    = "arn:aws:s3:::outputs-demo-e63a1b07"
  "name"   = "outputs-demo-e63a1b07"
  "region" = "ap-south-1"
}
bucket_name = "outputs-demo-e63a1b07"
db_password = <sensitive>
```

**My observation:**
- `db_password = <sensitive>` — the password is NEVER shown in terminal, even after apply
- `bucket_console_url` is a fully computed URL — you can copy-paste it directly into a browser
- `bucket_info` shows as a grouped object — name, ARN, and region together in one output
- SSM created the parameter as `SecureString` — AWS automatically encrypted it with KMS

**Verification in AWS Console:**
- Opened `bucket_console_url` in browser — confirmed S3 bucket page loaded
- AWS Console → Systems Manager → Parameter Store → `/handson/db/password` → confirmed SecureString type

📸 **Screenshot:** `03_terraform_apply.png`
> Take screenshot showing all 4 outputs, especially `db_password = <sensitive>`

📸 **Screenshot:** `04_s3_bucket_in_console.png`
> Open `bucket_console_url` in browser → screenshot of S3 bucket page

📸 **Screenshot:** `05_ssm_parameter_in_console.png`
> AWS Console → Systems Manager → Parameter Store → `/handson/db/password` → screenshot showing SecureString type

---

### Step 4 — terraform output (all outputs)

**Command run:**
```bash
terraform output
```

**Output received:**
```
bucket_console_url = "https://s3.console.aws.amazon.com/s3/buckets/outputs-demo-e63a1b07"
bucket_info = {
  "arn"    = "arn:aws:s3:::outputs-demo-e63a1b07"
  "name"   = "outputs-demo-e63a1b07"
  "region" = "ap-south-1"
}
bucket_name = "outputs-demo-e63a1b07"
db_password = <sensitive>
```

**My observation:**
- `db_password` is still `<sensitive>` — even with direct `terraform output` command
- `sensitive = true` protects the value in ALL terminal output — plan, apply, and output
- This is the correct behavior — passwords should never appear in terminal logs

**Verification:** ✅ All 4 outputs shown, sensitive value still protected

📸 **Screenshot:** `06_terraform_output.png`
> Take screenshot of terminal showing all 4 outputs

---

### Step 5 — terraform output -raw (for scripts)

**Commands run:**
```bash
terraform output -raw bucket_name
terraform output -raw bucket_console_url
```

**Outputs received:**
```
outputs-demo-e63a1b07
https://s3.console.aws.amazon.com/s3/buckets/outputs-demo-e63a1b07
```

**My observation:**
- `-raw` returns the value with **no quotes** — essential for shell scripts
- Regular `terraform output` returns `"outputs-demo-e63a1b07"` (with quotes)
- `-raw` returns `outputs-demo-e63a1b07` (no quotes) — directly usable in commands
- Real-world use: `BUCKET=$(terraform output -raw bucket_name)` then `aws s3 cp file.txt s3://$BUCKET/`

**Verification:** ✅ Clean values returned without quotes, ready for scripting

📸 **Screenshot:** `07_terraform_output_raw.png`
> Take screenshot showing both `-raw` commands and their clean outputs

---

### Step 6 — terraform output -json (reveal sensitive)

**Command run:**
```bash
terraform output -json db_password
```

**Output received:**
```
"super-secret-password-123"
```

**My observation:**
- `-json` is the **only way** to reveal a sensitive output value
- Regular `terraform output db_password` → `<sensitive>`
- `terraform output -raw db_password` → ERROR (blocked for sensitive values)
- `terraform output -json db_password` → `"super-secret-password-123"` ✅
- **Production note:** Never store real passwords in Terraform code. Use AWS Secrets Manager for application secrets. SSM SecureString is fine for non-critical config.

**Verification:** ✅ Sensitive value revealed only via `-json` flag

📸 **Screenshot:** `08_terraform_output_json_sensitive.png`
> Take screenshot showing the `-json` command revealing the sensitive value

---

### Step 7 — terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes
```

**Output received:**
```
aws_ssm_parameter.db_password: Destruction complete after 0s
aws_s3_bucket.app: Destruction complete after 0s
random_id.suffix: Destruction complete after 0s

Destroy complete! Resources: 3 destroyed.
```

**My observation:**
- All 3 resources destroyed cleanly
- SSM parameter deleted — the encrypted value is gone from AWS
- S3 bucket deleted — the `bucket_console_url` output no longer works

**Verification:** ✅ All resources deleted, cost = $0

📸 **Screenshot:** `09_terraform_destroy.png`
> Take screenshot of terminal showing "Destroy complete! Resources: 3 destroyed"

---

## Summary

### Output Commands Comparison

| Command | Shows sensitive? | Use case |
|---------|-----------------|---------|
| `terraform output` | ❌ `<sensitive>` | View all outputs |
| `terraform output -raw <name>` | ❌ Blocked | Shell scripts, CI/CD |
| `terraform output -json <name>` | ✅ Revealed | Only way to see sensitive value |

### 4 Output Types

| Type | Code | Result | Use case |
|------|------|--------|---------|
| Simple string | `value = resource.attr` | `"outputs-demo-e63a1b07"` | Single value |
| Sensitive | `sensitive = true` | `<sensitive>` | Passwords, keys |
| Object | `value = { key = val }` | `{ name, arn, region }` | Group related values |
| Computed URL | `value = "https://.../${attr}"` | Full URL | Direct links |

### Key Observations from This Phase

1. **`sensitive = true` hides value everywhere** — plan, apply, output, logs
2. **`-json` is the only way to reveal sensitive outputs** — use carefully
3. **`-raw` removes quotes** — essential for shell script usage
4. **Computed outputs are powerful** — build URLs, commands, connection strings
5. **Object outputs group related values** — cleaner than multiple separate outputs
6. **SSM SecureString auto-encrypts with KMS** — no extra configuration needed
7. **Outputs are shown after every apply** — no need to run `terraform output` separately

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| S3 bucket (empty) | ~5 seconds | $0.00 |
| SSM Parameter (SecureString) | ~5 seconds | $0.00 |
| **Total** | | **$0.00** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `01_terraform_init.png` | "Terraform has been successfully initialized!" | ⬜ |
| 2 | `02_terraform_plan.png` | 4 outputs including `db_password = (sensitive value)` | ⬜ |
| 3 | `03_terraform_apply.png` | All 4 outputs, `db_password = <sensitive>` | ⬜ |
| 4 | `04_s3_bucket_in_console.png` | S3 bucket page via console URL | ⬜ |
| 5 | `05_ssm_parameter_in_console.png` | SSM Parameter Store showing SecureString | ⬜ |
| 6 | `06_terraform_output.png` | All 4 outputs, sensitive still hidden | ⬜ |
| 7 | `07_terraform_output_raw.png` | Both `-raw` commands with clean outputs | ⬜ |
| 8 | `08_terraform_output_json_sensitive.png` | `-json` revealing sensitive value | ⬜ |
| 9 | `09_terraform_destroy.png` | "Destroy complete! Resources: 3 destroyed" | ⬜ |

> **Save all screenshots to:**
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\03_outputs\`

---

*Author: Viswanath TGR | LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
