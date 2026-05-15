# Hands-on Log — Project 3.1 Phase 4: Terraform Data Sources

**Date:** 2026-05-13
**AWS Account:** 495331821583
**IAM User:** vswnth1
**Region:** ap-south-1 (Mumbai)
**Terraform Version:** v1.7.5
**Working Directory:** `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\04_data_sources\`

---

## Phase Description

Phases 1–3 created resources. This phase does something different — it **reads** existing AWS resources without creating anything. Data sources solve the problem of hardcoded values that break over time.

**Why this phase matters:**
AMI IDs change every time AWS releases a new Amazon Linux version. If you hardcode `ami-0abcd1234`, your config breaks when that AMI is deprecated. Data sources always fetch the latest value dynamically — your code never goes stale.

**What you will learn:**
- How data sources read AWS without creating anything
- 5 data sources: AMI, account identity, region, VPC, subnets, AZs
- Why `terraform apply` with only data sources creates 0 resources
- Real values discovered from your AWS account (ap-south-1)

**Resources created in this phase:**
- **ZERO** — data sources only read, never create

**Total cost: $0.00**

---

## The main.tf File

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
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Data Source 2: Current AWS Account & Region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Data Source 3: Default VPC
data "aws_vpc" "default" {
  default = true
}

# Data Source 4: Subnets in Default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Data Source 5: Availability Zones
data "aws_availability_zones" "available" {
  state = "available"
}

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

**Note:** EC2 instance was intentionally removed. Data sources alone demonstrate the concept at zero cost. The `useful_for_ec2` output shows how these values will be used in Project 3.2.

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
- Only the AWS provider needed — no `random` provider since we're not creating resources
- `terraform init` is still local-only — no AWS interaction yet

**Verification:** ✅ Initialized successfully

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
- Data sources show `Reading...` — NOT `Creating...` — this is the key visual difference
- No `Plan: X to add` line — because zero resources will be created
- All 9 values resolved from your real AWS account in ap-south-1
- The AMI name `al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64` shows the exact version — if you had hardcoded an AMI ID from 6 months ago, it might be deprecated by now
- `useful_for_ec2` output shows exactly what you'll use in Project 3.2 for EC2 creation

**Verification:** ✅ All 9 values discovered from AWS account, zero resources planned

📸 **Screenshot:** `02_terraform_plan.png`
> Take screenshot showing all 9 outputs in "Changes to Outputs" and the message "without changing any real infrastructure"

---

### Step 3 — terraform apply

**Command run:**
```bash
terraform apply
# typed: yes
```

**Output received:**
```
(all data sources read again)

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
- `Resources: 0 added, 0 changed, 0 destroyed` — this is the ONLY Terraform apply that creates nothing in AWS
- Outputs are saved to `terraform.tfstate` — other Terraform configs can read them via `terraform_remote_state`
- `tolist([...])` wrapping is normal — Terraform shows the type explicitly in output
- The `useful_for_ec2` output is ready to use directly in Project 3.2's EC2 resource

**Verification:** ✅ Apply completed with zero AWS resources created

📸 **Screenshot:** `03_terraform_apply.png`
> Take screenshot showing "Apply complete! Resources: 0 added, 0 changed, 0 destroyed" and all 9 outputs

---

### Step 4 — terraform output

**Command run:**
```bash
terraform output
```

**Output received:**
```
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
- All 9 values confirmed and saved in state
- These values are specific to your account (495331821583) and region (ap-south-1)
- If someone else runs this in a different account/region, they'll get different values — that's the power of data sources

**Verification:** ✅ All 9 outputs confirmed

📸 **Screenshot:** `04_terraform_output.png`
> Take screenshot of terminal showing all 9 output values

---

### Step 5 — Verify in AWS Console

**5a. Account ID and Region**

```
AWS Console → Top right corner → click username
Account ID: 495331821583 ✅
Region: Asia Pacific (Mumbai) ap-south-1 ✅
```

**My observation:** The account ID and region in the console match exactly what data sources returned.

📸 **Screenshot:** `05_aws_console_account_region.png`
> Take screenshot of AWS Console top-right showing account ID and region

---

**5b. AMI ID**

```
AWS Console → EC2 → Images → AMIs
Change filter to "Public images"
Search: ami-0627662924eb1b8c6
Name: al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64 ✅
```

**My observation:** The AMI exists and is the latest Amazon Linux 2023 in ap-south-1. If we had hardcoded this ID 6 months ago, it might have been deprecated by now.

📸 **Screenshot:** `06_aws_console_ami.png`
> Take screenshot of EC2 → AMIs showing `ami-0627662924eb1b8c6`

---

**5c. Default VPC**

```
AWS Console → VPC → Your VPCs
Default VPC = Yes ✅
VPC ID: vpc-037f017eee3062491 ✅
IPv4 CIDR: 172.31.0.0/16 ✅
```

**My observation:** Every AWS account has a default VPC. The data source found it automatically — no hardcoding needed.

📸 **Screenshot:** `07_aws_console_vpc.png`
> Take screenshot of VPC console showing default VPC with ID and CIDR

---

**5d. Subnets**

```
AWS Console → VPC → Subnets
Filter by VPC: vpc-037f017eee3062491
3 subnets visible:
  subnet-0b4de952205c30013 → ap-south-1a ✅
  subnet-0b58ab8f767a2690b → ap-south-1b ✅
  subnet-0e133633325b2845b → ap-south-1c ✅
```

**My observation:** 3 subnets — one per AZ. The data source returned all 3 IDs as a list. In Project 3.2, we'll use `[0]` to pick the first one for EC2.

📸 **Screenshot:** `08_aws_console_subnets.png`
> Take screenshot of VPC → Subnets showing 3 subnets with their AZ assignments

---

**5e. Availability Zones**

```
AWS Console → EC2 → Launch Instance → Subnet dropdown
Shows: ap-south-1a, ap-south-1b, ap-south-1c ✅
```

**My observation:** ap-south-1 has 3 AZs. The data source returned all 3 — useful for distributing resources across AZs for high availability.

📸 **Screenshot:** `09_aws_console_azs.png`
> Take screenshot showing 3 availability zones in ap-south-1

---

### No destroy needed

**My observation:**
- Data sources created **zero resources** — there is nothing to destroy
- `terraform destroy` would show `Destroy complete! Resources: 0 destroyed.`
- This is the only phase where you don't need to run destroy
- The state file contains only the cached data source values — no real AWS resources

---

## Summary

### What Was Discovered From Your AWS Account

| Value | Discovered | Source |
|-------|-----------|--------|
| Account ID | `495331821583` | `aws_caller_identity` |
| Region | `ap-south-1` | `aws_region` |
| Latest AMI ID | `ami-0627662924eb1b8c6` | `aws_ami` |
| AMI Name | `al2023-ami-minimal-2023.11.20260509.0-kernel-6.18-x86_64` | `aws_ami` |
| Default VPC ID | `vpc-037f017eee3062491` | `aws_vpc` |
| VPC CIDR | `172.31.0.0/16` | `aws_vpc` |
| Subnet 1 (1a) | `subnet-0b4de952205c30013` | `aws_subnets` |
| Subnet 2 (1b) | `subnet-0b58ab8f767a2690b` | `aws_subnets` |
| Subnet 3 (1c) | `subnet-0e133633325b2845b` | `aws_subnets` |
| AZs | `ap-south-1a/b/c` | `aws_availability_zones` |

### Command Summary

| Command | Touched AWS? | Result |
|---------|-------------|--------|
| `terraform init` | ❌ No | Downloaded AWS provider |
| `terraform plan` | ❌ Read-only | Discovered 9 values |
| `terraform apply` | ❌ No resources | Saved outputs to state |
| `terraform output` | ❌ No | Displayed all 9 values |

### Key Observations from This Phase

1. **Data sources show `Reading...`** — not `Creating...` — the key visual difference
2. **`apply` with only data sources = `Resources: 0 added`** — nothing created in AWS
3. **AMI IDs are region-specific** — always use data source, never hardcode
4. **No destroy needed** — nothing was created, nothing to clean up
5. **`useful_for_ec2` output** — ready to use directly in Project 3.2 EC2 resource
6. **Data sources reference resources not managed by this config** — the default VPC was not created by Terraform, but we can read it

### Where to Find Each Value in AWS Console

| Value | AWS Console Path |
|-------|-----------------|
| Account ID | Top right → username dropdown |
| Region | Top navigation bar |
| AMI ID | EC2 → Images → AMIs → Public images |
| Default VPC | VPC → Your VPCs → Default VPC = Yes |
| Subnets | VPC → Subnets → filter by VPC ID |
| AZs | EC2 → Launch Instance → Subnet dropdown |

### Cost

| Resource | Cost |
|----------|------|
| Data sources (read-only) | $0.00 |
| **Total** | **$0.00** |

---

## Screenshots Checklist

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `01_terraform_init.png` | "Terraform has been successfully initialized!" | ⬜ |
| 2 | `02_terraform_plan.png` | All 9 outputs + "without changing any real infrastructure" | ⬜ |
| 3 | `03_terraform_apply.png` | "Resources: 0 added, 0 changed, 0 destroyed" + all 9 outputs | ⬜ |
| 4 | `04_terraform_output.png` | All 9 output values | ⬜ |
| 5 | `05_aws_console_account_region.png` | Account ID 495331821583 and region ap-south-1 | ⬜ |
| 6 | `06_aws_console_ami.png` | EC2 → AMIs showing `ami-0627662924eb1b8c6` | ⬜ |
| 7 | `07_aws_console_vpc.png` | Default VPC `vpc-037f017eee3062491` with CIDR | ⬜ |
| 8 | `08_aws_console_subnets.png` | 3 subnets with AZ assignments | ⬜ |
| 9 | `09_aws_console_azs.png` | ap-south-1a, ap-south-1b, ap-south-1c | ⬜ |

> **Save all screenshots to:**
> `D:\1.projects\AI\my-aws\01_new_handson\stage_03\project_3.1_terraform_basics\screenshots\04_data_sources\`

---

*Author: Viswanath TGR | LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Series: AWS Terraform Hands-on — 62 Projects*
