# Verification & Validation — Project 11.20 Network Automation (IaC)

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Terraform State Bucket | S3 → Buckets | `tf-state-11-20-<account-id>`, versioning enabled |
| DynamoDB Lock Table | DynamoDB → Tables | `tf-lock-11-20`, exists |
| VPC (Terraform) | VPC → Your VPCs | VPC created by Terraform with correct tags |
| CFN Stack | CloudFormation → Stacks | `vpc-11-20`, Status = **CREATE_COMPLETE** |
| CDK Stack | CloudFormation → Stacks | CDK-generated stack, Status = **CREATE_COMPLETE** |
| Terraform Workspaces | — | `default` and `staging` workspaces with separate VPCs |

📸 Screenshot: S3 bucket showing `terraform.tfstate` file with versioning  
📸 Screenshot: CloudFormation stack `vpc-11-20` showing CREATE_COMPLETE  
📸 Screenshot: Drift detection result showing manual change detected

---

## 2. AWS CLI Verification

```bash
# 2.1 Terraform remote state in S3
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 ls s3://tf-state-11-20-$ACCOUNT_ID/
# Expected: terraform.tfstate file present

# 2.2 S3 versioning enabled
aws s3api get-bucket-versioning --bucket tf-state-11-20-$ACCOUNT_ID
# Expected: Status=Enabled

# 2.3 DynamoDB lock table exists
aws dynamodb describe-table --table-name tf-lock-11-20 \
  --query "Table.{Name:TableName,Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}"
# Expected: Status=ACTIVE, BillingMode=PAY_PER_REQUEST

# 2.4 CloudFormation stack complete
aws cloudformation describe-stacks --stack-name vpc-11-20 \
  --query "Stacks[0].{Status:StackStatus,Outputs:Outputs}"
# Expected: Status=CREATE_COMPLETE or UPDATE_COMPLETE

# 2.5 CloudFormation stack resources
aws cloudformation list-stack-resources --stack-name vpc-11-20 \
  --query "StackResourceSummaries[*].{Type:ResourceType,ID:PhysicalResourceId,Status:ResourceStatus}"
# Expected: all resources = CREATE_COMPLETE

# 2.6 Drift detection
aws cloudformation detect-stack-drift --stack-name vpc-11-20
DRIFT_ID=$(aws cloudformation detect-stack-drift --stack-name vpc-11-20 \
  --query "StackDriftDetectionId" --output text)
sleep 30
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DRIFT_ID \
  --query "{Status:DetectionStatus,DriftStatus:StackDriftStatus}"
# Expected: DetectionStatus=DETECTION_COMPLETE
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 Confirm remote backend is active
terraform state list
# If this returns results without error, remote state is working

# 3.2 Verify workspace isolation
terraform workspace list
# Expected: * default, staging

terraform workspace select staging
terraform state list
# Should show staging VPC resources (separate from default)

terraform workspace select default

# 3.3 Confirm outputs
terraform output
# Expected: vpc_id, subnet_ids, environment=dev

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.

# 3.5 State locking test
# Open two terminals, run terraform plan simultaneously
# Second terminal should show: Error acquiring the state lock
```

---

## 4. Health Check — IaC Equivalence

```bash
# Verify all three IaC tools created equivalent infrastructure
TF_VPC=$(cd terraform && terraform output -raw vpc_id)
CFN_VPC=$(aws cloudformation describe-stack-resource \
  --stack-name vpc-11-20 --logical-resource-id VPC \
  --query "StackResourceDetail.PhysicalResourceId" --output text)

# Both VPCs should have same CIDR and structure
aws ec2 describe-vpcs --vpc-ids $TF_VPC $CFN_VPC \
  --query "Vpcs[*].{ID:VpcId,CIDR:CidrBlock,DNS:EnableDnsHostnames}"

# CDK stack VPC
CDK_VPC=$(aws cloudformation describe-stack-resource \
  --stack-name <CDK_STACK_NAME> --logical-resource-id VPC \
  --query "StackResourceDetail.PhysicalResourceId" --output text)
```

---

## 5. Expected Successful Outputs

**Terraform remote state:**
```
2024-01-01 12:00:00    4521 terraform.tfstate
```

**CloudFormation stack:**
```json
{ "Status": "CREATE_COMPLETE", "Outputs": [{ "OutputKey": "VpcId", "OutputValue": "vpc-0abc123" }] }
```

**Workspace isolation:**
```
  default   → VPC CIDR: 10.0.0.0/16
  staging   → VPC CIDR: 10.1.0.0/16  (separate state, separate resources)
```

**State locking:**
```
Error: Error acquiring the state lock
Lock Info:
  ID:        xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Path:      tf-state-11-20-xxx/terraform.tfstate
  Operation: OperationTypePlan
```

---

## 6. Verification Checklist

- [ ] S3 bucket created for Terraform remote state, versioning enabled
- [ ] DynamoDB table created for state locking
- [ ] `terraform init` uses remote backend (S3)
- [ ] `terraform apply` creates full VPC infrastructure
- [ ] Terraform workspace `staging` creates separate VPC with different CIDR
- [ ] CloudFormation stack status = CREATE_COMPLETE
- [ ] CloudFormation drift detection identifies manual changes
- [ ] CDK synthesizes valid CloudFormation template
- [ ] CDK deploy creates equivalent VPC infrastructure
- [ ] State locking prevents concurrent Terraform runs
- [ ] All three IaC tools produce equivalent infrastructure
- [ ] `terraform plan` shows no changes (default workspace)
