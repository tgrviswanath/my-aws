# Steps — Project 0.1 Local Cloud Development Setup

## Phase 1 — Install Tools

### 1.1 Install Docker Desktop
Download from https://www.docker.com/products/docker-desktop

```bash
docker --version
docker compose version
```

### 1.2 Install AWS CLI v2
Download from https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

```bash
aws --version
```

### 1.3 Install Terraform
Download from https://developer.hashicorp.com/terraform/downloads

```bash
terraform --version
```

### 1.4 Install Git
```bash
git --version
```

---

## Phase 2 — Configure AWS CLI for LocalStack

```bash
aws configure --profile localstack
# AWS Access Key ID:     test
# AWS Secret Access Key: test
# Default region:        us-east-1
# Default output format: json
```

---

## Phase 3 — Start LocalStack

```bash
# From this project folder
docker compose up -d

# Verify all services are healthy
curl http://localhost:4566/_localstack/health
```

Expected output:
```json
{
  "services": {
    "s3": "running",
    "lambda": "running",
    "dynamodb": "running",
    "apigateway": "running"
  }
}
```

---

## Phase 4 — Test S3 Locally

```bash
# Create bucket
aws --endpoint-url=http://localhost:4566 --profile localstack \
  s3 mb s3://test-bucket

# Upload file
echo "Hello LocalStack" > test.txt
aws --endpoint-url=http://localhost:4566 --profile localstack \
  s3 cp test.txt s3://test-bucket/

# List contents
aws --endpoint-url=http://localhost:4566 --profile localstack \
  s3 ls s3://test-bucket/
```

---

## Phase 5 — Deploy Lambda Locally

Create `hello_lambda.py`:
```python
import json

def handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello from LocalStack Lambda!"})
    }
```

```bash
# Package
zip hello_lambda.zip hello_lambda.py

# Deploy
aws --endpoint-url=http://localhost:4566 --profile localstack \
  lambda create-function \
  --function-name hello-lambda \
  --runtime python3.11 \
  --handler hello_lambda.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --zip-file fileb://hello_lambda.zip

# Invoke
aws --endpoint-url=http://localhost:4566 --profile localstack \
  lambda invoke \
  --function-name hello-lambda \
  output.json

cat output.json
```

---

## Phase 6 — Test DynamoDB Locally

```bash
# Create table
aws --endpoint-url=http://localhost:4566 --profile localstack \
  dynamodb create-table \
  --table-name Users \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Insert item
aws --endpoint-url=http://localhost:4566 --profile localstack \
  dynamodb put-item \
  --table-name Users \
  --item '{"userId": {"S": "user-001"}, "name": {"S": "Alice"}}'

# Scan table
aws --endpoint-url=http://localhost:4566 --profile localstack \
  dynamodb scan --table-name Users
```

---

## Phase 7 — Terraform with LocalStack

```bash
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```

---

## Screenshots to Take
- [ ] `docker compose up` output showing LocalStack healthy
- [ ] `curl localhost:4566/_localstack/health` response
- [ ] S3 bucket created and file uploaded
- [ ] Lambda invocation output
- [ ] DynamoDB table scan result
