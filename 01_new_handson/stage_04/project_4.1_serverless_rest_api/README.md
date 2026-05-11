# Project 4.1 — Serverless REST API

## What This Does
Builds a fully serverless REST API using API Gateway + Lambda + DynamoDB. No servers to manage, scales automatically, pay only for what you use.

## Architecture
```
Client → API Gateway → Lambda → DynamoDB
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /items | List all items |
| GET | /items/{id} | Get item by ID |
| POST | /items | Create item |
| PUT | /items/{id} | Update item |
| DELETE | /items/{id} | Delete item |

## Services Used
| Service | Role |
|---------|------|
| API Gateway (HTTP API) | Route HTTP requests to Lambda |
| Lambda | Business logic — stateless functions |
| DynamoDB | NoSQL database — fast key-value store |
| IAM | Lambda execution role with DynamoDB access |
| CloudWatch Logs | Lambda function logs |

## How to Deploy
```bash
cd terraform
terraform init
terraform apply

# Get API URL
terraform output api_url
```

## Lessons Learned
- HTTP API (v2) is cheaper and faster than REST API (v1) — use HTTP API for most cases
- Lambda cold starts: first invocation after idle period is slower (~100–500ms)
- DynamoDB `PAY_PER_REQUEST` billing is best for unpredictable traffic
- Always return proper HTTP status codes from Lambda (200, 201, 400, 404, 500)
- Use Lambda environment variables for config — never hardcode table names or regions
- Lambda timeout default is 3 seconds — increase for DB operations
