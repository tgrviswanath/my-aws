# Steps — Project 11.20 Network Automation (IaC)

## Phase 1 — Terraform Modules

### 1.1 Set Up Remote State Backend
```bash
# Create S3 bucket for state
aws s3 mb s3://tf-state-11-20-$(aws sts get-caller-identity --query Account --output text)
aws s3api put-bucket-versioning \
  --bucket tf-state-11-20-<ACCOUNT_ID> \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name tf-lock-11-20 \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 1.2 Deploy with Terraform Modules
```bash
cd terraform
terraform init    # downloads modules, configures backend
terraform plan    # preview changes
terraform apply   # deploy
terraform output  # show outputs
```

### 1.3 Test Module Reusability
```bash
# Deploy a second environment (staging) using the same module
cd terraform
terraform workspace new staging
terraform apply -var="environment=staging" -var="vpc_cidr=10.1.0.0/16"
terraform workspace list
```

---

## Phase 2 — CloudFormation

### 2.1 Deploy VPC Stack
```bash
cd cfn

# Validate template
aws cloudformation validate-template --template-body file://vpc-stack.yaml

# Deploy
aws cloudformation deploy \
  --template-file vpc-stack.yaml \
  --stack-name vpc-11-20 \
  --parameter-overrides \
    Environment=dev \
    VpcCidr=10.0.0.0/16 \
  --capabilities CAPABILITY_IAM

# Check status
aws cloudformation describe-stacks --stack-name vpc-11-20 \
  --query "Stacks[0].{Status:StackStatus,Outputs:Outputs}"
```

### 2.2 Test Drift Detection
```bash
# Manually change something in the console (e.g., add a tag to the VPC)
# Then detect drift:
aws cloudformation detect-stack-drift --stack-name vpc-11-20
DRIFT_ID=$(aws cloudformation detect-stack-drift --stack-name vpc-11-20 \
  --query "StackDriftDetectionId" --output text)
sleep 30
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DRIFT_ID
```

---

## Phase 3 — AWS CDK

### 3.1 Set Up CDK
```bash
cd cdk
pip install -r requirements.txt
cdk bootstrap   # one-time setup per account/region

# Preview
cdk diff

# Deploy
cdk deploy

# Show synthesized CloudFormation
cdk synth
```

---

## Phase 4 — Verify

```bash
# 1. Terraform — verify state is in S3
aws s3 ls s3://tf-state-11-20-<ACCOUNT_ID>/

# 2. Terraform — verify outputs
cd terraform && terraform output

# 3. Terraform — verify workspace isolation
terraform workspace list
# Should show: default, staging

# 4. CloudFormation — verify stack is complete
aws cloudformation describe-stacks --stack-name vpc-11-20 \
  --query "Stacks[0].StackStatus"
# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# 5. CloudFormation — list stack resources
aws cloudformation list-stack-resources --stack-name vpc-11-20 \
  --query "StackResourceSummaries[*].{Type:ResourceType,ID:PhysicalResourceId,Status:ResourceStatus}"

# 6. CDK — verify synthesized template
cdk synth | grep -c "AWS::"
# Shows number of AWS resources in the CDK stack

# 7. Verify all three approaches created equivalent infrastructure
python code/iac_checker.py \
  --tf-vpc-id $(cd terraform && terraform output -raw vpc_id) \
  --cfn-stack vpc-11-20
```

---

## Phase 5 — Test

```bash
# Test 1: Terraform module reuse — deploy staging environment
cd terraform
terraform workspace new staging
terraform apply \
  -var="environment=staging" \
  -var="vpc_cidr=10.1.0.0/16" \
  -var="region=us-east-1"
# Expected: new VPC with 10.1.0.0/16 created

# Verify staging VPC exists
terraform output vpc_id
aws ec2 describe-vpcs --vpc-ids $(terraform output -raw vpc_id) \
  --query "Vpcs[0].{CIDR:CidrBlock,Tags:Tags}"

# Test 2: CloudFormation drift detection
# Manually add a tag to the VPC via console
# Then run drift detection:
aws cloudformation detect-stack-drift --stack-name vpc-11-20
sleep 30
aws cloudformation describe-stack-resource-drifts \
  --stack-name vpc-11-20 \
  --stack-resource-drift-status-filters MODIFIED DELETED
# Should show the manually added tag as a drift

# Test 3: Terraform plan detects drift
cd terraform && terraform workspace select default
terraform plan
# Should show the manual tag change as a diff

# Test 4: CDK diff after manual change
cd cdk && cdk diff
# Should show the manual change

# Test 5: Destroy staging, keep default
cd terraform
terraform workspace select staging
terraform destroy -var="environment=staging" -var="vpc_cidr=10.1.0.0/16"
terraform workspace select default
terraform workspace delete staging

# Test 6: Verify remote state locking
# Open two terminals, run terraform apply in both simultaneously
# Second one should get: "Error acquiring the state lock"

# Run automated checker
python code/iac_checker.py --tf-vpc-id <VPC_ID> --cfn-stack vpc-11-20
```

### Verification Checklist
- [ ] S3 bucket created for Terraform remote state
- [ ] DynamoDB table created for state locking
- [ ] Terraform init uses remote backend (S3)
- [ ] `terraform apply` creates full three-tier VPC
- [ ] Terraform workspace `staging` creates separate VPC with different CIDR
- [ ] CloudFormation stack status = CREATE_COMPLETE
- [ ] CloudFormation drift detection identifies manual changes
- [ ] CDK synthesizes valid CloudFormation template
- [ ] CDK deploy creates equivalent VPC infrastructure
- [ ] State locking prevents concurrent Terraform runs
- [ ] All three IaC tools produce equivalent infrastructure

---

## Teardown
```bash
# Terraform
cd terraform
terraform workspace select staging && terraform destroy
terraform workspace select default && terraform destroy

# CloudFormation
aws cloudformation delete-stack --stack-name vpc-11-20

# CDK
cd cdk && cdk destroy

# Cleanup backend
aws s3 rm s3://tf-state-11-20-<ACCOUNT_ID> --recursive
aws s3 rb s3://tf-state-11-20-<ACCOUNT_ID>
aws dynamodb delete-table --table-name tf-lock-11-20
```
