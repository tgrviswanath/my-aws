# Project 4.2 — API Gateway Authorization

**Stage:** 04 | **Level:** Intermediate | **Est. Time:** 60 min | **Cost:** ~$0.20/month

This project adds JWT-based authorization to the Serverless REST API built in Project 4.1.
A second Lambda function acts as a REQUEST-type Lambda Authorizer attached to all protected routes.
When a client sends a request with a `Bearer <token>` Authorization header, API Gateway invokes the
authorizer Lambda before routing to the backend. The authorizer decodes the JWT using the shared secret,
validates the signature and expiry (`exp` claim), and returns an IAM policy with `Effect: Allow` or
`Effect: Deny`. API Gateway caches the returned policy for 300 seconds, keyed on the request's
Authorization header, so repeated calls with the same valid token skip the authorizer Lambda entirely
and reduce latency and cost.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| API Gateway HTTP API | Routes requests, enforces authorizer on protected routes | $1.00/1M calls |
| Lambda Authorizer (Python 3.12) | Validates JWT Bearer token, returns IAM Allow/Deny policy | $0.20/1M requests |
| Lambda Backend (from 4.1) | Handles CRUD operations after authorization passes | $0.20/1M requests |
| IAM | Policy evaluation — Allow grants access to specific route ARN | Free |
| CloudWatch Logs | Authorizer and backend function logs for debugging 401/403 flows | $0.50/GB ingested |

## Input / Output

### Input

| Parameter | Type | Where | Example |
|---|---|---|---|
| Running API from Project 4.1 | Deployed HTTP API | AWS account | API ID `abc123` |
| JWT secret key | String | Lambda env var `JWT_SECRET` | `my-super-secret-key` |
| Valid JWT Bearer token | String | HTTP `Authorization` header | `Bearer eyJhbGciOiJIUzI1NiJ9...` |
| Expired JWT token | String | HTTP `Authorization` header | `Bearer eyJhbGciOiJIUzI1NiJ9...` (exp in past) |
| Missing Authorization header | — | No header sent | (omit header entirely) |

### Output

| Scenario | HTTP Status | Response |
|---|---|---|
| Valid token, route allowed | 200 | Normal CRUD response from backend Lambda |
| Expired token | 401 | `{"message": "Unauthorized"}` |
| Invalid signature | 403 | `{"message": "Forbidden"}` |
| Missing Authorization header | 401 | `{"message": "Unauthorized"}` |
| Cached policy hit (same valid token) | 200 | Response served without invoking authorizer Lambda |

## Architecture

```
Client (curl / Postman)
        |  Authorization: Bearer <jwt>
        v
+-----------------------------+
|   API Gateway HTTP API      |
|   Authorizer attached to    |
|   POST /items               |
|   GET  /items/{id}          |
|   DELETE /items/{id}        |
+-----------------------------+
        |  Invoke authorizer first
        v
+-----------------------------+
|  Authorizer Lambda          |
|  Python 3.12                |
|  - Extract Bearer token     |
|  - Decode JWT (HS256)       |
|  - Check exp claim          |
|  - Return IAM policy        |
+-----------------------------+
        |  Effect: Allow / Deny
        v
+-----------------------------+       +--------------------+
|  API Gateway Policy Cache   |       |  403 Forbidden     |
|  TTL: 300s (per token)      |  Deny |  or 401 Unauth     |
+-----------------------------+ ----> +--------------------+
        |  Allow
        v
+-----------------------------+
|  Backend Lambda (4.1)       |
|  DynamoDB CRUD              |
+-----------------------------+
```

## Quick Start

```cmd
REM 1. Create the authorizer Lambda function
powershell Compress-Archive -Path authorizer.py -DestinationPath authorizer.zip -Force
aws lambda create-function ^
  --function-name api-jwt-authorizer ^
  --runtime python3.12 ^
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-dynamo-role ^
  --handler authorizer.lambda_handler ^
  --zip-file fileb://authorizer.zip ^
  --environment Variables={JWT_SECRET=my-super-secret-key} ^
  --region us-east-1

REM 2. Create a Lambda Authorizer on the existing HTTP API
aws apigatewayv2 create-authorizer ^
  --api-id YOUR_API_ID ^
  --authorizer-type REQUEST ^
  --authorizer-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:api-jwt-authorizer/invocations ^
  --identity-sources "$request.header.Authorization" ^
  --authorizer-result-ttl-in-seconds 300 ^
  --name jwt-authorizer ^
  --region us-east-1

REM 3. Grant API Gateway permission to invoke the authorizer Lambda
aws lambda add-permission ^
  --function-name api-jwt-authorizer ^
  --statement-id apigateway-auth-invoke ^
  --action lambda:InvokeFunction ^
  --principal apigateway.amazonaws.com ^
  --source-arn "arn:aws:execute-api:us-east-1:YOUR_ACCOUNT_ID:YOUR_API_ID/*" ^
  --region us-east-1

REM 4. Attach the authorizer to a route (e.g., GET /items/{id})
aws apigatewayv2 update-route ^
  --api-id YOUR_API_ID ^
  --route-id YOUR_ROUTE_ID ^
  --authorization-type CUSTOM ^
  --authorizer-id YOUR_AUTHORIZER_ID ^
  --region us-east-1

REM 5. Test with a valid token
curl -X GET https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/items/item-001 ^
  -H "Authorization: Bearer YOUR_VALID_JWT"

REM 6. Test with no token (expect 401)
curl -X GET https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/items/item-001
```

## Data Flow

1. Client sends HTTP request with `Authorization: Bearer <jwt>` header to API Gateway.
2. API Gateway detects a CUSTOM authorizer is attached to the matched route.
3. API Gateway invokes the authorizer Lambda, passing the full request context including headers, path, and query parameters.
4. Authorizer Lambda extracts the token from `event["headers"]["authorization"]`.
5. Lambda decodes the JWT using `PyJWT` and the `JWT_SECRET` env var; validates the `exp` (expiry) claim.
6. If valid: authorizer returns an IAM policy document with `Effect: Allow` and the backend Lambda ARN as the resource, plus a `principalId`.
7. If invalid or expired: authorizer returns `Effect: Deny` or raises an `Unauthorized` exception.
8. API Gateway evaluates the returned policy. On Allow, it forwards the original request to the backend Lambda.
9. The policy is cached for 300 seconds keyed on the Authorization header value — the next request with the same token skips step 3–7.
10. Backend Lambda executes the CRUD operation and returns the response through API Gateway to the client.

## Project Files

| File | Description |
|---|---|
| `authorizer.py` | Lambda Authorizer — extracts JWT, validates signature and expiry, returns IAM policy |
| `authorizer.zip` | Deployment package for the authorizer Lambda |
| `generate_tokens.py` | Helper script to generate valid and expired JWTs using the shared secret for testing |
| `README.md` | This file |

## Lessons Learned

- Lambda Authorizer vs Cognito: the authorizer is fully custom logic (any token format, any rule); Cognito manages user registration, MFA, and token refresh — use Cognito for full user management, authorizer when you own token issuance.
- Authorizer result cache (TTL 0–3600s) skips Lambda invocation for repeated requests with the same token — at 300s TTL, 10 requests/minute triggers the authorizer once per 5 minutes, cutting invocation costs by 98%.
- REQUEST-type authorizer receives full request context (headers, query params, path, stage variables); TOKEN-type receives only the token — use REQUEST when authorization depends on more than the token alone.
- The IAM policy `Resource` must be the exact route ARN (`arn:aws:execute-api:region:account:api-id/stage/METHOD/path`) — a wildcard `*` grants access to every route on the API, which is usually too broad.
- HTTP 401 = credentials absent or malformed (no header, bad JWT structure); HTTP 403 = credentials parsed but access denied — the authorizer controls which is returned via exception type or Deny effect.
- The `principalId` in the returned policy is accessible as `$context.authorizer.principalId` in access logs — use it to correlate API requests to individual users in audit trails.
