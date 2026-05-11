# Architecture — Project 3.1 Terraform Basics

## Terraform Workflow

```
Write .tf files
      │
      ▼
terraform init
  └── Downloads provider plugins
  └── Creates .terraform/ directory
  └── Initializes backend (local by default)
      │
      ▼
terraform plan
  └── Reads current state (terraform.tfstate)
  └── Calls AWS API to check real state
  └── Computes diff: what needs to create/update/destroy
  └── Shows plan — NO changes made yet
      │
      ▼
terraform apply
  └── Shows plan again
  └── Asks for confirmation (yes/no)
  └── Calls AWS API to make changes
  └── Updates terraform.tfstate
      │
      ▼
terraform destroy
  └── Removes all resources in state
  └── Clears terraform.tfstate
```

## State File Concept

```
terraform.tfstate (JSON)
{
  "resources": [
    {
      "type": "aws_s3_bucket",
      "name": "hello",
      "instances": [{
        "attributes": {
          "bucket": "hello-terraform-abc123",
          "arn": "arn:aws:s3:::hello-terraform-abc123",
          ...
        }
      }]
    }
  ]
}

Terraform uses this to:
- Know what it manages
- Detect drift (real AWS vs state)
- Plan changes efficiently
```

## Variable Precedence (highest to lowest)

```
1. -var="key=value" flag          ← highest priority
2. -var-file="file.tfvars" flag
3. terraform.tfvars (auto-loaded)
4. *.auto.tfvars (auto-loaded)
5. TF_VAR_name environment variable
6. Default value in variable block  ← lowest priority
```

## File Structure Convention

```
project/
├── main.tf        ← resources
├── variables.tf   ← variable declarations
├── outputs.tf     ← output declarations
├── locals.tf      ← local values
├── providers.tf   ← provider config
├── versions.tf    ← required_providers block
├── terraform.tfvars  ← variable values (gitignored if sensitive)
└── dev.tfvars     ← environment-specific values
```
