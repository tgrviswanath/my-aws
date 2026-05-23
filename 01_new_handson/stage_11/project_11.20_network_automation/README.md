# Project 11.20 — Network Automation (Infrastructure as Code)

## What This Does
Automates the full three-tier VPC from Project 11.5 using Terraform modules,
CloudFormation, and AWS CDK. Demonstrates reusable network modules, parameterized
deployments, and automated drift detection.

## Architecture
```
Three approaches to the same infrastructure:

1. Terraform Modules
   └── module "vpc" → reusable VPC module
   └── module "subnets" → parameterized subnet creation
   └── module "routing" → route tables and associations

2. CloudFormation
   └── vpc-stack.yaml → nested stacks for each tier
   └── Parameters → environment-specific values

3. AWS CDK (Python)
   └── VpcStack → L2 constructs for VPC
   └── SubnetStack → custom subnet configuration
```

## Services Used
| Service | Role |
|---------|------|
| Terraform | Primary IaC tool with reusable modules |
| CloudFormation | AWS-native IaC with nested stacks |
| AWS CDK | Python-based IaC with high-level constructs |
| AWS Config | Detect configuration drift |
| EventBridge | Trigger automation on drift detection |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| Terraform modules | Reusable, parameterized infrastructure components |
| Remote state | Terraform state in S3 with DynamoDB locking |
| CloudFormation nested stacks | Modular CFN templates |
| CDK L2 constructs | High-level abstractions (e.g., `ec2.Vpc`) |
| Drift detection | Identify manual changes vs IaC-defined state |

## How to Deploy
```bash
# Terraform
cd terraform && terraform init && terraform apply

# CloudFormation
aws cloudformation deploy --template-file cfn/vpc-stack.yaml --stack-name vpc-11-20

# CDK
cd cdk && pip install -r requirements.txt && cdk deploy
```

## Lessons Learned
- Terraform modules make VPC creation reusable across environments
- Remote state prevents concurrent modifications and enables team collaboration
- CDK generates CloudFormation — good for Python developers
- Drift detection catches manual console changes that break IaC consistency

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Terraform modules, CloudFormation, CDK implementation + Phase 4 CLI verification checklist |
| `verify.md` | Console verification table, Terraform state checks, state locking test, drift detection, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Deployable Terraform configuration with remote state |
| `cfn/vpc-stack.yaml` | CloudFormation template |
| `cdk/app.py` | AWS CDK Python application |
| `code/iac_checker.py` | Python boto3 script — programmatic verification |
| `docs/architecture.md` | Traffic flow diagrams and architecture notes |
| `notes/notes.md` | Gotchas, troubleshooting tips, key commands |
