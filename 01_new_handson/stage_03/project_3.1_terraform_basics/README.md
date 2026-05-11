# Project 3.1 — Terraform Basics

## What This Does
Learns core Terraform concepts by building simple AWS resources from scratch — providers, resources, variables, outputs, and state management.

## Concepts Covered

| Concept | Description |
|---------|-------------|
| Provider | Plugin that talks to AWS API |
| Resource | An AWS resource to create (S3, EC2, etc.) |
| Variable | Input parameter — makes configs reusable |
| Output | Value exported after apply (IP, ARN, etc.) |
| State | `terraform.tfstate` — tracks what Terraform manages |
| Plan | Preview changes before applying |
| Apply | Execute the changes |
| Destroy | Remove all managed resources |
| Data source | Read existing AWS resources (not create) |
| `depends_on` | Explicit dependency between resources |

## Files in This Project
```
project_3.1_terraform_basics/
├── README.md
├── steps.md
├── 01_hello_terraform/     ← first resource ever
├── 02_variables/           ← parameterize configs
├── 03_outputs/             ← export values
├── 04_data_sources/        ← read existing resources
├── 05_locals/              ← computed values
├── docs/
│   └── architecture.md
└── cost_estimate.md
```

## How to Run
```bash
cd 01_hello_terraform
terraform init
terraform plan
terraform apply
terraform destroy
```

## Lessons Learned
- `terraform init` downloads the provider plugin — run it once per directory
- `terraform plan` never changes anything — always run it before apply
- State file is the source of truth — never edit it manually
- `terraform destroy` removes everything Terraform created — use carefully
- Variables without defaults will prompt you at runtime
- Use `terraform fmt` to auto-format code and `terraform validate` to check syntax
