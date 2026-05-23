# Stage 04 — Serverless & Event-Driven Architecture

6 hands-on projects covering Lambda, API Gateway, DynamoDB, Cognito, SNS, SQS, and Step Functions.

---

## Projects

| # | Project | Key Services | Difficulty |
|---|---------|-------------|-----------|
| 4.1 | Serverless REST API | API Gateway, Lambda, DynamoDB | ⭐⭐ |
| 4.2 | API Authentication | Cognito, JWT Authorizer, Lambda | ⭐⭐⭐ |
| 4.3 | URL Shortener | API Gateway, Lambda, DynamoDB TTL | ⭐⭐ |
| 4.4 | Event-Driven Image Processing | S3 Events, Lambda, Pillow, DynamoDB | ⭐⭐⭐ |
| 4.5 | SNS/SQS Microservices | SNS, SQS, DLQ, Lambda fan-out | ⭐⭐⭐ |
| 4.6 | Step Functions Workflow | Step Functions, Lambda, parallel states | ⭐⭐⭐⭐ |

---

## Recommended Order

Start with 4.1 (foundation), then 4.2 (adds auth to 4.1), then 4.3–4.6 in any order.

---

## Structure

Each project folder contains:

| File | Purpose |
|------|---------|
| `README.md` | What it does, architecture, lessons learned |
| `steps.md` | Step-by-step deploy and test instructions |
| `verify.md` | Console + CLI verification checklist with expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Infrastructure as Code |
| `src/` | Lambda function source code |
| `docs/architecture.md` | Architecture diagrams |

---

## Verify Coverage

| Project | verify.md Highlights |
|---------|---------------------|
| 4.1 | CRUD endpoint tests, DynamoDB item check, Lambda logs, error cases |
| 4.2 | Cognito user pool, JWT decode, protected endpoint 401/200, RBAC |
| 4.3 | Redirect test, click counter, TTL expiry, stats endpoint |
| 4.4 | S3 trigger, thumbnail/medium output, DynamoDB metadata, recursive trigger guard |
| 4.5 | SNS fan-out to all 3 queues, DLQ test, Lambda consumer logs |
| 4.6 | Execution graph, parallel branch success, Catch/Retry test, DynamoDB result |

---

## Estimated Cost (all 6 projects, ~2–3 hours each)

All services are within AWS Free Tier for typical lab usage:
- Lambda: 1M free requests/month
- API Gateway: 1M HTTP API calls/month (12 months)
- DynamoDB: 25 GB + 25 WCU/RCU free forever
- SNS/SQS: 1M requests/month free
- Step Functions: 4,000 state transitions/month free
- Cognito: 50,000 MAU free

**Estimated cost: $0–$1** for lab-scale usage.
