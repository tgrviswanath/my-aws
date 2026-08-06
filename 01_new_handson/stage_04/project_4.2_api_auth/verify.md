# Verification & Validation — Project 4.2 API Authentication & Authorization

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Cognito User Pool | Cognito → User pools | `handson-auth-user-pool` exists |
| App Client | User pool → App clients | `handson-auth-client` (no secret) |
| Admin Group | User pool → Groups | `admin` group exists |
| Users Group | User pool → Groups | `users` group exists |
| JWT Authorizer | API Gateway → Authorizers | `cognito-jwt-authorizer` attached to protected routes |
| Protected Route | API Gateway → Routes | `GET /protected` has Authorization = JWT |
| Lambda auth | Lambda → Functions | `handson-auth-auth`, Runtime = Python 3.11 |
| Lambda protected | Lambda → Functions | `handson-auth-protected`, Runtime = Python 3.11 |

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
  --query "UserPool.{Name:Name,Id:Id}"
# Expected: Name=handson-auth-user-pool

# 2.2 Register user
curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"verifyuser","password":"Verify@1234","email":"verify@example.com"}' \
  | python3 -m json.tool
# Expected: 201 {"message": "User verifyuser registered successfully"}

# 2.3 Login and get token
TOKEN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"verifyuser","password":"Verify@1234"}')
echo $TOKEN_RESPONSE | python3 -m json.tool
# Expected: id_token, access_token, refresh_token, expires_in, token_type

ID_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# 2.4 Without token — 401
curl -s $API_URL/protected
# Expected: {"message":"Unauthorized"} with 401

# 2.5 With valid token — 200
curl -s $API_URL/protected \
  -H "Authorization: Bearer $ID_TOKEN" | python3 -m json.tool
# Expected: 200 with {"message": "Hello, verifyuser!", "user": {...}, "path": "/protected", "method": "GET", "note": "..."}

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
# aws_cognito_user_group.users
# aws_apigatewayv2_authorizer.jwt
# aws_apigatewayv2_route.register
# aws_apigatewayv2_route.login
# aws_apigatewayv2_route.protected
# aws_lambda_function.auth
# aws_lambda_function.protected
# aws_iam_role.lambda
# aws_iam_role_policy_attachment.lambda_basic
# aws_iam_role_policy.cognito

terraform state show aws_apigatewayv2_authorizer.jwt
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
{ "message": "User verifyuser registered successfully" }
```

**Login (200):**
```json
{
  "access_token": "eyJ...",
  "id_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Protected without token (401):**
```json
{ "message": "Unauthorized" }
```

**Protected with valid token (200):**
```json
{
  "message": "Hello, verifyuser!",
  "user": {"username": "verifyuser", "email": "verify@example.com", "groups": ["admin"]},
  "path": "/protected",
  "method": "GET",
  "note": "This endpoint is protected — you must have a valid JWT to reach here"
}
```

**POST /protected (admin required, non-admin user — 403):**
```json
{ "error": "Forbidden", "message": "User verifyuser does not have admin privileges" }
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

- [ ] Cognito User Pool `handson-auth-user-pool` created and active
- [ ] App client `handson-auth-client` created (no secret)
- [ ] `admin` group exists in User Pool
- [ ] `users` group exists in User Pool
- [ ] JWT Authorizer `cognito-jwt-authorizer` attached to `GET /protected`
- [ ] POST /auth/register returns 201
- [ ] POST /auth/login returns id_token, access_token, refresh_token, expires_in, token_type
- [ ] GET /protected without token returns 401
- [ ] GET /protected with valid token returns 200 with `"message": "Hello, {username}!"`
- [ ] GET /protected with invalid token returns 401
- [ ] User added to admin group via CLI
- [ ] Re-login token contains `cognito:groups: ["admin"]` claim
- [ ] JWT expiry is ~60 minutes from issue time
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
