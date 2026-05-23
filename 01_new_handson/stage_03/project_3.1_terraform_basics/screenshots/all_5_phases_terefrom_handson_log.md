# Hands-on Log — Project 3.1: Terraform Basics (All 5 Phases)

**Date:** 2026-05-12 to 2026-05-13
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**AWS CLI Version:** v2.x

---

## Project Description

Project 3.1 covers the **5 foundational Terraform concepts** — each phase builds on the previous one. By the end, you have everything needed to write real, production-grade Terraform code.

**Why this project matters:**
Before this project, infrastructure was created by clicking in the AWS Console — manual, unrepeatable, and untracked. After this project, you create infrastructure with code — automated, repeatable, and version-controlled.

**5 Phases:**
| Phase | Topic | Key Concept | Resources Created |
|-------|-------|-------------|-------------------|
| Phase 1 | Hello Terraform | Full lifecycle: init → plan → apply → destroy | S3 bucket + versioning |
| Phase 2 | Variables | Reusable configs with .tfvars files | S3 bucket + versioning |
| Phase 3 | Outputs | Export values: string, sensitive, object, URL | S3 bucket + SSM parameter |
| Phase 4 | Data Sources | Read AWS without creating anything | ZERO — read-only |
| Phase 5 | Locals | DRY principle, computed values, conditions | S3 bucket + versioning |

**Total cost across all 5 phases: $0.00**

---

## Prerequisites Verified (Once for All Phases)

### Pre-req 1 — AWS CLI Authentication

**Command run:**
```bash
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
- `Account: 495331821583` — AWS account ID used in bucket names throughout the roadmap
- `user/vswnth1` — confirms IAM user, not root account (correct security practice)
- `UserId` starting with `AIDA` confirms this is an IAM user (not a role or root)

**Verification:** OK — AWS CLI configured and authenticated correctly

[Screenshot: 00_aws_cli_auth.png]
> Terminal showing the full aws sts get-caller-identity output

---

### Pre-req 2 — Terraform Installation

**Command run:**
```bash
terraform --version
```

**Output received:**
```
Terraform v1.7.5
on windows_amd64
```

**My observation:**
- v1.7.5 satisfies `required_version = ">= 1.5.0"` in our main.tf
- `windows_amd64` confirms running on Windows 64-bit

**Verification:** OK — Terraform installed and working

[Screenshot: 00_terraform_version.png]
> Terminal showing Terraform v1.7.5 on windows_amd64

---

## File Structure

```
project_3.1_terraform_basics/
├── 01_hello_terraform/
│   └── main.tf          ← S3 bucket + random suffix + versioning
├── 02_variables/
│   ├── main.tf          ← 5 variable types + validation
│   └── dev.tfvars       ← variable values for dev environment
├── 03_outputs/
│   └── main.tf          ← 4 output types + SSM SecureString
├── 04_data_sources/
│   └── main.tf          ← 5 data sources, zero resources created
├── 05_locals/
│   └── main.tf          ← locals, DRY principle, conditions
└── screenshots/
    └── handson_log.md   ← This file
```

---

## ═══════════════════════════════════════════════════════
## PHASE 1 — Hello Terraform
## ═══════════════════════════════════════════════════════

**Working Directory:** `01_hello_terraform\`
**Date:** 2026-05-12

### Phase Description

This is the **complete Terraform lifecycle** — from zero to a live AWS resource and back to zero. Write your first `.tf` file, run all core Terraform commands, and understand exactly what each one does and whether it touches AWS.

**What you will learn:**
- The 4 core Terraform commands: `init`, `plan`, `apply`, `destroy`
- Which commands touch AWS and which are local-only
- What the state file is and why it matters
- How AWS auto-applies security defaults you did not configure

**Resources created:**
| Resource | Name | Cost |
|----------|------|------|
| `random_id.suffix` | generates `9273bec5` | $0 |
| `aws_s3_bucket.hello` | `hello-terraform-9273bec5` | $0 |
| `aws_s3_bucket_versioning.hello` | Enabled | $0 |

---

### The main.tf File

**Bug fixed before running:**
The `random` provider was missing from `required_providers`. Added it to fix `terraform init` failure.

```hcl
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    random = { source = "hashicorp/random" version = "~> 3.0" }  # added
  }
  required_version = ">= 1.5.0"
}

provider "aws" { region = "ap-south-1" }

resource "aws_s3_bucket" "hello" {
  bucket = "hello-terraform-${random_id.suffix.hex}"
  tags = {
    Name      = "hello-terraform"
    Project   = "handson"
    Stage     = "stage-03"
    ManagedBy = "terraform"
  }
}

resource "random_id" "suffix" {
  byte_length = 4   # generates 8-char hex like "9273bec5"
}

resource "aws_s3_bucket_versioning" "hello" {
  bucket = aws_s3_bucket.hello.id
  versioning_configuration { status = "Enabled" }
}

output "bucket_name" { value = aws_s3_bucket.hello.bucket }
output "bucket_arn"  { value = aws_s3_bucket.hello.arn }
```

---

### Hands-on Steps

#### Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Finding hashicorp/random versions matching "~> 3.0"...
- Installing hashicorp/aws v5.100.0...
- Installing hashicorp/random v3.8.1...
Terraform has been successfully initialized!
```

**My observation:**
- `terraform init` is completely safe — it NEVER touches AWS
- Downloads plugins to `.terraform/providers/` folder only
- Lock file `.terraform.lock.hcl` created — locks provider versions for reproducibility
- Run `init` once per directory (or when providers change)

**Verification:** OK — Both providers downloaded, initialization successful

[Screenshot: 01_p1_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

#### Step 2 — terraform plan

**Command run:**
```bash
terraform plan
```

**Output received:**
```
+ aws_s3_bucket.hello            will be created
  + bucket = (known after apply)
+ aws_s3_bucket_versioning.hello will be created
  + status = "Enabled"
+ random_id.suffix               will be created
  + byte_length = 4

Plan: 3 to add, 0 to change, 0 to destroy.

Changes to Outputs:
+ bucket_arn  = (known after apply)
+ bucket_name = (known after apply)
```

**My observation:**
- `terraform plan` is always safe — read-only preview, nothing created
- `+` symbol = will be created, `~` = change, `-` = delete
- `(known after apply)` = AWS generates these values at creation time
- Always run `plan` before `apply` — review what will change before committing

**Verification:** OK — Plan shows exactly 3 resources to create

[Screenshot: 02_p1_terraform_plan.png]
> Terminal showing "Plan: 3 to add, 0 to change, 0 to destroy"

---

#### Step 3 — terraform apply

**Command run:**
```bash
terraform apply
# typed: yes
```

**Output received:**
```
random_id.suffix: Creation complete after 0s [id=knO-xQ]
aws_s3_bucket.hello: Creation complete after 3s [id=hello-terraform-9273bec5]
aws_s3_bucket_versioning.hello: Creation complete after 2s [id=hello-terraform-9273bec5]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

Outputs:
bucket_arn  = "arn:aws:s3:::hello-terraform-9273bec5"
bucket_name = "hello-terraform-9273bec5"
```

**My observation:**
- Terraform created in dependency order: random_id first (needed for bucket name), then bucket, then versioning
- Bucket name `hello-terraform-9273bec5` = prefix + random hex — globally unique
- Total time: ~5 seconds to create real AWS infrastructure from code

**Verification in AWS Console:**
- S3 Console → `hello-terraform-9273bec5` bucket visible in ap-south-1
- Properties → Versioning → Enabled

[Screenshot: 03_p1_terraform_apply.png]
> Terminal showing "Apply complete! Resources: 3 added" with both outputs

[Screenshot: 04_p1_s3_bucket_console.png]
> AWS Console → S3 showing hello-terraform-9273bec5 in bucket list

[Screenshot: 05_p1_s3_versioning_enabled.png]
> S3 bucket → Properties → Versioning: Enabled

---

#### Step 4 — terraform state list

**Command run:**
```bash
terraform state list
```

**Output received:**
```
aws_s3_bucket.hello
aws_s3_bucket_versioning.hello
random_id.suffix
```

**My observation:**
- State file (`terraform.tfstate`) is Terraform's memory — tracks everything it created
- 3 resources listed = exactly what was created in apply
- Never edit `terraform.tfstate` manually — always use Terraform commands
- If you delete the state file, Terraform loses track — it won't know to destroy them

**Verification:** OK — All 3 resources tracked in state

[Screenshot: 06_p1_terraform_state_list.png]
> Terminal showing the 3 resources listed

---

#### Step 5 — terraform show

**Command run:**
```bash
terraform show
```

**Key output:**
```
aws_s3_bucket.hello:
  bucket = "hello-terraform-9273bec5"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"    # AWS auto-added this!
      }
    }
  }

aws_s3_bucket_versioning.hello:
  versioning_configuration { status = "Enabled" }

random_id.suffix:
  hex = "9273bec5"
  dec = "2457059013"
```

**My observation — important discovery:**
- AWS **automatically added AES256 encryption** even though we never configured it
- Default security behavior since January 2023 — all new S3 buckets are encrypted
- `versioning.enabled = false` in the bucket resource is normal — versioning is managed by the separate `aws_s3_bucket_versioning` resource

**Verification:** OK — Full resource details visible, encryption auto-applied by AWS

[Screenshot: 07_p1_terraform_show.png]
> Terminal showing terraform show output including sse_algorithm = "AES256"

---

#### Step 6 — terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes
```

**Output received:**
```
aws_s3_bucket_versioning.hello: Destruction complete after 0s
aws_s3_bucket.hello: Destruction complete after 1s
random_id.suffix: Destruction complete after 0s

Destroy complete! Resources: 3 destroyed.
```

**My observation:**
- Terraform destroyed in reverse dependency order: versioning first, then bucket, then random_id
- Dependency order is automatic — Terraform knows the graph
- `terraform.tfstate` is now empty — Terraform's memory cleared

**Verification:** OK — Bucket no longer in S3 Console

[Screenshot: 08_p1_terraform_destroy.png]
> Terminal showing "Destroy complete! Resources: 3 destroyed"

[Screenshot: 09_p1_s3_bucket_gone.png]
> S3 Console showing bucket no longer exists

---

### Phase 1 Summary

| Command | Touches AWS? | What it does |
|---------|-------------|--------------|
| `terraform init` | No | Downloads provider plugins locally |
| `terraform plan` | No (read-only) | Previews what will change |
| `terraform apply` | Yes | Creates resources in AWS |
| `terraform state list` | No | Lists tracked resources |
| `terraform show` | No | Shows full resource details from state |
| `terraform destroy` | Yes | Deletes all managed resources |

**Key observations:**
1. `terraform init` is local-only — downloads plugins, never touches AWS
2. `terraform plan` is always safe — read-only preview, run before every apply
3. Only `apply` and `destroy` touch AWS — everything else is local
4. AWS auto-adds AES256 encryption to all new S3 buckets (default since 2023)
5. State file = Terraform's memory — never edit it manually
6. Dependency order is automatic — Terraform creates/destroys in correct order

---

## ═══════════════════════════════════════════════════════
## PHASE 2 — Variables
## ═══════════════════════════════════════════════════════

**Working Directory:** `02_variables\`
**Date:** 2026-05-12

### Phase Description

Phase 1 hardcoded all values directly in `main.tf`. That works for one environment but breaks when you need dev, qa, and prod. This phase solves that with **Terraform variables**.

**What you will learn:**
- 5 variable types: string, bool, map, validation, no-default
- 3 ways to pass variable values: `.tfvars` file, `-var` flag, interactive prompt
- How `validation` blocks reject invalid values before touching AWS
- Why `.tfvars` files are the industry standard approach

**Resources created:**
| Resource | Name | Cost |
|----------|------|------|
| `aws_s3_bucket.main` | `dev-my-app-data-495331821583` | $0 |
| `aws_s3_bucket_versioning.main` | Enabled (from bool variable) | $0 |

---

### Files Used

**main.tf:**
```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
  # No default — will prompt at runtime or must be passed via -var or .tfvars
}

variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "Environment must be dev, qa, or prod."
  }
}

variable "enable_versioning" {
  type    = bool
  default = true
}

variable "tags" {
  type = map(string)
  default = {
    Project   = "handson"
    Stage     = "stage-03"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket" "main" {
  bucket = "${var.environment}-${var.bucket_name}"
  tags   = merge(var.tags, { Environment = var.environment })
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

output "bucket_name" { value = aws_s3_bucket.main.bucket }
output "bucket_arn"  { value = aws_s3_bucket.main.arn }
output "environment" { value = var.environment }
```

**dev.tfvars:**
```hcl
region            = "ap-south-1"
bucket_name       = "my-app-data-495331821583"
environment       = "dev"
enable_versioning = true

tags = {
  Project     = "handson"
  Stage       = "stage-03"
  ManagedBy   = "terraform"
  Owner       = "vswnth1"
}
```

---

### Bug Fixed Before Starting

**Error encountered:**
```
Error: Missing attribute separator
  on main.tf line 6:
  aws = { source = "hashicorp/aws" version = "~> 5.0" }
Expected a newline or comma to mark the beginning of the next attribute.
```

**Root cause:** Missing comma between `source` and `version` on the same line.

**Fix:** Changed to `aws = { source = "hashicorp/aws", version = "~> 5.0" }`

**My observation:** HCL requires a comma or newline between attributes on the same line. Always read the error message carefully — it tells you exactly what is wrong.

---

### Hands-on Steps

#### Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
- Installing hashicorp/aws v5.100.0...
Terraform has been successfully initialized!
```

**My observation:**
- Only the AWS provider needed — no `random` provider since bucket name comes from variables
- Same provider version (v5.100.0) as Phase 1 — lock file ensures consistency

[Screenshot: 01_p2_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

#### Step 2 — Way 1: terraform plan with .tfvars file

**Command run:**
```bash
terraform plan -var-file="dev.tfvars"
```

**Key output:**
```
+ bucket = "dev-my-app-data-495331821583"
+ tags = {
    "Environment" = "dev"
    "ManagedBy"   = "terraform"
    "Owner"       = "vswnth1"
    "Project"     = "handson"
    "Stage"       = "stage-03"
  }

Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
+ bucket_name = "dev-my-app-data-495331821583"
+ environment = "dev"
```

**My observation:**
- Bucket name `dev-my-app-data-495331821583` = `${environment}-${bucket_name}` — meaningful and readable
- Compare to Phase 1: `hello-terraform-9273bec5` (random) vs `dev-my-app-data-495331821583` (tells you environment + purpose + account)
- 5 tags applied including `Owner = vswnth1` — came from `dev.tfvars`

[Screenshot: 02_p2_plan_with_tfvars.png]
> Terminal showing bucket = "dev-my-app-data-495331821583" in plan output

---

#### Step 3 — Way 2: Override one variable at runtime

**Command run:**
```bash
terraform plan -var-file="dev.tfvars" -var="environment=qa"
```

**Key output:**
```
+ bucket = "qa-my-app-data-495331821583"

Changes to Outputs:
+ bucket_name = "qa-my-app-data-495331821583"
+ environment = "qa"
```

**My observation:**
- With ONE flag, the bucket name changed from `dev-...` to `qa-...`
- Zero code changes — same `main.tf`, same `dev.tfvars`, just one override flag
- This is exactly how real companies deploy to multiple environments in CI/CD pipelines
- `-var` flag always overrides `.tfvars` values — it has higher precedence

[Screenshot: 03_p2_plan_qa_override.png]
> Terminal showing bucket = "qa-my-app-data-495331821583" and environment = "qa"

---

#### Step 4 — Way 3: No tfvars — interactive prompt

**Command run:**
```bash
terraform plan
```

**Terraform prompted:**
```
var.bucket_name
  S3 bucket name (must be globally unique)

  Enter a value: test-bucket
```

**My observation:**
- Terraform stopped and asked for `bucket_name` because it has no default value
- No `Owner` tag — because `dev.tfvars` was not loaded, `tags` used its default (no Owner)
- Never use interactive prompts in CI/CD — they block automation

[Screenshot: 04_p2_plan_interactive_prompt.png]
> Terminal showing var.bucket_name prompt and Enter a value: line

---

#### Step 5 — terraform apply (create dev bucket)

**Command run:**
```bash
terraform apply -var-file="dev.tfvars"
# typed: yes
```

**Output received:**
```
aws_s3_bucket.main: Creation complete after 3s [id=dev-my-app-data-495331821583]
aws_s3_bucket_versioning.main: Creation complete after 2s [id=dev-my-app-data-495331821583]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
bucket_arn  = "arn:aws:s3:::dev-my-app-data-495331821583"
bucket_name = "dev-my-app-data-495331821583"
environment = "dev"
```

**My observation:**
- Only 2 resources (vs 3 in Phase 1) — no `random_id` needed, bucket name comes from variables
- All 3 outputs shown including `environment` — useful for CI/CD to verify which env was deployed

**Verification in AWS Console:**
- S3 Console → `dev-my-app-data-495331821583` bucket visible
- Properties → Tags → all 5 tags including `Owner = vswnth1`

[Screenshot: 05_p2_terraform_apply.png]
> Terminal showing "Apply complete! Resources: 2 added"

[Screenshot: 06_p2_s3_bucket_console.png]
> S3 Console showing dev-my-app-data-495331821583

[Screenshot: 07_p2_s3_tags_console.png]
> S3 bucket → Properties → Tags showing all 5 tags including Owner=vswnth1

---

#### Step 6 — Validation test (invalid environment)

**Command run:**
```bash
terraform plan -var-file="dev.tfvars" -var="environment=staging"
```

**Output received:**
```
Error: Invalid value for variable
  Environment must be dev, qa, or prod.
```

**My observation:**
- `staging` is not in the allowed list — Terraform rejected it immediately before connecting to AWS
- The error message is exactly what we wrote in `error_message` — clear and actionable
- Validation blocks are guardrails — prevent mistakes before any AWS interaction

[Screenshot: 08_p2_validation_error.png]
> Terminal showing the validation error for "staging"

---

#### Step 7 — terraform destroy

**Command run:**
```bash
terraform destroy -var-file="dev.tfvars"
# typed: yes
```

**Output received:**
```
aws_s3_bucket_versioning.main: Destruction complete after 0s
aws_s3_bucket.main: Destruction complete after 1s

Destroy complete! Resources: 2 destroyed.
```

**My observation:**
- Must pass `-var-file="dev.tfvars"` with destroy too — Terraform needs variable values
- Without `-var-file`, it would prompt interactively for `bucket_name`

[Screenshot: 09_p2_terraform_destroy.png]
> Terminal showing "Destroy complete! Resources: 2 destroyed"

---

### Phase 2 Summary

**3 Ways to Pass Variables:**

| Way | Command | Owner tag? | When to use |
|-----|---------|-----------|-------------|
| `.tfvars` file | `-var-file="dev.tfvars"` | Yes | Standard — all real projects |
| Runtime override | `-var="environment=qa"` | Yes (from tfvars) | Quick one-off change |
| Interactive prompt | no flags | Missing | Testing only — never CI/CD |

**Key observations:**
1. Variables make configs reusable — same `main.tf` works for dev, qa, prod
2. `.tfvars` files are the industry standard — one file per environment
3. `-var` flag overrides `.tfvars` — useful for quick one-off changes
4. Missing `.tfvars` = missing tags — always use `-var-file` in real projects
5. Validation blocks catch errors before AWS — saves time and prevents mistakes
6. Always pass `-var-file` with destroy too — not just apply

---
## 
## PHASE 3  Outputs
## 

**Working Directory:** `03_outputs\`
**Date:** 2026-05-12

### Phase Description

After `terraform apply`, you need to know what was created  the bucket name, ARN, URL, or a password. Terraform **outputs** export these values. This phase demonstrates 4 output types and 3 ways to read them.

**What you will learn:**
- 4 output types: simple string, sensitive, object, computed URL
- 3 ways to read outputs: `terraform output`, `-raw` (for scripts), `-json` (reveals sensitive)
- How `sensitive = true` protects passwords in ALL terminal output
- How SSM SecureString encrypts values with KMS automatically

**Resources created:**
| Resource | Name | Cost |
|----------|------|------|
| `random_id.suffix` | hex = `e63a1b07` | $0 |
| `aws_s3_bucket.app` | `outputs-demo-e63a1b07` | $0 |
| `aws_ssm_parameter.db_password` | `/handson/db/password` (SecureString) | $0 |

---

### The main.tf File

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

# Output 2: Sensitive  hidden in terminal
output "db_password" {
  value     = aws_ssm_parameter.db_password.value
  sensitive = true
}

# Output 3: Object  multiple values grouped
output "bucket_info" {
  value = {
    name   = aws_s3_bucket.app.bucket
    arn    = aws_s3_bucket.app.arn
    region = aws_s3_bucket.app.region
  }
}

# Output 4: Computed URL  built from resource values
output "bucket_console_url" {
  value = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.app.bucket}"
}
```

---

### Hands-on Steps

#### Step 1  terraform init

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

[Screenshot: 01_p3_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

#### Step 2  terraform plan

**Command run:**
```bash
terraform plan
```

**Key output:**
```
# aws_ssm_parameter.db_password will be created
  + value = (sensitive value)    # hidden even at plan stage!

Plan: 3 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + bucket_console_url = (known after apply)
  + bucket_info        = { arn, name, region }
  + bucket_name        = (known after apply)
  + db_password        = (sensitive value)    # hidden in plan too!
```

**My observation:**
- `db_password` shows as `(sensitive value)` even in the plan  before anything is created
- `sensitive = true` working  Terraform never reveals sensitive values in any output
- All 4 outputs visible in the plan  useful for reviewing what will be exported

[Screenshot: 02_p3_terraform_plan.png]
> Terminal showing all 4 outputs, especially db_password = (sensitive value)

---

#### Step 3  terraform apply

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
- `db_password = <sensitive>`  the password is NEVER shown in terminal, even after apply
- `bucket_console_url` is a fully computed URL  copy-paste directly into a browser
- `bucket_info` shows as a grouped object  name, ARN, and region together
- SSM created the parameter as `SecureString`  AWS automatically encrypted it with KMS

**Verification in AWS Console:**
- Opened `bucket_console_url` in browser  S3 bucket page loaded
- Systems Manager  Parameter Store  `/handson/db/password`  SecureString type confirmed

[Screenshot: 03_p3_terraform_apply.png]
> Terminal showing all 4 outputs, especially db_password = <sensitive>

[Screenshot: 04_p3_s3_bucket_console.png]
> S3 bucket page opened via bucket_console_url

[Screenshot: 05_p3_ssm_parameter_console.png]
> Systems Manager  Parameter Store  /handson/db/password showing SecureString type

---

#### Step 4  terraform output (all outputs)

**Command run:**
```bash
terraform output
```

**Output received:**
```
bucket_console_url = "https://s3.console.aws.amazon.com/s3/buckets/outputs-demo-e63a1b07"
bucket_info = { "arn" = "...", "name" = "outputs-demo-e63a1b07", "region" = "ap-south-1" }
bucket_name = "outputs-demo-e63a1b07"
db_password = <sensitive>
```

**My observation:**
- `db_password` is still `<sensitive>`  even with direct `terraform output` command
- `sensitive = true` protects the value in ALL terminal output  plan, apply, and output

[Screenshot: 06_p3_terraform_output.png]
> Terminal showing all 4 outputs, sensitive still hidden

---

#### Step 5  terraform output -raw (for scripts)

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
- `-raw` returns the value with NO quotes  essential for shell scripts
- Regular `terraform output` returns `"outputs-demo-e63a1b07"` (with quotes)
- Real-world use: `BUCKET=$(terraform output -raw bucket_name)` then `aws s3 cp file.txt s3://$BUCKET/`

[Screenshot: 07_p3_terraform_output_raw.png]
> Terminal showing both -raw commands with clean outputs (no quotes)

---

#### Step 6  terraform output -json (reveal sensitive)

**Command run:**
```bash
terraform output -json db_password
```

**Output received:**
```
"super-secret-password-123"
```

**My observation:**
- `-json` is the ONLY way to reveal a sensitive output value
- Regular `terraform output db_password`  `<sensitive>`
- `terraform output -raw db_password`  ERROR (blocked for sensitive values)
- `terraform output -json db_password`  reveals the value
- Production note: Never store real passwords in Terraform code. Use AWS Secrets Manager.

[Screenshot: 08_p3_terraform_output_json.png]
> Terminal showing -json command revealing the sensitive value

---

#### Step 7  terraform destroy

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

[Screenshot: 09_p3_terraform_destroy.png]
> Terminal showing "Destroy complete! Resources: 3 destroyed"

---

### Phase 3 Summary

**Output Commands Comparison:**

| Command | Shows sensitive? | Use case |
|---------|-----------------|---------|
| `terraform output` | No  `<sensitive>` | View all outputs |
| `terraform output -raw <name>` | No  blocked | Shell scripts, CI/CD |
| `terraform output -json <name>` | Yes  revealed | Only way to see sensitive value |

**Key observations:**
1. `sensitive = true` hides value everywhere  plan, apply, output, logs
2. `-json` is the only way to reveal sensitive outputs  use carefully
3. `-raw` removes quotes  essential for shell script usage
4. Computed outputs are powerful  build URLs, commands, connection strings
5. Object outputs group related values  cleaner than multiple separate outputs
6. SSM SecureString auto-encrypts with KMS  no extra configuration needed

---
## 
## PHASE 4  Data Sources
## 

**Working Directory:** `04_data_sources\`
**Date:** 2026-05-13

### Phase Description

Phases 13 created resources. This phase does something different  it **reads** existing AWS resources without creating anything. Data sources solve the problem of hardcoded values that break over time.

**What you will learn:**
- How data sources read AWS without creating anything
- 5 data sources: AMI, account identity, region, VPC, subnets, AZs
- Why `terraform apply` with only data sources creates 0 resources
- Real values discovered from your AWS account (ap-south-1)

**Resources created: ZERO  data sources only read, never create**

---

### The main.tf File

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "ap-south-1" }

# Data Source 1: Latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name"               values = ["al2023-ami-*-x86_64"] }
  filter { name = "virtualization-type" values = ["hvm"] }
}

# Data Source 2: Current AWS Account and Region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Data Source 3: Default VPC
data "aws_vpc" "default" { default = true }

# Data Source 4: Subnets in Default VPC
data "aws_subnets" "default" {
  filter { name = "vpc-id" values = [data.aws_vpc.default.id] }
}

# Data Source 5: Availability Zones
data "aws_availability_zones" "available" { state = "available" }

output "ami_id"             { value = data.aws_ami.amazon_linux.id }
output "ami_name"           { value = data.aws_ami.amazon_linux.name }
output "account_id"         { value = data.aws_caller_identity.current.account_id }
output "current_region"     { value = data.aws_region.current.name }
output "default_vpc_id"     { value = data.aws_vpc.default.id }
output "default_vpc_cidr"   { value = data.aws_vpc.default.cidr_block }
output "default_subnet_ids" { value = data.aws_subnets.default.ids }
output "availability_zones" { value = data.aws_availability_zones.available.names }
output "useful_for_ec2" {
  value = "ami = ${data.aws_ami.amazon_linux.id} | subnet_id = ${data.aws_subnets.default.ids[0]}"
}
```

---

### Hands-on Steps

#### Step 1  terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
- Installing hashicorp/aws v5.100.0...
Terraform has been successfully initialized!
```

**My observation:**
- Only the AWS provider needed  no `random` provider since we are not creating resources
- `terraform init` is still local-only  no AWS interaction yet

[Screenshot: 01_p4_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

#### Step 2  terraform plan

**Command run:**
```bash
terraform plan
```

**Output received:**
```
data.aws_caller_identity.current: Reading...
data.aws_region.current: Reading...
data.aws_ami.amazon_linux: Reading...
data.aws_vpc.default: Reading...
data.aws_availability_zones.available: Reading...
data.aws_region.current: Read complete after 0s [id=ap-south-1]
data.aws_caller_identity.current: Read complete after 0s [id=495331821583]
data.aws_availability_zones.available: Read complete after 0s [id=ap-south-1]
data.aws_vpc.default: Read complete after 1s [id=vpc-037f017eee3062491]
data.aws_subnets.default: Reading...
data.aws_ami.amazon_linux: Read complete after 1s [id=ami-0627662924eb1b8c6]
data.aws_subnets.default: Read complete after 0s [id=ap-south-1]

Changes to Outputs:
+ account_id         = "495331821583"
+ ami_id             = "ami-0627662924eb1b8c6"
+ ami_name           = "al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64"
+ availability_zones = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
+ current_region     = "ap-south-1"
+ default_subnet_ids = ["subnet-0b4de952205c30013", "subnet-0b58ab8f767a2690b", "subnet-0e133633325b2845b"]
+ default_vpc_cidr   = "172.31.0.0/16"
+ default_vpc_id     = "vpc-037f017eee3062491"
+ useful_for_ec2     = "ami = ami-0627662924eb1b8c6 | subnet_id = subnet-0b4de952205c30013"

You can apply this plan to save these new output values to the Terraform state,
without changing any real infrastructure.
```

**My observation:**
- Data sources show `Reading...`  NOT `Creating...`  this is the key visual difference
- No `Plan: X to add` line  zero resources will be created
- All 9 values resolved from your real AWS account in ap-south-1
- AMI name shows exact version  if you had hardcoded an AMI ID from 6 months ago, it might be deprecated
- `useful_for_ec2` output shows exactly what will be used in Project 3.2 for EC2 creation

**Verification:** OK  All 9 values discovered from AWS account, zero resources planned

[Screenshot: 02_p4_terraform_plan.png]
> Terminal showing all 9 outputs and "without changing any real infrastructure"

---

#### Step 3  terraform apply

**Command run:**
```bash
terraform apply
# typed: yes
```

**Output received:**
```
Apply complete! Resources: 0 added, 0 changed, 0 destroyed.

Outputs:
account_id         = "495331821583"
ami_id             = "ami-0627662924eb1b8c6"
ami_name           = "al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64"
availability_zones = tolist(["ap-south-1a", "ap-south-1b", "ap-south-1c"])
current_region     = "ap-south-1"
default_subnet_ids = tolist(["subnet-0b4de952205c30013", "subnet-0b58ab8f767a2690b", "subnet-0e133633325b2845b"])
default_vpc_cidr   = "172.31.0.0/16"
default_vpc_id     = "vpc-037f017eee3062491"
useful_for_ec2     = "ami = ami-0627662924eb1b8c6 | subnet_id = subnet-0b4de952205c30013"
```

**My observation:**
- `Resources: 0 added, 0 changed, 0 destroyed`  the ONLY Terraform apply that creates nothing in AWS
- Outputs saved to `terraform.tfstate`  other configs can read them via `terraform_remote_state`
- `tolist([...])` wrapping is normal  Terraform shows the type explicitly in output

**Verification:** OK  Apply completed with zero AWS resources created

[Screenshot: 03_p4_terraform_apply.png]
> Terminal showing "Apply complete! Resources: 0 added, 0 changed, 0 destroyed" and all 9 outputs

---

#### Step 4  Verify in AWS Console

**Account ID and Region:**
```
AWS Console  Top right corner  Account ID: 495331821583
Region: Asia Pacific (Mumbai) ap-south-1
```

**AMI ID:**
```
EC2  Images  AMIs  Public images  ami-0627662924eb1b8c6
Name: al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64
```

**Default VPC:**
```
VPC  Your VPCs  Default VPC = Yes
VPC ID: vpc-037f017eee3062491
IPv4 CIDR: 172.31.0.0/16
```

**Subnets:**
```
VPC  Subnets  filter by vpc-037f017eee3062491
subnet-0b4de952205c30013  ap-south-1a
subnet-0b58ab8f767a2690b  ap-south-1b
subnet-0e133633325b2845b  ap-south-1c
```

**My observation:**
- Every value returned by data sources matches exactly what is in the AWS Console
- 3 subnets  one per AZ  the data source returned all 3 IDs as a list
- In Project 3.2, `[0]` picks the first subnet for EC2 placement

[Screenshot: 04_p4_aws_console_account.png]
> AWS Console top-right showing account ID 495331821583 and region ap-south-1

[Screenshot: 05_p4_aws_console_ami.png]
> EC2  AMIs showing ami-0627662924eb1b8c6

[Screenshot: 06_p4_aws_console_vpc.png]
> VPC Console showing default VPC vpc-037f017eee3062491 with CIDR 172.31.0.0/16

[Screenshot: 07_p4_aws_console_subnets.png]
> VPC  Subnets showing 3 subnets with AZ assignments

---

#### No destroy needed

**My observation:**
- Data sources created zero resources  there is nothing to destroy
- This is the only phase where you do not need to run destroy
- The state file contains only cached data source values  no real AWS resources

---

### Phase 4 Summary

**What Was Discovered From Your AWS Account:**

| Value | Discovered |
|-------|-----------|
| Account ID | `495331821583` |
| Region | `ap-south-1` |
| Latest AMI ID | `ami-0627662924eb1b8c6` |
| Default VPC ID | `vpc-037f017eee3062491` |
| VPC CIDR | `172.31.0.0/16` |
| Subnet 1 (1a) | `subnet-0b4de952205c30013` |
| Subnet 2 (1b) | `subnet-0b58ab8f767a2690b` |
| Subnet 3 (1c) | `subnet-0e133633325b2845b` |
| AZs | `ap-south-1a/b/c` |

**Key observations:**
1. Data sources show `Reading...`  not `Creating...`  the key visual difference
2. `apply` with only data sources = `Resources: 0 added`  nothing created in AWS
3. AMI IDs are region-specific  always use data source, never hardcode
4. No destroy needed  nothing was created, nothing to clean up
5. `useful_for_ec2` output is ready to use directly in Project 3.2 EC2 resource
6. Data sources reference resources not managed by this config  the default VPC was not created by Terraform

---
## 
## PHASE 5  Locals
## 

**Working Directory:** `05_locals\`
**Date:** 2026-05-13

### Phase Description

This is the final phase of Project 3.1 and the most important for writing clean, maintainable Terraform. **Locals** are computed values derived from other values  they implement the DRY (Don't Repeat Yourself) principle.

**What you will learn:**
- How locals compute values from variables, data sources, and other locals
- DRY principle  define `common_tags` once, use in every resource
- Boolean locals for environment-based conditions (`is_production`)
- `timestamp()` function for auto-tagging creation time
- `merge()` function for combining tag maps

**Resources created:**
| Resource | Name | Cost |
|----------|------|------|
| `aws_s3_bucket.data` | `handson-dev-data-495331821583` | $0 |
| `aws_s3_bucket_versioning.data` | Suspended (dev) | $0 |

---

### The main.tf File

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region"      { default = "ap-south-1" }
variable "project"     { default = "handson" }
variable "environment" { default = "dev" }
variable "owner"       { default = "vswnth1" }

locals {
  # Local 1: Consistent name prefix  used in every resource name
  name_prefix = "${var.project}-${var.environment}"

  # Local 2: Common tags  defined once, applied to every resource
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    CreatedAt   = timestamp()
  }

  # Local 3: Boolean condition  controls behavior based on environment
  is_production = var.environment == "prod"

  # Local 4: Complex name using data source  globally unique
  bucket_name = "${local.name_prefix}-data-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "data" {
  bucket = local.bucket_name
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-data" })
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = local.is_production ? "Enabled" : "Suspended"
  }
}

output "name_prefix"   { value = local.name_prefix }
output "bucket_name"   { value = aws_s3_bucket.data.bucket }
output "is_production" { value = local.is_production }
```

---

### Hands-on Steps

#### Step 1  terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
- Installing hashicorp/aws v5.100.0...
Terraform has been successfully initialized!
```

**My observation:**
- Only AWS provider needed  locals are computed internally, no extra providers required

[Screenshot: 01_p5_terraform_init.png]
> Terminal showing "Terraform has been successfully initialized!"

---

#### Step 2  terraform plan (dev environment  default)

**Command run:**
```bash
terraform plan
```

**Key output:**
```
+ bucket = "handson-dev-data-495331821583"
+ versioning_configuration {
    status = "Suspended"
  }

Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
+ bucket_name   = "handson-dev-data-495331821583"
+ is_production = false
+ name_prefix   = "handson-dev"
```

**How locals were computed:**

| Local | Expression | Result |
|-------|-----------|--------|
| `name_prefix` | `"handson" + "-" + "dev"` | `"handson-dev"` |
| `bucket_name` | `"handson-dev" + "-data-" + "495331821583"` | `"handson-dev-data-495331821583"` |
| `is_production` | `"dev" == "prod"` | `false` |
| Versioning | `false ? "Enabled" : "Suspended"` | `"Suspended"` |

**My observation:**
- `is_production = false` because `environment = "dev"` is not equal to `"prod"`
- Versioning is `Suspended`  saves cost in dev (no version history needed)
- Bucket name built from 3 sources: variable + variable + data source  all computed automatically
- `tags = (known after apply)` because `timestamp()` is computed at apply time, not plan time

[Screenshot: 02_p5_terraform_plan_dev.png]
> Terminal showing bucket = "handson-dev-data-495331821583" and is_production = false

---

#### Step 3  terraform plan -var="environment=prod" (prod scenario)

**Command run:**
```bash
terraform plan -var="environment=prod"
```

**Key output:**
```
+ bucket = "handson-prod-data-495331821583"
+ versioning_configuration {
    status = "Enabled"
  }

Changes to Outputs:
+ bucket_name   = "handson-prod-data-495331821583"
+ is_production = true
+ name_prefix   = "handson-prod"
```

**Dev vs Prod  what changed with ONE flag:**

| Local | Dev (default) | Prod (-var="environment=prod") |
|-------|--------------|-------------------------------|
| `name_prefix` | `handson-dev` | `handson-prod` |
| `bucket_name` | `handson-dev-data-495331821583` | `handson-prod-data-495331821583` |
| `is_production` | `false` | `true` |
| Versioning | `Suspended` | `Enabled` |
| Code changed? | No | No |

**My observation:**
- One variable change  all 4 locals recomputed  everything updated automatically
- Versioning switched from `Suspended` to `Enabled`  prod needs version history for compliance
- This is the power of locals: the logic is defined once, the behavior adapts to the environment

[Screenshot: 03_p5_terraform_plan_prod.png]
> Terminal showing bucket = "handson-prod-data-495331821583", is_production = true, status = "Enabled"

---

#### Step 4  terraform apply (create dev bucket)

**Command run:**
```bash
terraform apply
# typed: yes (uses default dev environment)
```

**Output received:**
```
aws_s3_bucket.data: Creation complete after 4s [id=handson-dev-data-495331821583]
aws_s3_bucket_versioning.data: Creation complete after 1s [id=handson-dev-data-495331821583]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
bucket_name   = "handson-dev-data-495331821583"
is_production = false
name_prefix   = "handson-dev"
```

**My observation:**
- Bucket created with the name computed by `local.bucket_name`
- `is_production = false` confirmed in outputs  useful for CI/CD to verify environment
- `name_prefix = "handson-dev"`  this prefix will be used for ALL resources in a real project

**Verification in AWS Console:**
- S3 Console  `handson-dev-data-495331821583` bucket visible

[Screenshot: 04_p5_terraform_apply.png]
> Terminal showing "Apply complete! Resources: 2 added"

[Screenshot: 05_p5_s3_bucket_console.png]
> S3 Console showing handson-dev-data-495331821583

---

#### Step 5  terraform show (verify tags with timestamp)

**Command run:**
```bash
terraform show
```

**Key output:**
```
aws_s3_bucket.data:
  bucket = "handson-dev-data-495331821583"
  tags = {
    "CreatedAt"   = "2026-05-13T06:31:55Z"   # timestamp() worked!
    "Environment" = "dev"
    "ManagedBy"   = "terraform"
    "Name"        = "handson-dev-data"        # from local.name_prefix
    "Owner"       = "vswnth1"
    "Project"     = "handson"
  }

aws_s3_bucket_versioning.data:
  versioning_configuration {
    status = "Suspended"   # is_production = false
  }
```

**My observation:**
- 6 tags applied  `common_tags` (5 tags) + `Name` (1 extra via `merge()`)
- `CreatedAt = "2026-05-13T06:31:55Z"`  `timestamp()` captured the exact apply time
- `Name = "handson-dev-data"`  built from `local.name_prefix` + `-data`
- `Versioning = Suspended`  confirmed `is_production = false` logic worked
- `merge()` combined `common_tags` with the resource-specific `Name` tag cleanly

**Verification in AWS Console:**
- S3 bucket  Properties  Tags  all 6 tags visible including `CreatedAt`
- Properties  Versioning  Suspended

[Screenshot: 06_p5_terraform_show.png]
> Terminal showing terraform show output with CreatedAt timestamp in tags

[Screenshot: 07_p5_s3_versioning_suspended.png]
> S3 bucket  Properties  Versioning: Suspended

[Screenshot: 08_p5_s3_tags_timestamp.png]
> S3 bucket  Properties  Tags showing all 6 tags including CreatedAt

---

#### Step 6  terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes
```

**Output received:**
```
aws_s3_bucket_versioning.data: Destruction complete after 0s
aws_s3_bucket.data: Destruction complete after 1s

Destroy complete! Resources: 2 destroyed.
```

**My observation:**
- No `-var-file` needed  all variables have defaults
- Versioning removed first (dependency order), then bucket

[Screenshot: 09_p5_terraform_destroy.png]
> Terminal showing "Destroy complete! Resources: 2 destroyed"

---

### Phase 5 Summary

**Locals Computed in This Phase:**

| Local | Expression | Dev Result | Prod Result |
|-------|-----------|-----------|------------|
| `name_prefix` | `var.project + "-" + var.environment` | `handson-dev` | `handson-prod` |
| `bucket_name` | `name_prefix + "-data-" + account_id` | `handson-dev-data-495331821583` | `handson-prod-data-495331821583` |
| `is_production` | `var.environment == "prod"` | `false` | `true` |
| Versioning | `is_production ? "Enabled" : "Suspended"` | `Suspended` | `Enabled` |

**Key observations:**
1. Locals compute FROM other values  not passed in from outside
2. DRY principle  `common_tags` defined once, used in every resource via `merge()`
3. Boolean locals control behavior  `is_production` switches versioning on/off
4. `timestamp()` auto-tags creation time  useful for auditing
5. `merge()` combines tag maps  `common_tags` + resource-specific `Name` tag
6. One variable change  all locals recompute  everything updates automatically
7. Locals can reference each other  `bucket_name` uses `local.name_prefix`

---

## 
## OVERALL PROJECT SUMMARY
## 

### All 5 Phases  What Was Built

| Phase | Resources Created | Key Command | Key Learning |
|-------|------------------|-------------|-------------|
| Phase 1 | S3 bucket + versioning (3 resources) | `terraform show` | AES256 auto-applied by AWS |
| Phase 2 | S3 bucket + versioning (2 resources) | `-var-file="dev.tfvars"` | Validation blocks catch errors before AWS |
| Phase 3 | S3 bucket + SSM parameter (3 resources) | `terraform output -json` | Only `-json` reveals sensitive values |
| Phase 4 | ZERO  read-only | `terraform plan` | Data sources show `Reading...` not `Creating...` |
| Phase 5 | S3 bucket + versioning (2 resources) | `terraform show` | `timestamp()` + `merge()` + `is_production` |

### Command Reference  All Phases

| Command | Touches AWS? | What it does |
|---------|-------------|--------------|
| `terraform init` | No | Downloads provider plugins locally |
| `terraform plan` | No (read-only) | Previews what will change |
| `terraform apply` | Yes | Creates/modifies resources in AWS |
| `terraform apply -var-file="dev.tfvars"` | Yes | Apply with variable file |
| `terraform apply -var="environment=prod"` | Yes | Apply with variable override |
| `terraform state list` | No | Lists tracked resources |
| `terraform show` | No | Shows full resource details from state |
| `terraform output` | No | Shows all output values |
| `terraform output -raw <name>` | No | Output without quotes (for scripts) |
| `terraform output -json <name>` | No | Output as JSON (reveals sensitive) |
| `terraform destroy` | Yes | Deletes all managed resources |

### Key Observations Across All Phases

1. **`terraform init` is always local-only**  downloads plugins, never touches AWS
2. **`terraform plan` is always safe**  read-only preview, run before every apply
3. **Only `apply` and `destroy` touch AWS**  everything else is local
4. **AWS auto-adds AES256 encryption** to all new S3 buckets (default since 2023)
5. **State file = Terraform's memory**  never edit it manually
6. **Variables make configs reusable**  same `main.tf` works for dev, qa, prod
7. **Validation blocks catch errors before AWS**  saves time and prevents mistakes
8. **`sensitive = true` hides value everywhere**  plan, apply, output, logs
9. **Data sources show `Reading...`**  not `Creating...`  zero resources created
10. **Locals implement DRY**  define once, use everywhere, update in one place

### Total Cost

| Phase | Resources | Duration | Cost |
|-------|-----------|----------|------|
| Phase 1 | S3 bucket | ~5 seconds | $0.00 |
| Phase 2 | S3 bucket | ~5 seconds | $0.00 |
| Phase 3 | S3 bucket + SSM | ~5 seconds | $0.00 |
| Phase 4 | ZERO | N/A | $0.00 |
| Phase 5 | S3 bucket | ~5 seconds | $0.00 |
| **Total** | | | **$0.00** |

---

## Screenshots Checklist

| # | File | Phase | Description | Status |
|---|------|-------|-------------|--------|
| 1 | `00_aws_cli_auth.png` | Pre-req | aws sts get-caller-identity output | Add screenshot |
| 2 | `00_terraform_version.png` | Pre-req | terraform --version output | Add screenshot |
| 3 | `01_p1_terraform_init.png` | Phase 1 | "Terraform has been successfully initialized!" | Add screenshot |
| 4 | `02_p1_terraform_plan.png` | Phase 1 | "Plan: 3 to add, 0 to change, 0 to destroy" | Add screenshot |
| 5 | `03_p1_terraform_apply.png` | Phase 1 | "Apply complete! Resources: 3 added" | Add screenshot |
| 6 | `04_p1_s3_bucket_console.png` | Phase 1 | S3 Console showing hello-terraform-9273bec5 | Add screenshot |
| 7 | `05_p1_s3_versioning_enabled.png` | Phase 1 | S3 Properties  Versioning: Enabled | Add screenshot |
| 8 | `06_p1_terraform_state_list.png` | Phase 1 | 3 resources listed | Add screenshot |
| 9 | `07_p1_terraform_show.png` | Phase 1 | Full state including sse_algorithm = "AES256" | Add screenshot |
| 10 | `08_p1_terraform_destroy.png` | Phase 1 | "Destroy complete! Resources: 3 destroyed" | Add screenshot |
| 11 | `09_p1_s3_bucket_gone.png` | Phase 1 | S3 Console  bucket no longer exists | Add screenshot |
| 12 | `01_p2_terraform_init.png` | Phase 2 | "Terraform has been successfully initialized!" | Add screenshot |
| 13 | `02_p2_plan_with_tfvars.png` | Phase 2 | Plan showing dev-my-app-data-495331821583 | Add screenshot |
| 14 | `03_p2_plan_qa_override.png` | Phase 2 | Plan showing qa-my-app-data-495331821583 | Add screenshot |
| 15 | `04_p2_plan_interactive_prompt.png` | Phase 2 | var.bucket_name prompt | Add screenshot |
| 16 | `05_p2_terraform_apply.png` | Phase 2 | "Apply complete! Resources: 2 added" | Add screenshot |
| 17 | `06_p2_s3_bucket_console.png` | Phase 2 | S3 Console showing dev-my-app-data-495331821583 | Add screenshot |
| 18 | `07_p2_s3_tags_console.png` | Phase 2 | Tags showing all 5 including Owner=vswnth1 | Add screenshot |
| 19 | `08_p2_validation_error.png` | Phase 2 | Validation error for "staging" | Add screenshot |
| 20 | `09_p2_terraform_destroy.png` | Phase 2 | "Destroy complete! Resources: 2 destroyed" | Add screenshot |
| 21 | `01_p3_terraform_init.png` | Phase 3 | "Terraform has been successfully initialized!" | Add screenshot |
| 22 | `02_p3_terraform_plan.png` | Phase 3 | 4 outputs including db_password = (sensitive value) | Add screenshot |
| 23 | `03_p3_terraform_apply.png` | Phase 3 | All 4 outputs, db_password = <sensitive> | Add screenshot |
| 24 | `04_p3_s3_bucket_console.png` | Phase 3 | S3 bucket page via console URL | Add screenshot |
| 25 | `05_p3_ssm_parameter_console.png` | Phase 3 | SSM Parameter Store showing SecureString | Add screenshot |
| 26 | `06_p3_terraform_output.png` | Phase 3 | All 4 outputs, sensitive still hidden | Add screenshot |
| 27 | `07_p3_terraform_output_raw.png` | Phase 3 | Both -raw commands with clean outputs | Add screenshot |
| 28 | `08_p3_terraform_output_json.png` | Phase 3 | -json revealing sensitive value | Add screenshot |
| 29 | `09_p3_terraform_destroy.png` | Phase 3 | "Destroy complete! Resources: 3 destroyed" | Add screenshot |
| 30 | `01_p4_terraform_init.png` | Phase 4 | "Terraform has been successfully initialized!" | Add screenshot |
| 31 | `02_p4_terraform_plan.png` | Phase 4 | All 9 outputs + "without changing any real infrastructure" | Add screenshot |
| 32 | `03_p4_terraform_apply.png` | Phase 4 | "Resources: 0 added, 0 changed, 0 destroyed" | Add screenshot |
| 33 | `04_p4_aws_console_account.png` | Phase 4 | Account ID 495331821583 and region ap-south-1 | Add screenshot |
| 34 | `05_p4_aws_console_ami.png` | Phase 4 | EC2  AMIs showing ami-0627662924eb1b8c6 | Add screenshot |
| 35 | `06_p4_aws_console_vpc.png` | Phase 4 | Default VPC vpc-037f017eee3062491 with CIDR | Add screenshot |
| 36 | `07_p4_aws_console_subnets.png` | Phase 4 | 3 subnets with AZ assignments | Add screenshot |
| 37 | `01_p5_terraform_init.png` | Phase 5 | "Terraform has been successfully initialized!" | Add screenshot |
| 38 | `02_p5_terraform_plan_dev.png` | Phase 5 | bucket = "handson-dev-data-495331821583", is_production = false | Add screenshot |
| 39 | `03_p5_terraform_plan_prod.png` | Phase 5 | bucket = "handson-prod-data-495331821583", is_production = true | Add screenshot |
| 40 | `04_p5_terraform_apply.png` | Phase 5 | "Apply complete! Resources: 2 added" | Add screenshot |
| 41 | `05_p5_s3_bucket_console.png` | Phase 5 | S3 Console showing handson-dev-data-495331821583 | Add screenshot |
| 42 | `06_p5_terraform_show.png` | Phase 5 | Full state with CreatedAt timestamp in tags | Add screenshot |
| 43 | `07_p5_s3_versioning_suspended.png` | Phase 5 | S3 Properties  Versioning: Suspended | Add screenshot |
| 44 | `08_p5_s3_tags_timestamp.png` | Phase 5 | S3 Properties  Tags showing all 6 tags | Add screenshot |
| 45 | `09_p5_terraform_destroy.png` | Phase 5 | "Destroy complete! Resources: 2 destroyed" | Add screenshot |

Save all screenshots to:
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\

---

*Author: Viswanath TGR*
*LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on  62 Projects*
