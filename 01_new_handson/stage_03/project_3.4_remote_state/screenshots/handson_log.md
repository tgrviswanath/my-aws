# Hands-on Log — Project 3.4: Terraform Remote State

**Date:** 2026-05-16
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5

---

## Project Description

This project moves Terraform state from a local file to **S3 with DynamoDB locking** — enabling team collaboration, state sharing between configs, and safe concurrent operations. It also demonstrates state migration, reading remote state from another config, and importing existing AWS resources into Terraform management.

**Why this project matters:**
In Projects 3.1–3.3, state was stored in `terraform.tfstate` on the local machine. That breaks the moment two people work on the same infrastructure — one person's apply overwrites the other's state. This project solves that permanently: state lives in S3, DynamoDB prevents concurrent applies, and any config can read another config's outputs.

**Architecture:**
```
terraform apply
    │
    ├── Acquires DynamoDB lock (LockID = state key)
    │       If another apply is running → ConditionalCheckFailed error
    │
    ├── Reads current state from S3
    │       s3://handson-terraform-state-495331821583/stage-03/project-3.4/...
    │
    ├── Calculates diff (plan)
    │
    ├── Creates/modifies/destroys resources in AWS
    │
    ├── Writes new state back to S3
    │
    └── Releases DynamoDB lock
```

**Resources created:**
| Category | Resource | Notes |
|----------|----------|-------|
| S3 | `handson-terraform-state-495331821583` | State bucket — versioning + encryption + public access blocked |
| DynamoDB | `handson-terraform-locks` | Lock table — PAY_PER_REQUEST, hash key = LockID |
| S3 | `handson-app-data-495331821583` | Demo app bucket — managed via remote state |
| SSM Parameter | `/handson/migration-demo/message` | Migration demo resource |
| **Total cost** | | ~$0.02/month |

---

## File Structure

```
project_3.4_remote_state/
├── bootstrap/
│   └── main.tf              ← Creates S3 bucket + DynamoDB table (local state)
├── main/
│   ├── main.tf              ← App bucket — uses S3 remote backend
│   └── backend.tf           ← S3 backend config pointing to bootstrap bucket
├── migration_demo/
│   └── main.tf              ← SSM parameter — demonstrates local → remote migration
├── import_demo/
│   └── main.tf              ← Demonstrates terraform import of existing resource
├── remote_state_consumer/
│   └── main.tf              ← Reads outputs from main/ via terraform_remote_state
├── code/
│   └── state_manager.py     ← Python helper for bootstrap and lock management
├── docs/
│   └── architecture.md
├── screenshots/
│   └── handson_log.md       ← This file
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
- Account ID 495331821583 is embedded in the S3 bucket name — ensures global uniqueness
- IAM user needs S3, DynamoDB, and SSM permissions for this project

**Verification:** OK — AWS CLI configured correctly

[Screenshot: 00_aws_cli_auth.png]
> Terminal showing aws sts get-caller-identity output

---

### Pre-req 2 — Understand the Chicken-and-Egg Problem

**The problem:**
To use S3 as a Terraform backend, the S3 bucket must already exist.
But if you use Terraform to create the S3 bucket, where does THAT state go?

**The solution — bootstrap pattern:**
```
Step 1: Run bootstrap/ with LOCAL state
        → Creates S3 bucket + DynamoDB table
        → bootstrap/terraform.tfstate stays local (intentional)

Step 2: All other configs use the S3 bucket as their backend
        → State stored remotely from this point forward
        → bootstrap/ is never touched again
```

**My observation:**
- The bootstrap config intentionally uses local state — it is the one exception
- The bootstrap bucket should have `lifecycle { prevent_destroy = true }` in production
- Never run `terraform destroy` on bootstrap — it would delete the state bucket for all other configs

---

## Phase 1 — Bootstrap (Create S3 + DynamoDB)

### Step 1 — terraform init (bootstrap)

**Command run:**
```bash
cd bootstrap
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

**My observation:**
- No backend block in bootstrap/main.tf — state stays local (intentional)
- This is the only config in the project that uses local state
- Provider v5.100.0 downloaded — same version as all other projects

**Verification:** OK — Initialized with local backend

[Screenshot: 01_bootstrap_init.png]
> Terminal showing terraform init for bootstrap directory

---

### Step 2 — terraform apply (bootstrap)

**Command run:**
```bash
terraform apply -auto-approve
```

**Output received:**
```
data.aws_caller_identity.current: Reading...
data.aws_caller_identity.current: Read complete after 0s [id=495331821583]

aws_s3_bucket.state: Creating...
aws_s3_bucket.state: Creation complete after 2s [id=handson-terraform-state-495331821583]
aws_s3_bucket_versioning.state: Creating...
aws_s3_bucket_versioning.state: Creation complete after 1s
aws_s3_bucket_server_side_encryption_configuration.state: Creating...
aws_s3_bucket_server_side_encryption_configuration.state: Creation complete after 0s
aws_s3_bucket_public_access_block.state: Creating...
aws_s3_bucket_public_access_block.state: Creation complete after 0s
aws_dynamodb_table.locks: Creating...
aws_dynamodb_table.locks: Creation complete after 7s [id=handson-terraform-locks]

Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
state_bucket_name = "handson-terraform-state-495331821583"
lock_table_name   = "handson-terraform-locks"
backend_config    = <<EOT
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "YOUR_PROJECT/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
EOT
```

**What was created:**
| Resource | Name | Configuration |
|----------|------|---------------|
| S3 Bucket | `handson-terraform-state-495331821583` | Versioning ON, AES256, public access blocked |
| S3 Versioning | Enabled | Allows rollback to previous state versions |
| S3 Encryption | AES256 | State file encrypted at rest |
| S3 Public Access Block | All 4 blocked | State file never publicly accessible |
| DynamoDB Table | `handson-terraform-locks` | PAY_PER_REQUEST, hash key = `LockID` |

**My observation:**
- `data.aws_caller_identity.current` resolved account ID — bucket name is auto-generated, no hardcoding
- DynamoDB took 7s — slightly slower than S3 resources
- The `backend_config` output prints the exact block to paste into other configs — very convenient
- Hash key MUST be exactly `LockID` — Terraform hardcodes this string when acquiring locks
- `PAY_PER_REQUEST` billing — only pay for actual lock operations, not provisioned capacity

**Verification:** OK — S3 bucket and DynamoDB table created

[Screenshot: 02_bootstrap_apply_complete.png]
> Terminal showing "Apply complete! Resources: 5 added" with bucket and table names in outputs

---

### Step 3 — Verify Bootstrap Resources in AWS Console

**S3 Console:**
```
AWS Console → S3 → handson-terraform-state-495331821583
Versioning:    Enabled
Encryption:    AES256
Public access: Blocked (all 4 settings)
```

**DynamoDB Console:**
```
AWS Console → DynamoDB → Tables → handson-terraform-locks
Status:       Active
Billing mode: PAY_PER_REQUEST
Partition key: LockID (String)
```

**My observation:**
- S3 versioning means every state write creates a new version — you can roll back if state gets corrupted
- The DynamoDB table is empty at this point — lock entries are created and deleted during apply
- Public access block on the state bucket is critical — state files contain sensitive resource details

**Verification:** OK — Both resources visible and correctly configured in AWS Console

[Screenshot: 03_s3_state_bucket_console.png]
> S3 Console showing handson-terraform-state-495331821583 with versioning enabled

[Screenshot: 04_dynamodb_table_console.png]
> DynamoDB Console showing handson-terraform-locks table with LockID partition key

---

## Phase 2 — Configure Remote Backend in Main Config

### Step 4 — Review backend.tf

**File: main/backend.tf**
```hcl
terraform {
  backend "s3" {
    bucket         = "handson-terraform-state-495331821583"
    key            = "stage-03/project-3.4/main/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
```

**What each field does:**
- `bucket` — the S3 bucket created in bootstrap
- `key` — the path inside the bucket where state is stored (like a folder structure)
- `region` — must match the region where the bucket was created
- `dynamodb_table` — the table created in bootstrap for locking
- `encrypt` — encrypts state in transit (in addition to S3 server-side encryption)

**My observation:**
- The `key` is the most important field for organisation — use a consistent naming convention
- Different projects use different keys in the same bucket — one bucket for all state
- `encrypt = true` adds client-side encryption on top of S3's AES256 — double encryption

---

### Step 5 — terraform init (main — migrates to remote backend)

**Command run:**
```bash
cd main
terraform init
```

**Output received:**
```
Initializing the backend...

Successfully configured the backend "s3"! Terraform will automatically
use this backend unless the backend configuration changes.

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)

Terraform has been successfully initialized!
```

**My observation:**
- "Successfully configured the backend s3!" — Terraform connected to S3 and verified the bucket exists
- If there was existing local state, Terraform would ask: "Do you want to copy existing state to the new backend?" — type yes
- From this point, all state reads and writes go to S3 — the local machine holds no state
- The `.terraform/terraform.tfstate` file now contains backend metadata, not actual resource state

**Verification:** OK — Backend configured, connected to S3

[Screenshot: 05_main_init_backend.png]
> Terminal showing "Successfully configured the backend s3!" message

---

### Step 6 — terraform apply (main)

**Command run:**
```bash
terraform apply -auto-approve
```

**Output received:**
```
data.aws_caller_identity.current: Reading...
data.aws_caller_identity.current: Read complete after 0s [id=495331821583]

aws_s3_bucket.app_data: Creating...
aws_s3_bucket.app_data: Creation complete after 2s [id=handson-app-data-495331821583]
aws_s3_bucket_versioning.app_data: Creating...
aws_s3_bucket_versioning.app_data: Creation complete after 1s
aws_s3_bucket_server_side_encryption_configuration.app_data: Creating...
aws_s3_bucket_server_side_encryption_configuration.app_data: Creation complete after 0s
aws_s3_bucket_public_access_block.app_data: Creating...
aws_s3_bucket_public_access_block.app_data: Creation complete after 0s

Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

Outputs:
app_bucket_name = "handson-app-data-495331821583"
app_bucket_arn  = "arn:aws:s3:::handson-app-data-495331821583"
account_id      = "495331821583"
region          = "ap-south-1"
```

**My observation:**
- Apply succeeded — state was written to S3, not to a local file
- No `terraform.tfstate` file was created in the `main/` directory — state is in S3
- The outputs (app_bucket_name, app_bucket_arn) are now readable by other configs via `terraform_remote_state`

**Verification:** OK — 4 resources created, state stored in S3

[Screenshot: 06_main_apply_complete.png]
> Terminal showing "Apply complete! Resources: 4 added" with outputs

---

## Phase 3 — Verify Remote State in S3

### Step 7 — Verify State File in S3 Console

**AWS Console check:**
```
S3 → handson-terraform-state-495331821583
→ stage-03/
  → project-3.4/
    → main/
      → terraform.tfstate   (size: ~2KB)
```

**Command run:**
```bash
aws s3 ls s3://handson-terraform-state-495331821583/stage-03/project-3.4/main/
```

**Output received:**
```
2026-05-16 10:23:45       2048 terraform.tfstate
```

**My observation:**
- State file is in S3 — not on the local machine
- The key path `stage-03/project-3.4/main/terraform.tfstate` matches exactly what was configured in backend.tf
- S3 versioning means this file has a version history — previous states are preserved

[Screenshot: 07_state_file_in_s3.png]
> S3 Console showing terraform.tfstate file at stage-03/project-3.4/main/ path

---

### Step 8 — Verify DynamoDB Lock During Apply

**What happens during terraform apply:**
```
1. Terraform writes a lock entry to DynamoDB:
   LockID = "handson-terraform-state-495331821583/stage-03/project-3.4/main/terraform.tfstate"
   Info   = { "Operation": "OperationTypeApply", "Who": "vswnth1@machine", ... }

2. Resources are created/modified

3. Terraform deletes the lock entry from DynamoDB
```

**Lock error (if two applies run simultaneously):**
```
Error: Error acquiring the state lock

Error message: ConditionalCheckFailedException: The conditional request failed
Lock Info:
  ID:        abc123-def456-...
  Path:      handson-terraform-state-495331821583/stage-03/...
  Operation: OperationTypeApply
  Who:       vswnth1@machine
  Created:   2026-05-16 10:23:45
```

**My observation:**
- The lock entry exists only during apply — the DynamoDB table is empty between applies
- `ConditionalCheckFailedException` is the DynamoDB error when a lock already exists
- If Terraform crashes mid-apply, the lock may remain — use `terraform force-unlock LOCK_ID` to clear it
- The lock ID is a UUID — unique per apply operation

[Screenshot: 08_dynamodb_lock_entry.png]
> DynamoDB Console showing lock entry during terraform apply (Items tab)

---

## Phase 4 — Read Remote State from Another Config

### Step 9 — terraform_remote_state Data Source

**File: remote_state_consumer/main.tf**
```hcl
data "terraform_remote_state" "main" {
  backend = "s3"
  config = {
    bucket = "handson-terraform-state-495331821583"
    key    = "stage-03/project-3.4/main/terraform.tfstate"
    region = "ap-south-1"
  }
}

output "app_bucket_name_from_remote_state" {
  value = data.terraform_remote_state.main.outputs.app_bucket_name
}
```

**Command run:**
```bash
cd remote_state_consumer
terraform init
terraform plan
```

**Output received:**
```
data.terraform_remote_state.main: Reading...
data.terraform_remote_state.main: Read complete after 1s

Changes to Outputs:
  + app_bucket_name_from_remote_state = "handson-app-data-495331821583"
  + app_bucket_arn_from_remote_state  = "arn:aws:s3:::handson-app-data-495331821583"
  + account_id_from_remote_state      = "495331821583"
  + region_from_remote_state          = "ap-south-1"

You can apply this plan to save these new output values to the Terraform
state, without changing any real infrastructure.
```

**My observation:**
- `terraform_remote_state` reads the state file from S3 — no API calls to AWS resources
- The consumer config can access ANY output that the main config exported
- This is how large teams share infrastructure details — VPC IDs, subnet IDs, security group IDs
- The consumer only needs READ access to the S3 bucket — not write access
- This is safer than hardcoding resource IDs — if the main config changes, the consumer picks up the new value automatically

**Verification:** OK — Remote state outputs readable from consumer config

[Screenshot: 09_remote_state_consumer_plan.png]
> Terminal showing terraform plan for remote_state_consumer with outputs from main config

---

## Phase 5 — State Migration (Local to Remote)

### Step 10 — Migration Demo

**Scenario:**
The `migration_demo/` config starts with local state (an SSM parameter already created).
We add a backend block and run `terraform init` to migrate the state to S3.

**Step 10a — Create resource with local state first:**
```bash
cd migration_demo
# (backend block commented out in main.tf)
terraform init
terraform apply -auto-approve
```

**Output:**
```
aws_ssm_parameter.demo: Creating...
aws_ssm_parameter.demo: Creation complete after 1s [id=/handson/migration-demo/message]

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

**Local state file created:** `migration_demo/terraform.tfstate`

---

**Step 10b — Add backend block and migrate:**
```bash
# backend block added to migration_demo/main.tf
terraform init
```

**Output received:**
```
Initializing the backend...
Do you want to copy existing state to the new backend?
  Pre-existing state was found while migrating the previous "local" backend to the
  newly configured "s3" backend. No existing state was found in the newly
  configured "s3" backend. Do you want to copy this state to the new backend?
  Enter a value: yes

Successfully configured the backend "s3"!
Terraform has been successfully initialized!
```

**After migration:**
```bash
terraform state list
# Output: aws_ssm_parameter.demo
# State is now read from S3 — not from local file

# Local terraform.tfstate is now empty:
# { "version": 4, "terraform_version": "1.7.5", "serial": 0, "lineage": "...", "outputs": {}, "resources": [] }
```

**My observation:**
- Terraform detected the existing local state and offered to migrate it — no manual copying needed
- After migration, the local `terraform.tfstate` is emptied — state lives in S3
- `terraform state list` now reads from S3 — the local file is just a placeholder
- This is the standard migration path for any existing project moving to remote state

**Verification:** OK — State migrated to S3, local file emptied

[Screenshot: 10_state_migration_prompt.png]
> Terminal showing "Do you want to copy existing state to the new backend?" prompt

[Screenshot: 11_state_migration_complete.png]
> Terminal showing "Successfully configured the backend s3!" after typing yes

---

## Phase 6 — terraform import

### Step 11 — Import Existing Resource

**Scenario:**
The S3 bucket `handson-app-data-495331821583` was created by `main/` and already exists in AWS.
The `import_demo/` config has never managed it. We import it so Terraform can track it.

**Step 11a — terraform init:**
```bash
cd import_demo
terraform init
```

**Step 11b — terraform import:**
```bash
terraform import aws_s3_bucket.imported handson-app-data-495331821583
```

**Output received:**
```
aws_s3_bucket.imported: Importing from ID "handson-app-data-495331821583"...
aws_s3_bucket.imported: Import prepared!
  Prepared aws_s3_bucket for import
aws_s3_bucket.imported: Refreshing state... [id=handson-app-data-495331821583]

Import successful!

The resources that were imported are shown above. These resources are now in
your Terraform state and will henceforth be managed by Terraform.
```

**Step 11c — Import sub-resources:**
```bash
terraform import aws_s3_bucket_versioning.imported handson-app-data-495331821583
terraform import aws_s3_bucket_server_side_encryption_configuration.imported handson-app-data-495331821583
terraform import aws_s3_bucket_public_access_block.imported handson-app-data-495331821583
```

**Step 11d — terraform plan (verify no drift):**
```bash
terraform plan
```

**Output received:**
```
aws_s3_bucket.imported: Refreshing state... [id=handson-app-data-495331821583]
aws_s3_bucket_versioning.imported: Refreshing state...
aws_s3_bucket_server_side_encryption_configuration.imported: Refreshing state...
aws_s3_bucket_public_access_block.imported: Refreshing state...

No changes. Your infrastructure matches the configuration.
```

**My observation:**
- `terraform import` only updates the state file — it does NOT modify the resource in AWS
- After import, `terraform plan` must show "No changes" — if it shows changes, the config does not match reality
- You must write the resource block BEFORE importing — Terraform needs the config to validate against
- Import is a one-time operation — after this, Terraform manages the resource normally
- Sub-resources (versioning, encryption, public access block) must be imported separately

**Verification:** OK — Resource imported, plan shows no changes

[Screenshot: 12_terraform_import.png]
> Terminal showing "Import successful!" for aws_s3_bucket.imported

[Screenshot: 13_plan_no_changes_after_import.png]
> Terminal showing "No changes. Your infrastructure matches the configuration."

---

## Phase 7 — terraform state list and terraform show

### Step 12 — Inspect Remote State

**Command run (from main/):**
```bash
cd main
terraform state list
```

**Output received:**
```
data.aws_caller_identity.current
aws_s3_bucket.app_data
aws_s3_bucket_public_access_block.app_data
aws_s3_bucket_server_side_encryption_configuration.app_data
aws_s3_bucket_versioning.app_data
```

**Command run:**
```bash
terraform state show aws_s3_bucket.app_data
```

**Key output:**
```
# aws_s3_bucket.app_data:
resource "aws_s3_bucket" "app_data" {
    bucket                      = "handson-app-data-495331821583"
    bucket_domain_name          = "handson-app-data-495331821583.s3.amazonaws.com"
    bucket_regional_domain_name = "handson-app-data-495331821583.s3.ap-south-1.amazonaws.com"
    hosted_zone_id              = "Z11RGJOFQNVJUP"
    id                          = "handson-app-data-495331821583"
    region                      = "ap-south-1"
    tags                        = {
        "ManagedBy" = "terraform"
        "Name"      = "handson-app-data"
        "Project"   = "handson"
        "Stage"     = "stage-03"
    }
}
```

**My observation:**
- `terraform state list` reads from S3 — no local state file needed
- `terraform state show` gives the full resource details including AWS-generated fields
- The `bucket_regional_domain_name` is auto-populated by AWS — not in our config
- State commands work identically whether state is local or remote — the backend is transparent

**Verification:** OK — State readable from S3

[Screenshot: 14_terraform_state_list.png]
> Terminal showing terraform state list output reading from S3 backend

---

## Summary

### All Resources Created

| Resource | Name / ID | Config | Status |
|----------|-----------|--------|--------|
| S3 State Bucket | `handson-terraform-state-495331821583` | bootstrap/ | Active |
| S3 Versioning | Enabled | bootstrap/ | Active |
| S3 Encryption | AES256 | bootstrap/ | Active |
| S3 Public Access Block | All blocked | bootstrap/ | Active |
| DynamoDB Lock Table | `handson-terraform-locks` | bootstrap/ | Active |
| S3 App Bucket | `handson-app-data-495331821583` | main/ | Active |
| SSM Parameter | `/handson/migration-demo/message` | migration_demo/ | Created then migrated |

### Command Summary

| Command | Directory | Touches AWS? | Result |
|---------|-----------|-------------|--------|
| `terraform init` | bootstrap/ | No | Local backend initialized |
| `terraform apply` | bootstrap/ | Yes | S3 bucket + DynamoDB created |
| `terraform init` | main/ | Yes (S3 backend) | Remote backend configured |
| `terraform apply` | main/ | Yes | App bucket created, state in S3 |
| `terraform init` | remote_state_consumer/ | Yes (S3 read) | Remote state data source ready |
| `terraform plan` | remote_state_consumer/ | Yes (S3 read) | Outputs from main/ visible |
| `terraform init` | migration_demo/ | Yes (S3 backend) | Local state migrated to S3 |
| `terraform import` | import_demo/ | Yes (S3 read) | Existing bucket imported |
| `terraform plan` | import_demo/ | Yes (S3 read) | No changes — import verified |
| `terraform state list` | main/ | Yes (S3 read) | 5 resources listed from S3 |

### Key Observations from This Project

1. **Bootstrap uses local state intentionally** — the chicken-and-egg problem requires this one exception
2. **DynamoDB hash key must be exactly `LockID`** — Terraform hardcodes this string, any other name breaks locking
3. **`terraform init` migrates state automatically** — detects local state and offers to copy it to the new backend
4. **After migration, local `terraform.tfstate` is emptied** — state lives in S3, local file is a placeholder
5. **`terraform_remote_state` reads S3 directly** — no API calls to AWS resources, just reads the state file
6. **`terraform import` only updates state** — it does NOT modify the resource in AWS
7. **After import, plan must show "No changes"** — if it shows changes, the config does not match reality
8. **Sub-resources must be imported separately** — versioning, encryption, public access block each need their own import
9. **S3 versioning on state bucket is critical** — allows rollback if state gets corrupted
10. **Lock entry exists only during apply** — DynamoDB table is empty between operations

### Cost

| Resource | Duration | Cost |
|----------|----------|------|
| S3 state bucket (< 1MB) | Permanent | ~$0.01/month |
| DynamoDB (PAY_PER_REQUEST) | Permanent | ~$0.00/month (free tier) |
| S3 app bucket (empty) | ~30 min | $0.00 |
| SSM parameter | ~10 min | $0.00 |
| **Total session** | | **~$0.01** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | 00_aws_cli_auth.png | aws sts get-caller-identity output | Add screenshot |
| 2 | 01_bootstrap_init.png | terraform init for bootstrap directory | Add screenshot |
| 3 | 02_bootstrap_apply_complete.png | "Apply complete! Resources: 5 added" with outputs | Add screenshot |
| 4 | 03_s3_state_bucket_console.png | S3 Console showing state bucket with versioning | Add screenshot |
| 5 | 04_dynamodb_table_console.png | DynamoDB Console showing lock table with LockID key | Add screenshot |
| 6 | 05_main_init_backend.png | "Successfully configured the backend s3!" | Add screenshot |
| 7 | 06_main_apply_complete.png | "Apply complete! Resources: 4 added" with outputs | Add screenshot |
| 8 | 07_state_file_in_s3.png | S3 Console showing terraform.tfstate at correct path | Add screenshot |
| 9 | 08_dynamodb_lock_entry.png | DynamoDB Items tab showing lock entry during apply | Add screenshot |
| 10 | 09_remote_state_consumer_plan.png | terraform plan showing outputs from main config | Add screenshot |
| 11 | 10_state_migration_prompt.png | "Do you want to copy existing state?" prompt | Add screenshot |
| 12 | 11_state_migration_complete.png | "Successfully configured the backend s3!" after migration | Add screenshot |
| 13 | 12_terraform_import.png | "Import successful!" for aws_s3_bucket.imported | Add screenshot |
| 14 | 13_plan_no_changes_after_import.png | "No changes. Your infrastructure matches the configuration." | Add screenshot |
| 15 | 14_terraform_state_list.png | terraform state list reading from S3 backend | Add screenshot |

Save all screenshots to:
D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.4_remote_state\screenshots\

---

*Author: Viswanath TGR*
*LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
