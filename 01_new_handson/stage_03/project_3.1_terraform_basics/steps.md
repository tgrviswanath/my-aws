# Steps — Project 3.1 Terraform Basics

## Phase 1 — Hello Terraform (First Resource)

```bash
cd 01_hello_terraform
terraform init      # download AWS provider
terraform fmt       # format code
terraform validate  # check syntax
terraform plan      # preview what will be created
terraform apply     # create the resource
terraform show      # inspect current state
terraform destroy   # remove the resource
```

---

## Phase 2 — Variables

```bash
cd 02_variables

# Apply with default values
terraform apply

# Override a variable at runtime
terraform apply -var="bucket_name=my-custom-bucket"

# Use a .tfvars file
terraform apply -var-file="dev.tfvars"

# Use environment variables
export TF_VAR_bucket_name="env-bucket"
terraform apply
```

---

## Phase 3 — Outputs

```bash
cd 03_outputs
terraform apply

# View all outputs
terraform output

# Get a specific output value (useful in scripts)
terraform output -raw bucket_name
terraform output -json
```

---

## Phase 4 — Data Sources

```bash
cd 04_data_sources

# Data sources READ existing resources — they don't create anything
# Example: get the latest Amazon Linux AMI ID automatically
terraform plan
# Notice: data.aws_ami.amazon_linux.id is resolved at plan time
```

---

## Phase 5 — Locals

```bash
cd 05_locals

# Locals are computed values — like variables but derived
# Example: build a consistent name prefix from environment + project
terraform plan
# Notice: local.name_prefix is used across multiple resources
```

---

## Phase 6 — State Inspection

```bash
# List all resources in state
terraform state list

# Show details of a specific resource
terraform state show aws_s3_bucket.example

# Move a resource in state (rename without recreating)
terraform state mv aws_s3_bucket.old_name aws_s3_bucket.new_name

# Remove a resource from state (stop managing it, don't delete it)
terraform state rm aws_s3_bucket.example

# Import an existing resource into state
terraform import aws_s3_bucket.example my-existing-bucket
```

---

## Phase 7 — Useful Commands

```bash
# Format all .tf files recursively
terraform fmt -recursive

# Validate syntax
terraform validate

# Show dependency graph (requires graphviz)
terraform graph | dot -Tsvg > graph.svg

# Refresh state from real AWS (sync state with reality)
terraform refresh

# Target a specific resource only
terraform apply -target=aws_s3_bucket.example

# Auto-approve (skip confirmation prompt — use carefully)
terraform apply -auto-approve
```

---

## Screenshots to Take
- [ ] `terraform init` output showing provider download
- [ ] `terraform plan` output showing resources to create
- [ ] `terraform apply` output showing resources created
- [ ] `terraform output` showing exported values
- [ ] `terraform state list` showing managed resources
- [ ] `terraform destroy` output showing resources removed
