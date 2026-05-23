# Verification & Validation — Project 0.1 Local Cloud Development Setup

---

## 1. Tool Version Verification

```bash
# Confirm all tools are installed and meet minimum versions
docker --version
# Expected: Docker version 24.x.x or later

docker compose version
# Expected: Docker Compose version v2.x.x

aws --version
# Expected: aws-cli/2.x.x

terraform --version
# Expected: Terraform v1.5.x or later

git --version
# Expected: git version 2.x.x
```

📸 Screenshot: Terminal showing all 4 version outputs together

---

## 2. LocalStack Health Verification

```bash
# Start LocalStack
docker compose up -d

# Confirm container is running
docker ps --filter "name=localstack"
# Expected: localstack container with STATUS = Up

# Health check — all services must show "running"
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

📸 Screenshot: `docker ps` showing LocalStack running + health check response

---

## 3. AWS CLI (LocalStack) Verification

```bash
# S3 — create bucket, upload, list
aws --endpoint-url=http://localhost:4566 --profile localstack \
  s3 mb s3://verify-bucket
# Expected: make_bucket: verify-bucket

aws --endpoint-url=http://localhost:4566 --profile localstack \
  s3 ls
# Expected: verify-bucket listed

# DynamoDB — create table, insert, scan
aws --endpoint-url=http://localhost:4566 --profile localstack \
  dynamodb list-tables
# Expected: { "TableNames": [...] }

# Lambda — list functions
aws --endpoint-url=http://localhost:4566 --profile localstack \
  lambda list-functions
# Expected: { "Functions": [...] }
```

📸 Screenshot: S3 bucket listed and Lambda invocation output

---

## 4. Terraform (LocalStack) Verification

```bash
cd terraform

# Init
terraform init
# Expected: Terraform has been successfully initialized!

# Plan — should show resources to create against LocalStack
terraform plan
# Expected: Plan: X to add, 0 to change, 0 to destroy

# Apply
terraform apply -auto-approve
# Expected: Apply complete! Resources: X added

# State list
terraform state list
# Expected: lists all created resources

# No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

📸 Screenshot: `terraform apply` success output

---

## 5. LocalStack Demo Script Verification

```bash
pip install boto3
python code/localstack_demo.py
```

Expected output:
```
✅ DynamoDB table created: local-items
✅ Items inserted: 3
✅ Lambda function created: hello-lambda
✅ Lambda invoked: {"statusCode": 200, "body": "Hello from LocalStack Lambda!"}
✅ API Gateway created
   Local URL: http://localhost:4566/restapis/<id>/dev/_user_request_/hello
```

📸 Screenshot: Full script output showing all ✅ checks

---

## 6. Verification Checklist

- [ ] Docker version ≥ 24.x
- [ ] Docker Compose version ≥ 2.x
- [ ] AWS CLI version ≥ 2.x
- [ ] Terraform version ≥ 1.5.x
- [ ] Git version ≥ 2.x
- [ ] LocalStack container running (`docker ps`)
- [ ] Health check returns all services = "running"
- [ ] `localstack` AWS CLI profile configured
- [ ] S3 bucket created and listed via LocalStack
- [ ] DynamoDB table created via LocalStack
- [ ] Lambda function invoked via LocalStack
- [ ] `terraform apply` succeeds against LocalStack
- [ ] `terraform plan` shows no changes after apply
- [ ] `localstack_demo.py` runs with all ✅
