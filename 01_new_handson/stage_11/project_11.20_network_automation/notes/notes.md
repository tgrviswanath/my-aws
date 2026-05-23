# Notes — Project 11.20

## Terraform Remote Backend Setup (one-time)
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="tf-state-11-20-$ACCOUNT_ID"

# Create bucket with versioning
aws s3 mb s3://$BUCKET --region us-east-1
aws s3api put-bucket-versioning \
  --bucket $BUCKET \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption \
  --bucket $BUCKET \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB lock table
aws dynamodb create-table \
  --table-name tf-lock-11-20 \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Update terraform/main.tf backend block with bucket name, then:
terraform init -reconfigure
```

## Terraform Workspace Commands
```bash
terraform workspace new staging      # create new workspace
terraform workspace select staging   # switch to staging
terraform workspace list             # list all workspaces
terraform workspace show             # current workspace
terraform workspace delete staging   # delete (must be empty)
```

## CDK Useful Commands
```bash
cdk ls          # list all stacks
cdk synth       # synthesize CloudFormation template
cdk diff        # show what will change
cdk deploy      # deploy stack
cdk destroy     # destroy stack
cdk doctor      # check CDK setup
```

## CloudFormation Drift Detection
```bash
# Start drift detection
DRIFT_ID=$(aws cloudformation detect-stack-drift \
  --stack-name vpc-11-20 \
  --query "StackDriftDetectionId" --output text)

# Check status (takes 1-2 minutes)
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DRIFT_ID

# List drifted resources
aws cloudformation describe-stack-resource-drifts \
  --stack-name vpc-11-20 \
  --stack-resource-drift-status-filters MODIFIED DELETED
```

## When to Use Each Tool
- **Terraform**: multi-cloud, existing team expertise, complex module ecosystem
- **CloudFormation**: AWS-only, compliance requirements, native drift detection
- **CDK**: Python/TypeScript developers, complex conditional logic, reusable constructs
