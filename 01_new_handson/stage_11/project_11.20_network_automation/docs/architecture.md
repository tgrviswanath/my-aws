# Architecture Notes — Project 11.20

## Three IaC Approaches Compared

| | Terraform | CloudFormation | CDK |
|--|-----------|---------------|-----|
| Language | HCL | YAML/JSON | Python/TS/Java |
| State | Remote (S3) | Managed by AWS | Managed by AWS (via CFN) |
| Multi-cloud | Yes | AWS only | AWS only |
| Abstraction | Medium | Low | High (L2/L3 constructs) |
| Drift detection | `terraform plan` | Built-in | Via CFN |
| Modules | Yes (registry) | Nested stacks | Constructs |
| Best for | Multi-cloud, teams | AWS-native, compliance | Developers, complex logic |

## Terraform Workspace Pattern
```
terraform workspace new staging
terraform apply -var="environment=staging" -var="vpc_cidr=10.1.0.0/16"
# Creates completely separate state for staging
# Same code, different variables = different environments
```

## Remote State Architecture
```
Developer A                    Developer B
    ↓ terraform apply              ↓ terraform apply
    ↓ acquire lock                 ↓ wait for lock
S3 (state file)  ←→  DynamoDB (lock table)
    ↑ state stored                 ↑ lock released → B proceeds
```

## CDK Synthesis Flow
```
CDK Python code
    ↓ cdk synth
CloudFormation template (JSON)
    ↓ cdk deploy
CloudFormation stack
    ↓ creates
AWS Resources (VPC, subnets, etc.)
```
