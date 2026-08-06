# Project 4.2 — API Authentication & Authorization
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** API Authentication & Authorization with Cognito JWT + RBAC

**Business / Problem Statement:**
The REST API from Project 4.1 has no security — anyone who knows the URL can read, create, or delete data. Real applications need authentication (who are you?) and authorization (what are you allowed to do?). This project adds enterprise-grade auth using AWS Cognito: users register and log in to get JWT tokens, every API request is validated against the token, and admin-only routes are protected by role-based access control (RBAC) using Cognito Groups.

**Learning Objectives:**
- Understand JWT tokens: structure, signing, expiry, and claims
- Set up AWS Cognito User Pools for user registration and login
- Integrate API Gateway JWT Authorizer (validates tokens without Lambda)
- Implement RBAC using Cognito Groups and JWT group claims
- Test the full auth flow: register → login → get token → access protected API
- Understand why you should never build your own auth system

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| Cognito User Pool | Manages users, passwords, groups, token issuance |
| Cognito App Client | The "key" your app uses to call Cognito APIs |
| API Gateway JWT Authorizer | Validates JWT on every request — no Lambda needed |
| Lambda (auth_handler.py) | Handles register/login via Cognito SDK |
| Lambda (protected_handler.py) | Protected endpoints — reads group claims from JWT |
| IAM | Lambda execution roles |

**Service Interaction Flow:**
```
1. REGISTER:
   Client → POST /auth/register → Lambda → Cognito.SignUp() → User created

2. LOGIN:
   Client → POST /auth/login → Lambda → Cognito.InitiateAuth() → JWT tokens returned

3. ACCESS PROTECTED API:
   Client → GET /protected
            Authorization: Bearer <id_token>
                 │
                 ▼
          API Gateway JWT Authorizer
          Validates token against Cognito JWKS endpoint
                 │
            ┌────┴────┐
         Valid token  Invalid token
              │           │
         Lambda runs   401 Unauthorized
         (claims in event)
```

**High-Level Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Cognito User Pool                              │    │
│  │  ┌───────────┐  ┌────────────┐  ┌───────────────────┐  │    │
│  │  │  Users    │  │  Groups    │  │  JWT Token Issuer │  │    │
│  │  │  (signup) │  │  (admin)   │  │  (JWKS endpoint)  │  │    │
│  │  └───────────┘  └────────────┘  └───────────────────┘  │    │
│  └───────────────────────────┬──────────────────────────────┘   │
│                               │ JWT validation                   │
│  Client ──HTTPS──► API Gateway JWT Authorizer                    │
│                        │                                         │
│              ┌──────────┴──────────┐                            │
│              │ auth_handler Lambda  │ (register/login)           │
│              │ protected Lambda     │ (protected endpoints)      │
│              └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

**Best Practices Followed:**
- Never build your own auth — use Cognito (battle-tested, HIPAA/SOC2 compliant)
- JWT Authorizer at API Gateway layer (free, zero-latency vs Lambda authorizer)
- Tokens stored in memory, not in code
- RBAC via Cognito Groups (admin, users) — not hardcoded user lists
- Refresh token flow implemented for token renewal

---

## 3. Prerequisites

**Same as Project 4.1, plus:**

| Additional Requirement | Why |
|-----------------------|-----|
| Python `PyJWT` library | Decode JWT tokens locally for inspection |
| curl or Postman | Test auth endpoints manually |

**IAM Permissions Required (additional):**
```
cognito-idp:CreateUserPool, cognito-idp:CreateUserPoolClient
cognito-idp:AdminCreateUser, cognito-idp:CreateGroup
apigateway:CreateAuthorizer
```

**AWS Region:** `us-east-1` — Cognito is available in all major regions

**Environment Variable Setup:**
```bash
export AWS_DEFAULT_REGION=us-east-1
# These will be set after deployment:
# export USER_POOL_ID=us-east-1_XXXXXXXXX
# export CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# export API_URL=https://xxxxx.execute-api.us-east-1.amazonaws.com
```

---

## 4. Project Folder Structure

```
project_4.2_api_auth/
│
├── README.md               ← Project overview and auth flows
├── GUIDE.md                ← This file — complete implementation guide
├── steps.md                ← Quick deploy and test commands
├── verify.md               ← Verification checklist with JWT decode checks
├── cost_estimate.md        ← Cost breakdown (Cognito is free up to 50K MAU)
│
├── src/
│   ├── auth_handler.py     ← Register, login, refresh token via Cognito
│   └── protected_handler.py← Protected endpoints — reads JWT claims
│
├── docs/
│   └── architecture.md     ← Auth flow diagrams, JWT structure, RBAC model
│
└── terraform/
    └── main.tf             ← Cognito User Pool, App Client, API Gateway, Lambda
```

**File-by-File Explanation:**

| File | Purpose |
|------|---------|
| `src/auth_handler.py` | Calls Cognito APIs to register users and issue JWT tokens |
| `src/protected_handler.py` | Reads group claims injected by API Gateway from valid JWT |
| `terraform/main.tf` | Creates Cognito User Pool, App Client, JWT Authorizer, Lambdas |

---

## 5. Project Input & Output

**INPUT — Auth endpoints:**
```
POST /auth/register
{"username": "alice", "password": "Alice@1234", "email": "alice@example.com"}

POST /auth/login
{"username": "alice", "password": "Alice@1234"}

GET /protected
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

GET /protected  (no token)
→ No Authorization header
```

**OUTPUT:**
```
Register → 201
{"message": "User alice registered successfully"}

Login → 200
{
  "id_token":      "eyJ...",   ← Use this for API calls
  "access_token":  "eyJ...",   ← For Cognito operations
  "refresh_token": "eyJ...",   ← Renew without re-login
  "expires_in":    3600        ← Token valid for 1 hour
}

GET /protected (with valid token) → 200
{"message": "Hello, alice!", "user": {"username": "alice", "groups": ["admin"]}}

GET /protected (no token / invalid token) → 401
{"message": "Unauthorized"}

POST /items (admin route, non-admin user) → 403
{"error": "Forbidden", "message": "User alice does not have admin privileges"}
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create Cognito User Pool

**Prerequisites Check:**
- ✅ Required permissions: `cognito-idp:CreateUserPool`
- ✅ Services enabled: Amazon Cognito (check console)
- ✅ Region: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [Cognito Console](https://console.aws.amazon.com/cognito)
2. **Expected View:** Cognito dashboard with "Create user pool" button
3. **If Different:** Ensure you are in us-east-1

**Step 1.2: Make Selections**

**Decision Point 1:** Sign-in Options

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Username | Simple username-based login | ✅ Select this |
| Email | Login with email address | ✅ Also select this |
| Phone number | SMS-based login | ❌ Adds SMS cost |

Check both **Username** and **Email**, click **Next**

**📸 Screenshot:** Cognito "Step 1 Configure sign-in experience" with Username + Email checked

**Step 1.3: Configure Password Policy**

**Decision Point 2:** Password Requirements

| Option | Security | For This Project |
|--------|----------|-----------------|
| Cognito defaults | 8 chars, mixed case, numbers | ✅ Use defaults |
| Custom | Stricter requirements | ❌ Not needed for lab |

Leave defaults, click **Next**

**Step 1.4: Configure MFA**

| Setting | Value | Reason |
|---------|-------|--------|
| MFA | **No MFA** | Simplify for lab |
| User account recovery | Email | Simple recovery |

Click **Next**

**Step 1.5: Configure Sign-up Experience**

| Setting | Value |
|---------|-------|
| Self-registration | ✅ Allow |
| Required attributes | `email` |

Click **Next**

**Step 1.6: Configure Email Delivery**

| Setting | Value | Reason |
|---------|-------|--------|
| Email provider | Cognito (for development) | Free, no setup needed |
| FROM address | no-reply@verificationemail.com | Default |

Click **Next**

**Step 1.7: Integrate Your App**

| Field | Value | Explanation |
|-------|-------|-------------|
| User pool name | `handson-auth-user-pool` | Matches terraform: `${var.project}-auth-user-pool` |
| Hosted UI | **Don't use** | We build our own login UI |
| App type | **Public client** | SPA/mobile — no secret |
| App client name | `handson-auth-client` | Matches terraform: `${var.project}-auth-client` |
| Authentication flows | ✅ `ALLOW_USER_PASSWORD_AUTH` | Username/password flow |
| Authentication flows | ✅ `ALLOW_REFRESH_TOKEN_AUTH` | Refresh token support |

Click **Next** → Review → Click **Create user pool**

**Step 1.8: Validate Result**

**Expected Outcome:** User pool created with Pool ID like `us-east-1_XXXXXXXXX`

**📸 Screenshot:** Cognito user pool `handson-auth-user-pool` created showing Pool ID and App clients tab

**Note:** Copy the **User Pool ID** and **Client ID** — you need them for Lambda environment variables.

---

#### Step 2 — Create Admin Group in Cognito

**Step 2.1: Navigate**
1. Click on your user pool `handson-auth-user-pool`
2. Click **Groups** tab
3. Click **Create group**

**Step 2.2: Configure**

| Field | Value |
|-------|-------|
| Group name | `admin` |
| Description | `Administrator group with full access` |
| IAM role | *(leave empty — not needed)* |

Click **Create group**

**📸 Screenshot:** Groups tab showing `admin` group created

---

#### Step 3 — Deploy Lambda Functions

**Step 3.1: Create auth Lambda**

1. Go to Lambda Console → **Create function**
2. **Author from scratch**
3. Function name: `handson-auth-auth`
4. Runtime: Python 3.11
5. Execution role: Create or use `handson-auth-lambda-role`
6. Click **Create function**
7. Paste content of `src/auth_handler.py` into code editor
8. Click **Deploy**
9. Set environment variables:

| Key | Value (replace with your values) |
|-----|----------------------------------|
| `COGNITO_CLIENT_ID` | `[App Client ID from Step 1.7]` |
| `USER_POOL_ID` | `[User Pool ID from Step 1.8]` |

**Step 3.2: Create protected Lambda**

1. Create another function: `handson-auth-protected`
2. Same runtime and execution role
3. Paste content of `src/protected_handler.py`
4. Deploy — this Lambda needs no environment variables

---

#### Step 4 — Create API Gateway with JWT Authorizer

**Step 4.1: Create HTTP API**
1. Go to API Gateway → **Create API** → **HTTP API** → **Build**
2. Add integration → Lambda → `handson-auth-auth`
3. API name: `handson-auth-gateway`
4. Configure routes:

| Method | Path | Integration |
|--------|------|-------------|
| POST | `/auth/register` | `handson-auth-auth` |
| POST | `/auth/login` | `handson-auth-auth` |
| GET | `/protected` | `handson-auth-protected` |

5. Stage: `$default` → Create

**Step 4.2: Add JWT Authorizer**

1. In your API → **Authorization** tab → **Manage authorizers** → **Create**
2. Configure:

| Field | Value | Explanation |
|-------|-------|-------------|
| Authorizer type | **JWT** | Built-in token validation |
| Name | `cognito-authorizer` | Descriptive |
| Identity source | `$request.header.Authorization` | Where to find the token |
| Issuer URL | `https://cognito-idp.us-east-1.amazonaws.com/[YOUR_POOL_ID]` | Token issuer |
| Audience | `[YOUR_CLIENT_ID]` | Expected token audience |

3. Click **Create**

**Step 4.3: Attach Authorizer to Protected Route**

1. Go to **Routes** tab
2. Click on `GET /protected`
3. **Authorization** → Select `cognito-authorizer`
4. Click **Attach authorizer**

**📸 Screenshot:** Route showing `cognito-authorizer` attached to GET /protected

**Step 4.4: Validate Result**

**Expected Outcome:** GET /protected without a token returns 401 Unauthorized

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"
curl -s $API_URL/protected
# Expected: {"message":"Unauthorized"}
```

### METHOD B — AWS CLI Method

```bash
# ── Set variables ─────────────────────────────────────────────────────────────
REGION="us-east-1"
POOL_NAME="handson-auth-user-pool"
CLIENT_NAME="handson-auth-client"

# ── 1. Create Cognito User Pool ───────────────────────────────────────────────
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name $POOL_NAME \
  --policies 'PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true}' \
  --auto-verified-attributes email \
  --username-attributes email \
  --query "UserPool.Id" --output text)

echo "✅ User Pool ID: $USER_POOL_ID"

# ── 2. Create App Client (no secret — for SPA/mobile) ─────────────────────────
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name $CLIENT_NAME \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query "UserPoolClient.ClientId" --output text)

echo "✅ Client ID: $CLIENT_ID"

# ── 3. Create admin group ─────────────────────────────────────────────────────
aws cognito-idp create-group \
  --group-name admin \
  --user-pool-id $USER_POOL_ID \
  --description "Administrator group"

echo "✅ Admin group created"

# ── 4. Deploy Lambda functions ────────────────────────────────────────────────
ROLE_ARN=$(aws iam get-role --role-name handson-auth-lambda-role \
  --query Role.Arn --output text)

# Package handlers
cd src
zip ../auth_handler.zip auth_handler.py && zip ../protected_handler.zip protected_handler.py
cd ..

# Create auth Lambda
aws lambda create-function \
  --function-name handson-auth-auth \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler auth_handler.handler \
  --zip-file fileb://auth_handler.zip \
  --timeout 30 \
  --environment Variables="{COGNITO_CLIENT_ID=$CLIENT_ID,USER_POOL_ID=$USER_POOL_ID}"

# Create protected Lambda
aws lambda create-function \
  --function-name handson-auth-protected \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler protected_handler.handler \
  --zip-file fileb://protected_handler.zip \
  --timeout 30

aws lambda wait function-active --function-name handson-auth-auth
aws lambda wait function-active --function-name handson-auth-protected
echo "✅ Lambda functions deployed"

# ── 5. Create API with routes ─────────────────────────────────────────────────
AUTH_LAMBDA_ARN=$(aws lambda get-function --function-name handson-auth-auth \
  --query Configuration.FunctionArn --output text)
PROTECTED_LAMBDA_ARN=$(aws lambda get-function --function-name handson-auth-protected \
  --query Configuration.FunctionArn --output text)

API_ID=$(aws apigatewayv2 create-api \
  --name handson-auth-gateway \
  --protocol-type HTTP \
  --query ApiId --output text)

# Create integrations
AUTH_INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $AUTH_LAMBDA_ARN \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

PROTECTED_INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $PROTECTED_LAMBDA_ARN \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

# Create JWT Authorizer
AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
  --api-id $API_ID \
  --authorizer-type JWT \
  --identity-sources '$request.header.Authorization' \
  --name cognito-authorizer \
  --jwt-configuration "Audience=$CLIENT_ID,Issuer=https://cognito-idp.$REGION.amazonaws.com/$USER_POOL_ID" \
  --query AuthorizerId --output text)

echo "✅ JWT Authorizer: $AUTHORIZER_ID"

# Create routes
aws apigatewayv2 create-route \
  --api-id $API_ID --route-key "POST /auth/register" \
  --target "integrations/$AUTH_INT_ID"

aws apigatewayv2 create-route \
  --api-id $API_ID --route-key "POST /auth/login" \
  --target "integrations/$AUTH_INT_ID"

# Protected route WITH authorizer
aws apigatewayv2 create-route \
  --api-id $API_ID --route-key "GET /protected" \
  --target "integrations/$PROTECTED_INT_ID" \
  --authorization-type JWT \
  --authorizer-id $AUTHORIZER_ID

# Deploy stage
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --auto-deploy

# Grant Lambda invoke permissions
for FUNC in handson-auth-auth handson-auth-protected; do
  aws lambda add-permission \
    --function-name $FUNC \
    --statement-id apigw-invoke-$FUNC \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"
done

API_URL=$(aws apigatewayv2 get-api --api-id $API_ID \
  --query ApiEndpoint --output text)
echo "✅ API URL: $API_URL"
```

---

## 7. Code Deep Dive

**`src/auth_handler.py` — Key Sections:**

```python
# cognito.initiate_auth() — the LOGIN call
result = cognito.initiate_auth(
    ClientId=COGNITO_CLIENT_ID,
    AuthFlow="USER_PASSWORD_AUTH",     # Username + password flow
    AuthParameters={
        "USERNAME": username,
        "PASSWORD": password
    },
)
# Returns THREE tokens:
# AuthenticationResult.IdToken    → Use for API calls (contains user identity + groups)
# AuthenticationResult.AccessToken → For Cognito API operations
# AuthenticationResult.RefreshToken → Exchange for new tokens when IdToken expires
```

```python
# auto-confirm for development — REMOVE in production!
cognito.admin_confirm_sign_up(UserPoolId=USER_POOL_ID, Username=username)
# In production: users confirm via email link — remove this line
# This bypasses the email verification step for lab convenience
```

**`src/protected_handler.py` — Claims Extraction:**

```python
# How JWT claims arrive in Lambda:
# API Gateway decodes the JWT and injects claims into the event
claims = event["requestContext"]["authorizer"]["jwt"]["claims"]

# Claims available:
# claims["cognito:username"]  → "alice"
# claims["email"]             → "alice@example.com"
# claims["cognito:groups"]    → "admin,users"  (comma-separated string!)
# claims["exp"]               → Unix timestamp of expiry
# claims["sub"]               → User UUID (permanent identifier)

# Parse groups — it's a comma-separated string, not a list!
groups = claims.get("cognito:groups", "").split(",")
# ["admin"] or ["admin", "users"] or []
```

**JWT Token Structure (decoded):**
```json
Header: {"alg": "RS256", "kid": "key-id"}

Payload: {
  "sub": "user-uuid-permanent",
  "cognito:username": "alice",
  "email": "alice@example.com",
  "cognito:groups": ["admin"],
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXX",
  "aud": "client-id",
  "exp": 1704067200,
  "iat": 1704063600
}
```

**Common Mistakes:**

| Mistake | Fix |
|---------|-----|
| Using `AccessToken` for API calls | Use `IdToken` — it has the user claims and groups |
| `cognito:groups` as list | It's a comma-separated string — split it |
| Not handling token expiry | Handle 401 → refresh token → retry |
| Secret in App Client | Never use client secret for browser/mobile apps |

---

## 8. Verification & Validation

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"
USER_POOL_ID="us-east-1_XXXXXXXXX"

# 1. Register a user
curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@1234","email":"test@example.com"}' \
  | python3 -m json.tool
# Expected: 201 {"message": "User testuser registered successfully"}

# 2. Login and extract token
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")
echo "Token: ${TOKEN:0:50}..."

# 3. Access without token — 401
curl -s $API_URL/protected
# Expected: {"message":"Unauthorized"}

# 4. Access with valid token — 200
curl -s $API_URL/protected \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Expected: 200 with user info

# 5. Add user to admin group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username testuser \
  --group-name admin

# 6. Re-login to get token with group claims
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# 7. Decode JWT payload — verify admin group claim
python3 << 'EOF'
import base64, json
token = "PASTE_TOKEN_HERE"
payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
print("Username:", payload.get("cognito:username"))
print("Groups:", payload.get("cognito:groups"))
print("Expires:", payload.get("exp"))
EOF
# Expected: Groups: ['admin']
```

**📸 Screenshot Guidance:**

| When | What to Capture |
|------|----------------|
| After Step 1 | Cognito User Pool with Pool ID |
| After Step 2 | Groups tab showing `admin` group |
| After register | 201 response with success message |
| After login | 200 response with id_token, access_token, refresh_token |
| After Step 4.3 | API Gateway route with JWT authorizer attached |
| Testing | 401 response without token |
| Testing | 200 response with valid token |
| Decode | JWT payload showing `cognito:groups: ["admin"]` |

---

## 9. Observations & Learning Notes

1. **JWT is stateless:** The API Gateway validates the token by checking the signature against Cognito's public JWKS endpoint — no database lookup needed. This makes validation extremely fast and scalable.

2. **Token expiry:** ID tokens expire in 1 hour by default. Refresh tokens last 30 days. Your app should silently refresh using the refresh token before the ID token expires.

3. **JWKS endpoint:** Cognito exposes public keys at `https://cognito-idp.REGION.amazonaws.com/POOL_ID/.well-known/jwks.json`. API Gateway fetches and caches these to validate signatures.

4. **Group propagation delay:** After adding a user to a group, they must re-login — the existing token does NOT update. This is by design (tokens are immutable after issuance).

5. **JWT vs session cookies:** JWT is stateless (server doesn't store state). Sessions require a session store (Redis/DB). JWT scales better but can't be instantly invalidated — that's why expiry is short (1 hour).

6. **Cost:** Cognito User Pools are FREE for the first 50,000 MAU — permanent, not just 12 months.

---

## 10. Cleanup Steps

```bash
# 1. Delete API Gateway
aws apigatewayv2 delete-api --api-id $API_ID

# 2. Delete Lambda functions
aws lambda delete-function --function-name handson-auth-auth
aws lambda delete-function --function-name handson-auth-protected

# 3. Delete Cognito User Pool (must delete app clients first)
aws cognito-idp delete-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID

aws cognito-idp delete-user-pool \
  --user-pool-id $USER_POOL_ID

echo "✅ All auth resources deleted"
```

---

## 11. Estimated AWS Cost

| Resource | Free Tier | Notes |
|----------|-----------|-------|
| Cognito User Pool | **50,000 MAU free — forever** | Sufficient for any lab |
| JWT Authorizer validation | **Free** | Built into API Gateway |
| Lambda (auth + protected) | 1M requests/month free | |
| API Gateway | 1M calls/month free (12 months) | |
| **Total for lab** | **~$0.01/month** | Only API Gateway calls |

> ✅ **Free Tier Eligible:** Cognito is permanently free up to 50K MAU. This project costs essentially nothing for lab use.

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
