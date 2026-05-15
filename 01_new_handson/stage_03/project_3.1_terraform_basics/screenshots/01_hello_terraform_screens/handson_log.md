# Hands-on Log — Project 3.1 Phase 1: Hello Terraform

**Date:** 2026-05-12
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**AWS CLI Version:** v2.x

---

## Phase Description

This is the **complete Terraform lifecycle** — from zero to a live AWS resource and back to zero.
You write your first `.tf` file, run all core Terraform commands, and understand exactly what each one does and whether it touches AWS.

**Why this phase matters:**
Before this phase, infrastructure was created by clicking in the AWS Console — manual, unrepeatable, and untracked. After this phase, you create infrastructure with code — automated, repeatable, and version-controlled.

**What you will learn:**
- The 4 core Terraform commands: `init`, `plan`, `apply`, `destroy`
- Which commands touch AWS and which are local-only
- What the state file is and why it matters
- How AWS auto-applies security defaults you didn't configure

**Resources created in this phase:**
| Resource | Name | Cost |
|----------|------|------|
| `random_id.suffix` | generates `9273bec5` | $0 |
| `aws_s3_bucket.hello` | `hello-terraform-9273bec5` | $0 |
| `aws_s3_bucket_versioning.hello` | Enabled on above bucket | $0 |

**Total cost: $0.00**

---

## Prerequisites Verified

### Step 1 — AWS CLI Authentication

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
- `Account: 495331821583` — this is our AWS account ID, used in bucket names throughout the roadmap
- `user/vswnth1` — confirms we are using an IAM user, not the root account (correct security practice)
- The `UserId` starting with `AIDA` confirms this is an IAM user (not a role or root)

**Verification:** ✅ AWS CLI configured and authenticated correctly

📸 **Screenshot:** `00_aws_cli_auth.png`
> Take screenshot of terminal showing the full `aws sts get-caller-identity` output

---

### Step 2 — Terraform Installation

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
- v1.7.5 satisfies `required_version = ">= 1.5.0"` in our `main.tf`
- "out of date" warning is harmless — v1.7.5 works perfectly for this roadmap
- `windows_amd64` confirms running on Windows 64-bit

**Verification:** ✅ Terraform installed and working

📸 **Screenshot:** `00_terraform_version.png`
> Take screenshot of terminal showing `Terraform v1.7.5 on windows_amd64`

---

## The main.tf File

**File location:**
```
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\01_hello_terraform\main.tf
```

**Bug fixed before running:**
The `random` provider was missing from `required_providers`. Added it to fix `terraform init` failure.

```hcl
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    random = { source = "hashicorp/random" version = "~> 3.0" }  ← added
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "ap-south-1"   ← Mumbai (your IAM user region)
}

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
  byte_length = 4   ← generates 8-char hex like "9273bec5"
}

resource "aws_s3_bucket_versioning" "hello" {
  bucket = aws_s3_bucket.hello.id
  versioning_configuration { status = "Enabled" }
}

output "bucket_name" { value = aws_s3_bucket.hello.bucket }
output "bucket_arn"  { value = aws_s3_bucket.hello.arn }
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
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Finding hashicorp/random versions matching "~> 3.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)
- Installing hashicorp/random v3.8.1...
- Installed hashicorp/random v3.8.1 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**What happened (local machine only):**
- Downloaded AWS provider plugin (v5.100.0) to `.terraform/providers/` folder
- Downloaded Random provider plugin (v3.8.1) to `.terraform/providers/` folder
- Created `.terraform.lock.hcl` — locks provider versions for reproducibility

**My observation:**
- `terraform init` is completely safe — it NEVER touches AWS
- It only downloads plugins to your local machine
- The lock file ensures everyone on the team uses the same provider version
- You only need to run `init` once per directory (or when providers change)

**Verification:** ✅ Both providers downloaded, initialization successful

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of terminal showing "Terraform has been successfully initialized!"

---

### Step 2 — terraform plan

**Command run:**
```bash
terraform plan
```

**Output received:**
```
+ aws_s3_bucket.hello            will be created
  + bucket = (known after apply)
  + tags   = { "ManagedBy" = "terraform", "Name" = "hello-terraform", ... }

+ aws_s3_bucket_versioning.hello will be created
  + status = "Enabled"

+ random_id.suffix               will be created
  + byte_length = 4

Plan: 3 to add, 0 to change, 0 to destroy.

Changes to Outputs:
+ bucket_arn  = (known after apply)
+ bucket_name = (known after apply)
```

**What happened:**
- Terraform connected to AWS and checked current state (nothing exists yet)
- Showed exactly what WOULD be created — nothing was created
- `(known after apply)` = AWS generates these values at creation time

**My observation:**
- `terraform plan` is always safe — it is a read-only preview
- The `+` symbol means "will be created" — `~` means change, `-` means delete
- `Plan: 3 to add, 0 to change, 0 to destroy` is the most important line — always read it
- Always run `plan` before `apply` — review what will change before committing

**Verification:** ✅ Plan shows exactly 3 resources to create, nothing to change or destroy

📸 **Screenshot:** `02_terraform_plan.png`
> Take screenshot of terminal showing "Plan: 3 to add, 0 to change, 0 to destroy"

---

### Step 3 — terraform apply

**Command run:**
```bash
terraform apply
# typed: yes when prompted
```

**Output received:**
```
random_id.suffix: Creating...
random_id.suffix: Creation complete after 0s [id=knO-xQ]
aws_s3_bucket.hello: Creating...
aws_s3_bucket.hello: Creation complete after 3s [id=hello-terraform-9273bec5]
aws_s3_bucket_versioning.hello: Creating...
aws_s3_bucket_versioning.hello: Creation complete after 2s [id=hello-terraform-9273bec5]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

Outputs:
bucket_arn  = "arn:aws:s3:::hello-terraform-9273bec5"
bucket_name = "hello-terraform-9273bec5"
```

**What was created in AWS:**
| Resource | Name | Time |
|----------|------|------|
| Random ID | hex = `9273bec5` | 0s |
| S3 Bucket | `hello-terraform-9273bec5` | 3s |
| S3 Versioning | Enabled | 2s |

**My observation:**
- Terraform created resources in dependency order: random_id first (needed for bucket name), then bucket, then versioning
- The bucket name `hello-terraform-9273bec5` = prefix + random hex — globally unique
- Outputs are shown immediately after apply — useful for next steps
- Total time: ~5 seconds to create real AWS infrastructure from code

**Verification in AWS Console:**
- Go to: https://s3.console.aws.amazon.com/s3/buckets?region=ap-south-1
- Confirmed: `hello-terraform-9273bec5` bucket visible in ap-south-1
- Confirmed: Properties → Versioning shows "Enabled"

📸 **Screenshot:** `03_terraform_apply.png`
> Take screenshot of terminal showing "Apply complete! Resources: 3 added"

📸 **Screenshot:** `04_s3_bucket_in_console.png`
> AWS Console → S3 → screenshot showing `hello-terraform-9273bec5` in the bucket list

📸 **Screenshot:** `05_s3_versioning_enabled.png`
> Click bucket → Properties tab → Versioning section → screenshot showing "Enabled"

---

### Step 4 — terraform state list

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
- The state file (`terraform.tfstate`) is Terraform's memory — it tracks everything it created
- 3 resources listed = exactly what we created in `apply`
- If you delete the state file, Terraform loses track of these resources — it won't know to destroy them
- Never edit `terraform.tfstate` manually — always use Terraform commands

**Verification:** ✅ All 3 created resources are tracked in state

📸 **Screenshot:** `06_terraform_state_list.png`
> Take screenshot of terminal showing the 3 resources listed

---

### Step 5 — terraform show

**Command run:**
```bash
terraform show
```

**Key output:**
```
aws_s3_bucket.hello:
  bucket  = "hello-terraform-9273bec5"
  region  = "ap-south-1"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"    ← AWS auto-added this!
      }
    }
  }
  versioning {
    enabled    = false   ← shown here as false (managed by separate resource)
    mfa_delete = false
  }

aws_s3_bucket_versioning.hello:
  versioning_configuration {
    status = "Enabled"   ← our config worked correctly
  }

random_id.suffix:
  hex = "9273bec5"
  dec = "2457059013"
```

**My observation — important discovery:**
- AWS **automatically added AES256 encryption** even though we never configured it
- This is AWS's default security behavior since January 2023 — all new S3 buckets are encrypted by default
- This shows that AWS applies security defaults on top of what Terraform creates
- `versioning.enabled = false` in the bucket resource is normal — versioning is managed by the separate `aws_s3_bucket_versioning` resource

**Verification:** ✅ Full resource details visible, encryption auto-applied by AWS

📸 **Screenshot:** `07_terraform_show.png`
> Take screenshot of terminal showing the full `terraform show` output including `sse_algorithm = "AES256"`

---

### Step 6 — terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes when prompted
```

**Output received:**
```
aws_s3_bucket_versioning.hello: Destroying... [id=hello-terraform-9273bec5]
aws_s3_bucket_versioning.hello: Destruction complete after 0s
aws_s3_bucket.hello: Destroying... [id=hello-terraform-9273bec5]
aws_s3_bucket.hello: Destruction complete after 1s
random_id.suffix: Destroying... [id=knO-xQ]
random_id.suffix: Destruction complete after 0s

Destroy complete! Resources: 3 destroyed.
```

**My observation:**
- Terraform destroyed in reverse dependency order: versioning first, then bucket, then random_id
- This is automatic — Terraform knows the dependency graph
- `terraform.tfstate` is now empty — Terraform's memory is cleared
- The bucket is permanently deleted from AWS — no recovery possible

**Verification in AWS Console:**
- Go to: https://s3.console.aws.amazon.com/s3/buckets?region=ap-south-1
- Confirmed: `hello-terraform-9273bec5` is no longer in the bucket list

📸 **Screenshot:** `08_terraform_destroy.png`
> Take screenshot of terminal showing "Destroy complete! Resources: 3 destroyed"

📸 **Screenshot:** `09_s3_bucket_gone_console.png`
> AWS Console → S3 → screenshot showing the bucket is no longer in the list

---

## Summary

### Command Reference

| Command | Touches AWS? | What it does |
|---------|-------------|--------------|
| `terraform init` | ❌ No | Downloads provider plugins locally |
| `terraform plan` | ❌ No (read-only) | Previews what will change |
| `terraform apply` | ✅ Yes | Creates/modifies resources in AWS |
| `terraform state list` | ❌ No | Lists tracked resources |
| `terraform show` | ❌ No | Shows full resource details from state |
| `terraform destroy` | ✅ Yes | Deletes all managed resources |

### Key Observations from This Phase

1. **`terraform init` is local-only** — downloads plugins, never touches AWS
2. **`terraform plan` is always safe** — read-only preview, run it before every apply
3. **Only `apply` and `destroy` touch AWS** — everything else is local
4. **AWS auto-adds AES256 encryption** to all new S3 buckets (default since 2023)
5. **State file = Terraform's memory** — never edit it manually
6. **Dependency order is automatic** — Terraform creates/destroys in correct order
7. **Random suffix ensures global uniqueness** — S3 bucket names are global across all AWS accounts

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| S3 bucket (empty) | ~5 seconds | $0.00 |
| **Total** | | **$0.00** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `00_aws_cli_auth.png` | `aws sts get-caller-identity` output | ⬜ |
| 2 | `00_terraform_version.png` | `terraform --version` output | ⬜ |
| 3 | `01_terraform_init.png` | "Terraform has been successfully initialized!" | ⬜ |
| 4 | `02_terraform_plan.png` | "Plan: 3 to add, 0 to change, 0 to destroy" | ⬜ |
| 5 | `03_terraform_apply.png` | "Apply complete! Resources: 3 added" | ⬜ |
| 6 | `04_s3_bucket_in_console.png` | S3 Console showing bucket | ⬜ |
| 7 | `05_s3_versioning_enabled.png` | S3 Properties → Versioning: Enabled | ⬜ |
| 8 | `06_terraform_state_list.png` | 3 resources listed | ⬜ |
| 9 | `07_terraform_show.png` | Full state including AES256 encryption | ⬜ |
| 10 | `08_terraform_destroy.png` | "Destroy complete! Resources: 3 destroyed" | ⬜ |
| 11 | `09_s3_bucket_gone_console.png` | S3 Console — bucket no longer exists | ⬜ |

> **Save all screenshots to:**
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\01_hello_terraform_screens\`

---

*Author: Viswanath TGR | LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
