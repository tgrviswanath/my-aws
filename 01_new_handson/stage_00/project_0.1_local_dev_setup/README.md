# Project 0.1 — Local Cloud Development Setup

## What This Does
Emulates AWS services locally using LocalStack. Allows safe development and testing without AWS costs or risk.

## Tools Used
| Tool | Purpose |
|------|---------|
| Docker + Docker Compose | Run LocalStack and containers |
| LocalStack | Emulate AWS services locally |
| AWS CLI | Interact with LocalStack via terminal |
| Terraform | Infrastructure as code (configured for local) |
| Git | Version control |
| VS Code | Editor |

## Services Emulated Locally
- S3
- Lambda
- API Gateway
- DynamoDB
- IAM
- CloudWatch Logs

## How to Run
```bash
docker compose up -d
curl http://localhost:4566/_localstack/health
```

## Folder Structure
```
project_0.1_local_dev_setup/
├── README.md
├── steps.md
├── docker-compose.yml
├── terraform/
│   └── main.tf
├── docs/
│   └── architecture.md
└── cost_estimate.md
```

## Lessons Learned
- LocalStack port 4566 handles all AWS service endpoints
- Always use `--endpoint-url=http://localhost:4566` with AWS CLI for local testing
- Use a separate AWS CLI profile (`localstack`) to avoid mixing with real credentials

## Code

### `code/localstack_demo.py` — Run AWS services locally

```bash
# Install dependencies
pip install boto3

# Start LocalStack first
docker compose up -d

# Wait for LocalStack to be ready
curl http://localhost:4566/_localstack/health

# Run the demo (creates DynamoDB table, Lambda, API Gateway — all locally)
python code/localstack_demo.py
```

What it does:
- Creates a DynamoDB table `local-items` and inserts 3 items
- Creates a Lambda function from an inline ZIP and invokes it
- Creates an API Gateway REST API wired to the Lambda
- Prints the local invoke URL: `http://localhost:4566/restapis/<id>/dev/_user_request_/hello`
