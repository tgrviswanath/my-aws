# Architecture — Project 3.4 Terraform Remote State

## Remote State Flow

```
Developer 1                    Developer 2
    │                               │
    │ terraform apply               │ terraform apply
    │                               │
    ▼                               ▼
┌──────────────────────────────────────────────────────┐
│                    AWS                                │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              DynamoDB: handson-terraform-locks   │ │
│  │                                                   │ │
│  │  Dev1 acquires lock → LockID = "stage-03/..."    │ │
│  │  Dev2 tries to lock → ConditionalCheckFailed     │ │
│  │  Dev2 waits or errors                            │ │
│  │  Dev1 finishes → releases lock                   │ │
│  │  Dev2 can now acquire lock                       │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │         S3: handson-terraform-state-ACCOUNTID    │ │
│  │                                                   │ │
│  │  stage-03/project-3.4/terraform.tfstate          │ │
│  │  stage-03/project-3.2/terraform.tfstate          │ │
│  │  stage-03/project-3.3/dev/terraform.tfstate      │ │
│  │  stage-03/project-3.3/prod/terraform.tfstate     │ │
│  │                                                   │ │
│  │  Versioning: ON  (rollback to previous state)    │ │
│  │  Encryption: AES256                              │ │
│  │  Public access: BLOCKED                          │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## State Key Strategy

```
S3 bucket: handson-terraform-state-ACCOUNTID
├── stage-00/billing/terraform.tfstate
├── stage-01/static-website/terraform.tfstate
├── stage-02/vpc/terraform.tfstate
├── stage-03/
│   ├── project-3.2/terraform.tfstate
│   ├── project-3.3/dev/terraform.tfstate
│   ├── project-3.3/qa/terraform.tfstate
│   └── project-3.3/prod/terraform.tfstate
└── ...
```

## Remote State Data Source

```
Config A (VPC)          Config B (App)
  outputs:                reads:
  vpc_id ──────────────► data.terraform_remote_state.vpc.outputs.vpc_id
  subnet_ids ──────────► data.terraform_remote_state.vpc.outputs.subnet_ids
```
