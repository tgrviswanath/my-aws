# Hands-on Log — Project 3.1 Phase 1: Hello Terraform

**Date:** 2026-05-12
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**AWS CLI Version:** v2.x

---

## Environment Setup

### Step 1 — Verified AWS CLI

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

**Result:** ✅ AWS CLI configured and authenticated as `vswnth1`

---

### Step 2 — Verified Terraform Installation

**Command run:**
```bash
terraform --version
```

**Output received:**
```
Terraform v1.7.5
on windows_amd64
```

**Result:** ✅ Terraform installed and working

---

## Phase 1 — Hello Terraform (First Resource Ever)

**Working directory:**
```
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\01_hello_terraform\
```

**File used:** `main.tf`

```hcl
terraform {
  required_providers {
    aws    = { source = "hashicorp/aws"    version = "~> 5.0" }
    random = { source = "hashicorp/random" version = "~> 3.0" }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "ap-south-1"
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
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "hello" {
  bucket = aws_s3_bucket.hello.id
  versioning_configuration { status = "Enabled" }
}

output "bucket_name" { value = aws_s3_bucket.hello.bucket }
output "bucket_arn"  { value = aws_s3_bucket.hello.arn }
```

---

### Command 1 — terraform init

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

**What happened:**
- Downloaded AWS provider plugin (v5.100.0) to local `.terraform/` folder
- Downloaded Random provider plugin (v3.8.1) to local `.terraform/` folder
- Created `.terraform.lock.hcl` lock file
- **Nothing created in AWS**

**Result:** ✅ Providers downloaded successfully

📸 **Screenshot:** `01_terraform_init.png`
> Take screenshot of the terminal showing the full `terraform init` output above

---

### Command 2 — terraform plan

**Command run:**
```bash
terraform plan
```

**Key output:**
```
+ aws_s3_bucket.hello            will be created
+ aws_s3_bucket_versioning.hello will be created
+ random_id.suffix               will be created

Plan: 3 to add, 0 to change, 0 to destroy.
```

**What happened:**
- Terraform connected to AWS and checked current state
- Showed exactly what would be created
- **Nothing created in AWS yet**
- Values showing `(known after apply)` = AWS will generate them at creation time

**Result:** ✅ Plan shows 3 resources to create

📸 **Screenshot:** `02_terraform_plan.png`
> Take screenshot of the terminal showing the plan output with "Plan: 3 to add"

---

### Command 3 — terraform apply

**Command run:**
```bash
terraform apply
# typed: yes
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
| Resource | Name | Region |
|----------|------|--------|
| S3 Bucket | `hello-terraform-9273bec5` | ap-south-1 |
| S3 Versioning | Enabled on above bucket | ap-south-1 |
| Random ID | `9273bec5` (hex suffix) | local only |

**Result:** ✅ S3 bucket created in AWS Mumbai region

📸 **Screenshot:** `03_terraform_apply.png`
> Take screenshot of the terminal showing "Apply complete! Resources: 3 added"

📸 **Screenshot:** `04_s3_bucket_in_console.png`
> Go to AWS Console → S3 → take screenshot showing `hello-terraform-9273bec5` bucket in the list

📸 **Screenshot:** `05_s3_versioning_enabled.png`
> Click the bucket → Properties tab → scroll to Versioning → take screenshot showing "Versioning: Enabled"

---

### Command 4 — terraform state list

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

**What this shows:**
- Terraform is tracking 3 resources in its state file
- State file = `terraform.tfstate` in the working directory
- This is Terraform's "memory" of what it created

**Result:** ✅ All 3 resources tracked in state

📸 **Screenshot:** `06_terraform_state_list.png`
> Take screenshot of the terminal showing the 3 resources listed

---

### Command 5 — terraform show

**Command run:**
```bash
terraform show
```

**Key details from output:**
```
aws_s3_bucket.hello:
  bucket  = "hello-terraform-9273bec5"
  region  = "ap-south-1"
  sse_algorithm = "AES256"        ← AWS auto-added encryption
  versioning { enabled = true }   ← our config worked

random_id.suffix:
  hex = "9273bec5"
  dec = "2457059013"
```

**Interesting observation:**
- AWS automatically added `AES256` encryption even though we didn't configure it
- This is AWS's default security behavior (enabled by default since 2023)

**Result:** ✅ Full resource details visible in state

📸 **Screenshot:** `07_terraform_show.png`
> Take screenshot of the terminal showing the full terraform show output

---

### Command 6 — terraform destroy

**Command run:**
```bash
terraform destroy
# typed: yes
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

**What happened:**
- Versioning config removed first (dependency order)
- S3 bucket deleted from AWS
- Random ID removed from local state
- `terraform.tfstate` is now empty

**Result:** ✅ All resources deleted. AWS account clean.

📸 **Screenshot:** `08_terraform_destroy.png`
> Take screenshot of the terminal showing "Destroy complete! Resources: 3 destroyed"

📸 **Screenshot:** `09_s3_bucket_gone_console.png`
> Go to AWS Console → S3 → take screenshot showing the bucket is no longer in the list

---

## Summary

| Command | AWS Touched? | Result |
|---------|-------------|--------|
| `terraform init` | ❌ No | Downloaded providers locally |
| `terraform plan` | ❌ No | Previewed 3 resources |
| `terraform apply` | ✅ Yes | Created S3 bucket in ap-south-1 |
| `terraform state list` | ❌ No | Listed 3 tracked resources |
| `terraform show` | ❌ No | Showed full resource details |
| `terraform destroy` | ✅ Yes | Deleted all 3 resources |

## Key Concepts Learned

- `terraform init` only downloads plugins — never touches AWS
- `terraform plan` is always safe — read-only preview
- Only `apply` and `destroy` make changes in AWS
- State file (`terraform.tfstate`) is Terraform's memory
- AWS auto-adds encryption to S3 buckets by default
- Bucket names must be globally unique — random suffix solves this
- Always `destroy` after learning to avoid costs

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
| 2 | `02_terraform_plan.png` | ⬜ Add screenshot |
| 3 | `03_terraform_apply.png` | ⬜ Add screenshot |
| 4 | `04_s3_bucket_in_console.png` | ⬜ Add screenshot |
| 5 | `05_s3_versioning_enabled.png` | ⬜ Add screenshot |
| 6 | `06_terraform_state_list.png` | ⬜ Add screenshot |
| 7 | `07_terraform_show.png` | ⬜ Add screenshot |
| 8 | `08_terraform_destroy.png` | ⬜ Add screenshot |
| 9 | `09_s3_bucket_gone_console.png` | ⬜ Add screenshot |

> Save all screenshots to:
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\01_hello_terraform_screens\`
