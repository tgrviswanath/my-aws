# Project 4.2 — API Authentication & Authorization

## What This Does
Adds authentication and authorization to the REST API from Project 4.1 using AWS Cognito (user pools + JWT tokens) and API keys for service-to-service auth.

## Auth Flows Covered

| Flow | Use Case |
|------|---------|
| Cognito User Pool + JWT | Human users logging in via username/password |
| Cognito JWT Authorizer | API Gateway validates JWT on every request |
| API Keys | Service-to-service or third-party API access |
| RBAC via Cognito Groups | Admin vs regular user permissions |

## Architecture
```
User → Login (Cognito) → JWT Token
     → API Request + JWT → API Gateway → JWT Authorizer → Lambda
                                              ↓ invalid
                                           401 Unauthorized
```

## Endpoints
| Method | Path | Auth Required | Role |
|--------|------|--------------|------|
| POST | /auth/register | No | - |
| POST | /auth/login | No | - |
| GET | /items | Yes (JWT) | any |
| POST | /items | Yes (JWT) | admin |
| DELETE | /items/{id} | Yes (JWT) | admin |

## How to Deploy
```bash
cd terraform
terraform init
terraform apply
terraform output
```

## Lessons Learned
- Never build your own auth — use Cognito or a managed identity provider
- JWT tokens expire — always handle 401 responses and refresh tokens
- Cognito User Pool = who can log in; Identity Pool = what AWS resources they can access
- API Gateway JWT Authorizer validates tokens without Lambda — faster and cheaper
- Store JWT in memory (not localStorage) to prevent XSS attacks
- RBAC: use Cognito Groups to assign roles, check group claims in Lambda

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Deploy, register, login, protected endpoint tests, JWT decode, RBAC |
| `verify.md` | Console verification, CLI auth flow tests, JWT decode check, Terraform state, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — Cognito User Pool, App Client, JWT Authorizer, Lambda |
| `src/auth_handler.py` | JWT authentication Lambda (register/login) |
| `src/protected_handler.py` | Protected endpoint Lambda (validates group claims) |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `src/auth_handler.py` — JWT authentication Lambda

```bash
pip install boto3 PyJWT

# Test login endpoint locally
export JWT_SECRET=my-secret-key
python -c "
from src.auth_handler import handler
import json

# Login
resp = handler({
    'requestContext': {'http': {'method': 'POST'}},
    'rawPath': '/login',
    'body': json.dumps({'username': 'admin', 'password': 'password123'})
}, None)
print(resp)
"
```

Flow: `POST /login` → returns JWT → include as `Authorization: Bearer <token>` on protected endpoints.
