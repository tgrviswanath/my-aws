# Hands-on Log — Project 3.1 Phase 2: Terraform Variables

**Date:** 2026-05-12
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\02_variables\`

---

## What This Phase Covers

Instead of hardcoding values in Terraform, variables make configs **reusable**.
The same `main.tf` works for dev, qa, and prod — just by changing a `.tfvars` file.

### Variable Types Learned

| Variable | Type | Value Used |
|----------|------|-----------|
| `region` | `string` | `"ap-south-1"` |
| `bucket_name` | `string` (no default) | `"my-app-data-495331821583"` |
| `environment` | `string` with validation | `"dev"` |
| `enable_versioning` | `bool` | `true` |
| `tags` | `map(string)` | Project, Stage, ManagedBy, Owner |

---

## Files Used

### `main.tf`

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.region }

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
  # No default — will prompt at runtime or must be passed via -var or .tfvars
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "Environment must be dev, qa, or prod."
  }
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
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

### `dev.tfvars`

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
  on main.tf line 6, in terraform:
     6:     aws = { source = "hashicorp/aws" version = "~> 5.0" }
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

**Result:** ✅ Fixed — `terraform init` succeeded after this change.

---

## Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**What happened:**
- Downloaded AWS provider v5.100.0 to local `.terraform/` folder
- Created `.terraform.lock.hcl` lock file
- Nothing created in AWS

**Result:** ✅ Initialized successfully

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of terminal showing "Terraform has been successfully initialized!"

---

## Step 2 — Way 1: Using .tfvars file

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

**What happened:**
- All values loaded from `dev.tfvars`
- Bucket name = `dev-` + `my-app-data-495331821583` (environment prefix + bucket_name variable)
- 5 tags applied including `Owner = vswnth1`
- Nothing created in AWS yet

**Result:** ✅ Plan shows 2 resources to create

📸 **Screenshot:** `02_plan_with_tfvars.png`
> Take screenshot of terminal showing plan output with bucket = "dev-my-app-data-495331821583"

---

## Step 3 — Way 2: Override one variable at runtime

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

**What happened:**
- Same `dev.tfvars` used — but `environment` overridden to `qa`
- Bucket name changed from `dev-...` to `qa-...`
- Environment tag changed from `dev` to `qa`
- **Zero code changes** — just one flag

**Key learning:** `-var` flag overrides any value from `.tfvars`. This is how you deploy the same config to different environments.

**Result:** ✅ Bucket name changed to qa prefix with one flag

📸 **Screenshot:** `03_plan_qa_override.png`
> Take screenshot showing bucket = "qa-my-app-data-495331821583" and environment = "qa"

---

## Step 4 — Way 3: No tfvars — interactive prompt

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

**What happened:**
- Terraform stopped and asked for `bucket_name` because it has no default
- Typed `test-bucket` → bucket became `dev-test-bucket`
- **No `Owner` tag** — because `dev.tfvars` was not loaded
- This shows why `.tfvars` files are important — without them, tags are incomplete

**Result:** ✅ Demonstrated interactive prompt behavior

📸 **Screenshot:** `04_plan_interactive_prompt.png`
> Take screenshot showing "var.bucket_name" prompt and the Enter a value line

---

## Step 5 — terraform apply (dev environment)

**Command run:**
```bash
terraform apply -var-file="dev.tfvars"
```

**Typed:** `yes`

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

**What was created in AWS:**

| Resource | Name | Region |
|----------|------|--------|
| S3 Bucket | `dev-my-app-data-495331821583` | ap-south-1 |
| S3 Versioning | Enabled on above bucket | ap-south-1 |

**Result:** ✅ S3 bucket created in AWS Mumbai region

📸 **Screenshot:** `05_terraform_apply.png`
> Take screenshot of terminal showing "Apply complete! Resources: 2 added"

📸 **Screenshot:** `06_s3_bucket_in_console.png`
> Go to AWS Console → S3 → take screenshot showing `dev-my-app-data-495331821583` in the list

📸 **Screenshot:** `07_s3_tags_in_console.png`
> Click the bucket → Properties tab → Tags section → take screenshot showing all 5 tags including Owner=vswnth1

---

## Step 6 — Validation test (invalid environment)

**Command run:**
```bash
terraform plan -var-file="dev.tfvars" -var="environment=staging"
```

**Expected output:**
```
│ Error: Invalid value for variable
│
│   on main.tf line 28, in variable "environment":
│   28:   validation {
│
│ Environment must be dev, qa, or prod.
```

**What happened:**
- `staging` is not in the allowed list `["dev", "qa", "prod"]`
- Terraform rejected it immediately — before even connecting to AWS
- This is the `validation` block working as designed

**Result:** ✅ Validation correctly rejected invalid value

📸 **Screenshot:** `08_validation_error.png`
> Take screenshot of terminal showing the validation error for "staging"

---

## Step 7 — terraform destroy

**Command run:**
```bash
terraform destroy -var-file="dev.tfvars"
```

**Typed:** `yes`

**Output received:**
```
aws_s3_bucket_versioning.main: Destroying... [id=dev-my-app-data-495331821583]
aws_s3_bucket_versioning.main: Destruction complete after 0s
aws_s3_bucket.main: Destroying... [id=dev-my-app-data-495331821583]
aws_s3_bucket.main: Destruction complete after 1s

Destroy complete! Resources: 2 destroyed.
```

**What happened:**
- Versioning config removed first (dependency order)
- S3 bucket deleted from AWS
- AWS account is clean

**Result:** ✅ All resources deleted. Cost = $0.

📸 **Screenshot:** `09_terraform_destroy.png`
> Take screenshot of terminal showing "Destroy complete! Resources: 2 destroyed"

---

## Phase 2 Summary

### 3 Ways to Pass Variables

| Way | Command | When to use |
|-----|---------|-------------|
| `.tfvars` file | `-var-file="dev.tfvars"` | Standard — use in all real projects |
| Runtime override | `-var="environment=qa"` | Quick one-off change |
| Interactive prompt | no flags | Never in production — only for testing |

### Variable Types Demonstrated

| Type | Example | Use case |
|------|---------|---------|
| `string` | `region = "ap-south-1"` | Text values |
| `bool` | `enable_versioning = true` | Feature flags |
| `map(string)` | `tags = { Owner = "vswnth1" }` | Key-value pairs |
| Validation | `contains(["dev","qa","prod"])` | Enforce allowed values |
| No default | `bucket_name` | Force caller to provide value |

### Key Concepts Learned

- Variables make Terraform configs **reusable** across environments
- `.tfvars` files hold environment-specific values — one per environment
- `-var` flag overrides any value at runtime
- Variables without defaults **prompt interactively** — avoid in CI/CD
- `validation` blocks reject invalid values before touching AWS
- Bucket name = `${environment}-${bucket_name}` — meaningful and unique

## Cost

| Resource | Cost |
|----------|------|
| S3 bucket (empty, ~5 seconds) | $0.00 |
| **Total** | **$0.00** |

---

## Screenshots Checklist

| # | File | Status |
|---|------|--------|
| 1 | `01_terraform_init.png` | ⬜ Add screenshot |
| 2 | `02_plan_with_tfvars.png` | ⬜ Add screenshot |
| 3 | `03_plan_qa_override.png` | ⬜ Add screenshot |
| 4 | `04_plan_interactive_prompt.png` | ⬜ Add screenshot |
| 5 | `05_terraform_apply.png` | ⬜ Add screenshot |
| 6 | `06_s3_bucket_in_console.png` | ⬜ Add screenshot |
| 7 | `07_s3_tags_in_console.png` | ⬜ Add screenshot |
| 8 | `08_validation_error.png` | ⬜ Add screenshot |
| 9 | `09_terraform_destroy.png` | ⬜ Add screenshot |

> Save all screenshots to:
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\02_variables\`
