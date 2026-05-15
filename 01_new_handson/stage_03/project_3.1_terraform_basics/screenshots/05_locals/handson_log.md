# Hands-on Log — Project 3.1 Phase 5: Terraform Locals

**Date:** 2026-05-13
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\05_locals\`

---

## Phase Description

This is the final phase of Project 3.1 and the most important for writing clean, maintainable Terraform. **Locals** are computed values derived from other values — they implement the DRY (Don't Repeat Yourself) principle.

**Why this phase matters:**
In real projects with 50+ resources, you'd repeat the same tags, name prefixes, and computed values everywhere. If you need to change the project name, you'd update 50 places. With locals, you update one place and everything updates automatically.

**What you will learn:**
- How locals compute values from variables, data sources, and other locals
- DRY principle — define `common_tags` once, use in every resource
- Boolean locals for environment-based conditions (`is_production`)
- `timestamp()` function for auto-tagging creation time
- `merge()` function for combining tag maps

**Resources created in this phase:**
| Resource | Name | Cost |
|----------|------|------|
| `aws_s3_bucket.data` | `handson-dev-data-495331821583` | $0 |
| `aws_s3_bucket_versioning.data` | Suspended (dev) | $0 |

**Total cost: $0.00**

---

## The main.tf File

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
  # Local 1: Consistent name prefix — used in every resource name
  name_prefix = "${var.project}-${var.environment}"

  # Local 2: Common tags — defined once, applied to every resource
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    CreatedAt   = timestamp()
  }

  # Local 3: Boolean condition — controls behavior based on environment
  is_production = var.environment == "prod"

  # Local 4: Complex name using data source — globally unique
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

## Hands-on Steps

### Step 1 — terraform init

**Command run:**
```bash
terraform init
```

**Output received:**
```
Initializing provider plugins...
- Installing hashicorp/aws v5.100.0...
Terraform has been successfully initialized!
```

**My observation:**
- Only AWS provider needed — locals are computed internally, no extra providers required
- Same provider version as all previous phases

**Verification:** ✅ Initialized successfully

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of terminal showing "Terraform has been successfully initialized!"

---

### Step 2 — terraform plan (dev environment — default)

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
- `is_production = false` because `environment = "dev"` ≠ `"prod"`
- Versioning is `Suspended` — saves cost in dev (no version history needed)
- Bucket name built from 3 sources: variable + variable + data source — all computed automatically
- `tags = (known after apply)` because `timestamp()` is computed at apply time, not plan time

**Verification:** ✅ All locals computed correctly for dev environment

📸 **Screenshot:** `02_terraform_plan_dev.png`
> Take screenshot showing `bucket = "handson-dev-data-495331821583"` and `is_production = false`

---

### Step 3 — terraform plan -var="environment=prod" (prod scenario)

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

**Dev vs Prod — what changed with ONE flag:**

| Local | Dev (default) | Prod (`-var="environment=prod"`) |
|-------|--------------|----------------------------------|
| `name_prefix` | `handson-dev` | `handson-prod` |
| `bucket_name` | `handson-dev-data-495331821583` | `handson-prod-data-495331821583` |
| `is_production` | `false` | `true` |
| Versioning | `Suspended` | **`Enabled`** |
| Code changed? | ❌ No | ❌ No |

**My observation:**
- One variable change → all 4 locals recomputed → everything updated automatically
- Versioning switched from `Suspended` to `Enabled` — prod needs version history for compliance
- This is the power of locals: the logic is defined once, the behavior adapts to the environment
- In a real CI/CD pipeline, you'd pass `-var="environment=prod"` for production deployments

**Verification:** ✅ All locals correctly recomputed for prod environment

📸 **Screenshot:** `03_terraform_plan_prod.png`
> Take screenshot showing `bucket = "handson-prod-data-495331821583"`, `is_production = true`, and `status = "Enabled"`

---

### Step 4 — terraform apply (create dev bucket)

**Command run:**
```bash
terraform apply
# typed: yes (uses default dev environment)
```

**Output received:**
```
aws_s3_bucket.data: Creating...
aws_s3_bucket.data: Creation complete after 4s [id=handson-dev-data-495331821583]
aws_s3_bucket_versioning.data: Creating...
aws_s3_bucket_versioning.data: Creation complete after 1s [id=handson-dev-data-495331821583]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
bucket_name   = "handson-dev-data-495331821583"
is_production = false
name_prefix   = "handson-dev"
```

**My observation:**
- Bucket created with the name computed by `local.bucket_name`
- `is_production = false` confirmed in outputs — useful for CI/CD to verify environment
- `name_prefix = "handson-dev"` — this prefix will be used for ALL resources in a real project

**Verification in AWS Console:**
- Go to: https://s3.console.aws.amazon.com/s3/buckets?region=ap-south-1
- Confirmed: `handson-dev-data-495331821583` bucket visible

📸 **Screenshot:** `04_terraform_apply.png`
> Take screenshot of terminal showing "Apply complete! Resources: 2 added"

📸 **Screenshot:** `05_s3_bucket_in_console.png`
> AWS Console → S3 → screenshot showing `handson-dev-data-495331821583` in the list

---

### Step 5 — terraform show (verify tags with timestamp)

**Command run:**
```bash
terraform show
```

**Key output:**
```
aws_s3_bucket.data:
  bucket = "handson-dev-data-495331821583"
  region = "ap-south-1"
  tags = {
    "CreatedAt"   = "2026-05-13T06:31:55Z"   ← timestamp() worked!
    "Environment" = "dev"
    "ManagedBy"   = "terraform"
    "Name"        = "handson-dev-data"        ← from local.name_prefix
    "Owner"       = "vswnth1"
    "Project"     = "handson"
  }

aws_s3_bucket_versioning.data:
  versioning_configuration {
    status = "Suspended"   ← is_production = false
  }
```

**My observation:**
- **6 tags applied** — `common_tags` (5 tags) + `Name` (1 extra via `merge()`)
- `CreatedAt = "2026-05-13T06:31:55Z"` — `timestamp()` function captured the exact apply time
- `Name = "handson-dev-data"` — built from `local.name_prefix` + `-data`
- `Versioning = Suspended` — confirmed `is_production = false` logic worked
- `merge()` combined `common_tags` with the resource-specific `Name` tag cleanly

**Verification in AWS Console:**
- Click bucket → Properties tab → Tags section
- Confirmed: all 6 tags visible including `CreatedAt = 2026-05-13T06:31:55Z`
- Confirmed: Versioning shows `Suspended`

📸 **Screenshot:** `06_terraform_show.png`
> Take screenshot of `terraform show` output showing tags with `CreatedAt` timestamp

📸 **Screenshot:** `07_s3_versioning_suspended.png`
> S3 bucket → Properties → Versioning section → screenshot showing "Suspended"

📸 **Screenshot:** `08_s3_tags_with_timestamp.png`
> S3 bucket → Properties → Tags → screenshot showing all 6 tags including `CreatedAt`

---

### Step 6 — terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes
```

**Output received:**
```
aws_s3_bucket_versioning.data: Destroying... [id=handson-dev-data-495331821583]
aws_s3_bucket_versioning.data: Destruction complete after 0s
aws_s3_bucket.data: Destroying... [id=handson-dev-data-495331821583]
aws_s3_bucket.data: Destruction complete after 1s

Destroy complete! Resources: 2 destroyed.
```

**My observation:**
- Versioning removed first (dependency order), then bucket — same automatic ordering as all previous phases
- No `-var-file` needed for destroy here because all variables have defaults
- AWS account is clean — cost = $0

**Verification:** ✅ All resources deleted

📸 **Screenshot:** `09_terraform_destroy.png`
> Take screenshot of terminal showing "Destroy complete! Resources: 2 destroyed"

---

## Summary

### Locals Computed in This Phase

| Local | Expression | Dev Result | Prod Result |
|-------|-----------|-----------|------------|
| `name_prefix` | `var.project + "-" + var.environment` | `handson-dev` | `handson-prod` |
| `bucket_name` | `name_prefix + "-data-" + account_id` | `handson-dev-data-495331821583` | `handson-prod-data-495331821583` |
| `is_production` | `var.environment == "prod"` | `false` | `true` |
| Versioning | `is_production ? "Enabled" : "Suspended"` | `Suspended` | `Enabled` |

### Command Summary

| Command | Touched AWS? | Result |
|---------|-------------|--------|
| `terraform init` | ❌ No | Downloaded AWS provider |
| `terraform plan` | ❌ No | Showed dev locals computed |
| `terraform plan -var="environment=prod"` | ❌ No | Showed prod locals — versioning Enabled |
| `terraform apply` | ✅ Yes | Created dev bucket with 6 tags |
| `terraform show` | ❌ No | Showed `CreatedAt` timestamp in tags |
| `terraform destroy` | ✅ Yes | Deleted dev bucket |

### Key Observations from This Phase

1. **Locals compute FROM other values** — not passed in from outside
2. **DRY principle** — `common_tags` defined once, used in every resource via `merge()`
3. **Boolean locals control behavior** — `is_production` switches versioning on/off
4. **`timestamp()` auto-tags creation time** — useful for auditing when resources were created
5. **`merge()` combines tag maps** — `common_tags` + resource-specific `Name` tag
6. **One variable change → all locals recompute** — everything updates automatically
7. **Locals can reference each other** — `bucket_name` uses `local.name_prefix`

### Project 3.1 — All 5 Phases Complete

| Phase | Topic | Key Concept |
|-------|-------|-------------|
| Phase 1 | Hello Terraform | Full lifecycle: init → plan → apply → destroy |
| Phase 2 | Variables | Reusable configs with .tfvars files |
| Phase 3 | Outputs | Export values: string, sensitive, object, URL |
| Phase 4 | Data Sources | Read AWS without creating anything |
| Phase 5 | Locals | DRY principle, computed values, conditions |

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
| 2 | `02_terraform_plan_dev.png` | `bucket = "handson-dev-data-495331821583"`, `is_production = false` | ⬜ |
| 3 | `03_terraform_plan_prod.png` | `bucket = "handson-prod-data-495331821583"`, `is_production = true`, `Enabled` | ⬜ |
| 4 | `04_terraform_apply.png` | "Apply complete! Resources: 2 added" | ⬜ |
| 5 | `05_s3_bucket_in_console.png` | S3 Console showing `handson-dev-data-495331821583` | ⬜ |
| 6 | `06_terraform_show.png` | Full state with `CreatedAt = "2026-05-13T06:31:55Z"` | ⬜ |
| 7 | `07_s3_versioning_suspended.png` | S3 Properties → Versioning: Suspended | ⬜ |
| 8 | `08_s3_tags_with_timestamp.png` | S3 Properties → Tags showing all 6 tags | ⬜ |
| 9 | `09_terraform_destroy.png` | "Destroy complete! Resources: 2 destroyed" | ⬜ |

> **Save all screenshots to:**
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\05_locals\`

---

*Author: Viswanath TGR | LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
