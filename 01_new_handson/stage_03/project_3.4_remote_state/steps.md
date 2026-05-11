# Steps — Project 3.4 Terraform Remote State

## Phase 1 — Bootstrap (Create S3 + DynamoDB)

```bash
cd bootstrap
terraform init
terraform apply

# Note the outputs:
# state_bucket_name = "handson-terraform-state-ACCOUNTID"
# lock_table_name   = "handson-terraform-locks"
```

---

## Phase 2 — Configure Backend in Main Config

Edit `main/backend.tf`:
```hcl
terraform {
  backend "s3" {
    bucket         = "handson-terraform-state-ACCOUNTID"
    key            = "stage-03/project-3.4/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "handson-terraform-locks"
    encrypt        = true
  }
}
```

```bash
cd main
terraform init
# Terraform asks: "Do you want to copy existing state to the new backend?"
# Type: yes
```

---

## Phase 3 — Verify Remote State

```bash
# Apply something
terraform apply -auto-approve

# Verify state is in S3
aws s3 ls s3://handson-terraform-state-ACCOUNTID/stage-03/project-3.4/

# View state file content
aws s3 cp s3://handson-terraform-state-ACCOUNTID/stage-03/project-3.4/terraform.tfstate - | python3 -m json.tool | head -50
```

---

## Phase 4 — Test DynamoDB Locking

```bash
# In terminal 1 — start a slow apply
terraform apply -auto-approve &

# In terminal 2 — try to apply at the same time
terraform apply -auto-approve
# Expected: Error acquiring the state lock
# Error message: ConditionalCheckFailedException
# This proves locking works!
```

---

## Phase 5 — Read Remote State from Another Config

```bash
cd remote_state_consumer

# This config reads outputs from the main config's remote state
terraform init
terraform plan
# Shows: data.terraform_remote_state.main.outputs.vpc_id = "vpc-xxxxxxxx"
```

---

## Phase 6 — State Migration (local → remote)

```bash
# If you have an existing config with local state:
# 1. Add backend block to main.tf
# 2. Run terraform init
# 3. Terraform detects local state and asks to migrate
# 4. Type "yes" — state is copied to S3
# 5. Local terraform.tfstate is now empty (state is in S3)

# Verify migration
terraform state list  # reads from S3 now
```

---

## Phase 7 — Terraform Import

```bash
# Import an existing S3 bucket that wasn't created by Terraform
# First, add the resource block to your config:
# resource "aws_s3_bucket" "existing" {
#   bucket = "my-existing-bucket"
# }

# Then import it
terraform import aws_s3_bucket.existing my-existing-bucket

# Now Terraform manages it
terraform state show aws_s3_bucket.existing
terraform plan  # should show no changes if config matches reality
```

---

## Screenshots to Take
- [ ] S3 bucket created for state storage
- [ ] DynamoDB table with LockID hash key
- [ ] `terraform init` showing backend migration
- [ ] State file visible in S3 console
- [ ] DynamoDB lock entry during apply
- [ ] Lock error when two applies run simultaneously
- [ ] Remote state consumer reading outputs from another config
