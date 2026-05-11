# Architecture — Project 4.2 API Authentication & Authorization

## Auth Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Auth Flow                                │
│                                                                   │
│  1. Register                                                      │
│     Client → POST /auth/register → Lambda → Cognito.SignUp       │
│                                                                   │
│  2. Login                                                         │
│     Client → POST /auth/login → Lambda → Cognito.InitiateAuth    │
│                                       ← JWT (access + id token)  │
│                                                                   │
│  3. Access Protected Resource                                     │
│     Client → GET /protected                                       │
│              Authorization: Bearer <id_token>                    │
│                    │                                              │
│                    ▼                                              │
│             API Gateway JWT Authorizer                            │
│             Validates token against Cognito JWKS endpoint        │
│                    │                                              │
│             ┌──────┴──────┐                                       │
│             │ Valid token │  Invalid token                        │
│             ▼             ▼                                       │
│         Lambda runs    401 Unauthorized                           │
│         (claims in event)                                         │
└─────────────────────────────────────────────────────────────────┘
```

## JWT Token Structure

```
Header.Payload.Signature

Payload claims (Cognito ID token):
{
  "sub": "user-uuid",
  "cognito:username": "testuser",
  "email": "test@example.com",
  "cognito:groups": ["admin"],
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXX",
  "aud": "client-id",
  "exp": 1234567890,
  "iat": 1234564290
}
```

## RBAC Model

```
Cognito Groups → JWT claims → Lambda checks → Allow/Deny

Group: admin  → cognito:groups: ["admin"]  → full access
Group: users  → cognito:groups: ["users"]  → read only
No group      → cognito:groups: []         → read only
```

## API Gateway JWT Authorizer vs Lambda Authorizer

| Feature | JWT Authorizer | Lambda Authorizer |
|---------|---------------|-------------------|
| Cost | Free | $0.20/million |
| Latency | ~0ms (built-in) | +Lambda cold start |
| Flexibility | Token validation only | Any custom logic |
| Use case | Cognito / standard JWT | Custom auth schemes |
| Recommendation | ✅ Use for Cognito | Only for custom auth |
