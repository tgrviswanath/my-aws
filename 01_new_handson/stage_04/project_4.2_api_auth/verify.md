# Verification & Validation — Project 4.2 API Authentication & Authorization

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Cognito User Pool | Cognito → User pools | Pool exists, MFA = optional |
| App Client | User pool → App clients | Client with no secret (for SPA/mobile) |
| Admin Group | User pool → Groups | `admin` group exists |
| JWT Authorizer | API Gateway → Authorizers | Cognito authorizer attached to protected routes |
| Protected Routes | API Gateway → Routes | `/protected` requires authorization |

📸 Screenshot: Cognito User Pool created  
📸 Screenshot: 401 response without token  
📸 Screenshot: 200 response with valid JWT token  
📸 Screenshot: JWT decoded showing `cognito:groups` claim

---

## 2. AWS CLI Verification

```bash
API_URL=$(cd terraform && terraform output -raw api_url)
USER_POOL_ID=$(cd terraform && terraform output -raw user_pool_id)
CLIENT_ID=$(cd terraform && terraform output -raw client_id)

# 2.1 User pool exists
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID \
  --query "UserPool.{Name:Name,Status:Status,Id:Id}"
# Expected: Status=ACTIVE (or no Status field — means active)

# 2.2 Register user
curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"verifyuser","password":"Verify@1234","email":"verify@example.com"}' \
  | python3 -m json.tool
# Expected: 201 with user created message

# 2.3 Login and get token
TOKEN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"verifyuser","password":"Verify@1234"}')
echo $TOKEN_RESPONSE | python3 -m json.tool
# Expected: id_token, access_token, refresh_token

ID_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# 2.4 Without token — 401
curl -s $API_URL/protected
# Expected: {"message":"Unauthorized"} with 401

# 2.5 With valid token — 200
curl -s $API_URL/protected \
  -H "Authorization: Bearer $ID_TOKEN" | python3 -m json.tool
# Expected: 200 with user info

# 2.6 With invalid token — 401
curl -s $API_URL/protected \
  -H "Authorization: Bearer invalid.token.here"
# Expected: 401 Unauthorized

# 2.7 Add user to admin group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username verifyuser \
  --group-name admin

# 2.8 Re-login to get token with group claims
TOKEN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"verifyuser","password":"Verify@1234"}')
ADMIN_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# 2.9 Decode JWT payload — confirm group claim
echo $ADMIN_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool | grep -A2 "cognito:groups"
# Expected: "cognito:groups": ["admin"]
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_cognito_user_pool.main
# aws_cognito_user_pool_client.app
# aws_cognito_user_group.admin
# aws_apigatewayv2_authorizer.cognito
# aws_lambda_function.auth_handler
# aws_lambda_function.protected_handler

terraform state show aws_apigatewayv2_authorizer.cognito
# Shows: authorizer_type=JWT, identity_sources=$request.header.Authorization

terraform output
# Expected: api_url, user_pool_id, client_id

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Token Expiry

```bash
# Decode JWT to check expiry
python3 << 'EOF'
import base64, json, time

token = "PASTE_YOUR_ID_TOKEN_HERE"
payload = json.loads(base64.b64decode(token.split(".")[1] + "=="))
exp = payload.get("exp", 0)
remaining = exp - int(time.time())
print(f"Token expires in: {remaining // 60} minutes")
print(f"Issuer: {payload.get('iss')}")
print(f"Groups: {payload.get('cognito:groups', [])}")
print(f"Username: {payload.get('cognito:username')}")
EOF
# Expected: expiry in ~60 minutes, correct issuer URL
```

---

## 5. Expected Successful Outputs

**Register (201):**
```json
{ "message": "User registered successfully", "username": "verifyuser" }
```

**Login (200):**
```json
{ "id_token": "eyJ...", "access_token": "eyJ...", "refresh_token": "eyJ..." }
```

**Protected without token (401):**
```json
{ "message": "Unauthorized" }
```

**Protected with valid token (200):**
```json
{ "message": "Access granted", "user": "verifyuser", "groups": ["admin"] }
```

**JWT payload (decoded):**
```json
{
  "cognito:username": "verifyuser",
  "cognito:groups": ["admin"],
  "email": "verify@example.com",
  "exp": 1704067200
}
```

---

## 6. Verification Checklist

- [ ] Cognito User Pool created and active
- [ ] App client created (no secret)
- [ ] `admin` group exists in User Pool
- [ ] JWT Authorizer attached to protected routes in API Gateway
- [ ] POST /auth/register returns 201
- [ ] POST /auth/login returns id_token, access_token, refresh_token
- [ ] GET /protected without token returns 401
- [ ] GET /protected with valid token returns 200
- [ ] GET /protected with invalid token returns 401
- [ ] User added to admin group via CLI
- [ ] Re-login token contains `cognito:groups: ["admin"]` claim
- [ ] JWT expiry is ~60 minutes from issue time
- [ ] `terraform plan` shows no changes
