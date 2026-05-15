# Hands-on Log — Project 3.1 Phase 2: Terraform Variables

**Date:** 2026-05-12
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\02_variables\`

---

## Phase Description

Phase 1 hardcoded all values directly in `main.tf`. That works for one environment but breaks when you need dev, qa, and prod. This phase solves that with **Terraform variables**.

**Why this phase matters:**
In real companies, the same infrastructure runs in multiple environments. Without variables, you'd need separate `.tf` files for each environment — error-prone and hard to maintain. With variables, one `main.tf` + different `.tfvars` files = all environments covered.

**What you will learn:**
- 5 variable types: string, bool, map, validation, no-default
- 3 ways to pass variable values: `.tfvars` file, `-var` flag, interactive prompt
- How `validation` blocks reject invalid values before touching AWS
- Why `.tfvars` files are the industry standard approach

**Resources created in this phase:**
| Resource | Name | Cost |
|----------|------|------|
| `aws_s3_bucket.main` | `dev-my-app-data-495331821583` | $0 |
| `aws_s3_bucket_versioning.main` | Enabled (from bool variable) | $0 |

**Total cost: $0.00**

---

## Files Used

### main.tf

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
  # No default — will prompt at runtime
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

output "bucket_name"   { value = aws_s3_bucket.main.bucket }
output "bucket_arn"    { value = aws_s3_bucket.main.arn }
output "environment"   { value = var.environment }
```

### dev.tfvars

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

## Bug Fixed Before Starting

**Error encountered:**
```
Error: Missing attribute separator
  on main.tf line 6:
     aws = { source = "hashicorp/aws" version = "~> 5.0" }
Expected a newline or comma to mark the beginning of the next attribute.
```

**Root cause:** Missing comma between `source` and `version` on the same line.

**Fix applied:**
```hcl
# Before (broken)
aws = { source = "hashicorp/aws" version = "~> 5.0" }

# After (fixed)
aws = { source = "hashicorp/aws", version = "~> 5.0" }
```

**My observation:** HCL (HashiCorp Configuration Language) requires a comma or newline between attributes on the same line. This is a common beginner mistake. The error message is clear — always read it carefully.

**Verification:** ✅ Fixed — `terraform init` succeeded after this change

---

## Hands-on Steps

### Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**My observation:**
- Only the AWS provider is needed here (no `random` provider — bucket name comes from variables, not random)
- Same provider version (v5.100.0) as Phase 1 — the lock file ensures consistency

**Verification:** ✅ Initialized successfully

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of terminal showing "Terraform has been successfully initialized!"

---

### Step 2 — Way 1: terraform plan with .tfvars file

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
- Compare to Phase 1: `hello-terraform-9273bec5` (random, meaningless) vs `dev-my-app-data-495331821583` (tells you: environment + purpose + account)
- 5 tags applied including `Owner = vswnth1` — came from `dev.tfvars`
- Nothing created in AWS yet — this is still just a preview

**Verification:** ✅ Plan shows 2 resources, bucket name correctly built from variables

📸 **Screenshot:** `02_plan_with_tfvars.png`
> Take screenshot showing `bucket = "dev-my-app-data-495331821583"` in plan output

---

### Step 3 — Way 2: Override one variable at runtime

**Command run:**
```bash
terraform plan -var-file="dev.tfvars" -var="environment=qa"
```

**Key output:**
```
+ bucket = "qa-my-app-data-495331821583"
+ tags = {
    "Environment" = "qa"
    ...
  }

Changes to Outputs:
+ bucket_name = "qa-my-app-data-495331821583"
+ environment = "qa"
```

**My observation:**
- With ONE flag (`-var="environment=qa"`), the bucket name changed from `dev-...` to `qa-...`
- The `Environment` tag also changed automatically
- **Zero code changes** — same `main.tf`, same `dev.tfvars`, just one override flag
- This is exactly how real companies deploy to multiple environments in CI/CD pipelines
- The `-var` flag always overrides `.tfvars` values — it has higher precedence

**Verification:** ✅ Bucket name correctly changed to qa prefix with one flag

📸 **Screenshot:** `03_plan_qa_override.png`
> Take screenshot showing `bucket = "qa-my-app-data-495331821583"` and `environment = "qa"`

---

### Step 4 — Way 3: No tfvars — interactive prompt

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

**Key output:**
```
+ bucket = "dev-test-bucket"
+ tags = {
    "Environment" = "dev"
    "ManagedBy"   = "terraform"
    "Project"     = "handson"
    "Stage"       = "stage-03"
  }
```

**My observation:**
- Terraform stopped and asked for `bucket_name` because it has no default value
- Typed `test-bucket` → bucket became `dev-test-bucket`
- **Critical gap:** No `Owner` tag — because `dev.tfvars` was not loaded, the `tags` variable used its default (which doesn't include `Owner`)
- This demonstrates why `.tfvars` files are essential — without them, tags are incomplete
- **Never use interactive prompts in CI/CD** — they block automation

**Verification:** ✅ Demonstrated interactive prompt behavior and missing tag issue

📸 **Screenshot:** `04_plan_interactive_prompt.png`
> Take screenshot showing `var.bucket_name` prompt and `Enter a value:` line

---

### Step 5 — terraform apply (create dev bucket)

**Command run:**
```bash
terraform apply -var-file="dev.tfvars"
# typed: yes
```

**Output received:**
```
aws_s3_bucket.main: Creating...
aws_s3_bucket.main: Creation complete after 3s [id=dev-my-app-data-495331821583]
aws_s3_bucket_versioning.main: Creating...
aws_s3_bucket_versioning.main: Creation complete after 2s [id=dev-my-app-data-495331821583]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
bucket_arn  = "arn:aws:s3:::dev-my-app-data-495331821583"
bucket_name = "dev-my-app-data-495331821583"
environment = "dev"
```

**My observation:**
- Only 2 resources created (vs 3 in Phase 1) — no `random_id` needed because bucket name comes from variables
- Bucket name is meaningful: `dev-my-app-data-495331821583` tells you environment, purpose, and account
- All 3 outputs shown: `bucket_arn`, `bucket_name`, `environment` — the `environment` output is new and useful for scripts

**Verification in AWS Console:**
- Go to: https://s3.console.aws.amazon.com/s3/buckets?region=ap-south-1
- Confirmed: `dev-my-app-data-495331821583` bucket visible
- Click bucket → Properties → Tags → confirmed all 5 tags including `Owner = vswnth1`

📸 **Screenshot:** `05_terraform_apply.png`
> Take screenshot of terminal showing "Apply complete! Resources: 2 added"

📸 **Screenshot:** `06_s3_bucket_in_console.png`
> AWS Console → S3 → screenshot showing `dev-my-app-data-495331821583` in the list

📸 **Screenshot:** `07_s3_tags_in_console.png`
> Click bucket → Properties → Tags → screenshot showing all 5 tags including `Owner = vswnth1`

---

### Step 6 — Validation test (invalid environment)

**Command run:**
```bash
terraform plan -var-file="dev.tfvars" -var="environment=staging"
```

**Output received:**
```
│ Error: Invalid value for variable
│
│   on main.tf line 28, in variable "environment":
│   28:   validation {
│
│ Environment must be dev, qa, or prod.
```

**My observation:**
- `staging` is not in the allowed list `["dev", "qa", "prod"]`
- Terraform rejected it **immediately** — before connecting to AWS, before creating anything
- The error message is exactly what we wrote in `error_message` — clear and actionable
- This is the `validation` block working as designed — it's a guardrail that prevents mistakes
- **Industry value:** In a team, this prevents someone from accidentally deploying to a wrong environment name

**Verification:** ✅ Validation correctly rejected invalid value before any AWS interaction

📸 **Screenshot:** `08_validation_error.png`
> Take screenshot of terminal showing the validation error for "staging"

---

### Step 7 — terraform destroy

**Command run:**
```bash
terraform destroy -var-file="dev.tfvars"
# typed: yes
```

**Output received:**
```
aws_s3_bucket_versioning.main: Destroying... [id=dev-my-app-data-495331821583]
aws_s3_bucket_versioning.main: Destruction complete after 0s
aws_s3_bucket.main: Destroying... [id=dev-my-app-data-495331821583]
aws_s3_bucket.main: Destruction complete after 1s

Destroy complete! Resources: 2 destroyed.
```

**My observation:**
- Must pass `-var-file="dev.tfvars"` with destroy too — Terraform needs variable values to identify what to destroy
- Without `-var-file`, it would prompt interactively for `bucket_name`
- Versioning removed first (dependency order), then bucket — same automatic ordering as Phase 1

**Verification:** ✅ All resources deleted, AWS account clean

📸 **Screenshot:** `09_terraform_destroy.png`
> Take screenshot of terminal showing "Destroy complete! Resources: 2 destroyed"

---

## Summary

### 3 Ways to Pass Variables — Comparison

| Way | Command | Owner tag? | When to use |
|-----|---------|-----------|-------------|
| `.tfvars` file | `-var-file="dev.tfvars"` | ✅ Yes | Standard — all real projects |
| Runtime override | `-var="environment=qa"` | ✅ Yes (from tfvars) | Quick one-off change |
| Interactive prompt | no flags | ❌ Missing | Testing only — never CI/CD |

### Variable Types Demonstrated

| Type | Example | Key learning |
|------|---------|-------------|
| `string` | `region = "ap-south-1"` | Basic text value |
| `bool` | `enable_versioning = true` | Controls behavior on/off |
| `map(string)` | `tags = { Owner = "vswnth1" }` | Key-value pairs |
| Validation | `contains(["dev","qa","prod"])` | Rejects invalid values before AWS |
| No default | `bucket_name` | Forces caller to provide value |

### Key Observations from This Phase

1. **Variables make configs reusable** — same `main.tf` works for dev, qa, prod
2. **`.tfvars` files are the industry standard** — one file per environment
3. **`-var` flag overrides `.tfvars`** — useful for quick one-off changes
4. **Missing `.tfvars` = missing tags** — always use `-var-file` in real projects
5. **Validation blocks catch errors before AWS** — saves time and prevents mistakes
6. **Bucket name is now meaningful** — `dev-my-app-data-495331821583` vs `hello-terraform-9273bec5`
7. **Always pass `-var-file` with destroy too** — not just apply

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| S3 bucket (empty) | ~5 seconds | $0.00 |
| **Total** | | **$0.00** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `01_terraform_init.png` | "Terraform has been successfully initialized!" | ⬜ |
| 2 | `02_plan_with_tfvars.png` | Plan showing `dev-my-app-data-495331821583` | ⬜ |
| 3 | `03_plan_qa_override.png` | Plan showing `qa-my-app-data-495331821583` | ⬜ |
| 4 | `04_plan_interactive_prompt.png` | `var.bucket_name` prompt | ⬜ |
| 5 | `05_terraform_apply.png` | "Apply complete! Resources: 2 added" | ⬜ |
| 6 | `06_s3_bucket_in_console.png` | S3 Console showing bucket | ⬜ |
| 7 | `07_s3_tags_in_console.png` | Tags showing all 5 including Owner=vswnth1 | ⬜ |
| 8 | `08_validation_error.png` | Validation error for "staging" | ⬜ |
| 9 | `09_terraform_destroy.png` | "Destroy complete! Resources: 2 destroyed" | ⬜ |

> **Save all screenshots to:**
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\02_variables\`

---

*Author: Viswanath TGR | LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
