# Steps — Project 4.2 API Authentication & Authorization

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -auto-approve

API_URL=$(terraform output -raw api_url)
echo "API: $API_URL"
```

---

## Phase 2 — Register and Login

```bash
# Register a new user
curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "Test@1234", "email": "test@example.com"}' \
  | python3 -m json.tool

# Login and get JWT token
TOKEN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "Test@1234"}')

echo $TOKEN_RESPONSE | python3 -m json.tool

# Extract the ID token (used for API calls)
ID_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")
echo "Token: ${ID_TOKEN:0:50}..."
```

---

## Phase 3 — Access Protected Endpoint

```bash
# Without token — should fail
curl -s $API_URL/protected
# Expected: 401 Unauthorized

# With valid token — should succeed
curl -s $API_URL/protected \
  -H "Authorization: Bearer $ID_TOKEN" \
  | python3 -m json.tool
# Expected: 200 with user info

# With expired/invalid token — should fail
curl -s $API_URL/protected \
  -H "Authorization: Bearer invalid.token.here" \
  | python3 -m json.tool
# Expected: 401 Unauthorized
```

---

## Phase 4 — Test RBAC (Admin vs Regular User)

```bash
# Add user to admin group via CLI
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $(terraform output -raw user_pool_id) \
  --username testuser \
  --group-name admin

# Login again to get new token with group claims
TOKEN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "Test@1234"}')

ADMIN_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# Decode JWT to see group claims (base64 decode the payload)
echo $ADMIN_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
# Look for: "cognito:groups": ["admin"]
```

---

## Phase 5 — Inspect JWT Token

```bash
# Decode JWT without verification (for learning only)
python3 << 'EOF'
import base64, json, sys

token = "YOUR_ID_TOKEN_HERE"
parts = token.split(".")

# Decode header
header = json.loads(base64.b64decode(parts[0] + "=="))
print("Header:", json.dumps(header, indent=2))

# Decode payload (claims)
payload = json.loads(base64.b64decode(parts[1] + "=="))
print("Payload:", json.dumps(payload, indent=2))
EOF
```

---

## Screenshots to Take
- [ ] Cognito User Pool created in console
- [ ] User registered successfully (201 response)
- [ ] Login returning JWT tokens
- [ ] 401 when hitting protected endpoint without token
- [ ] 200 when hitting protected endpoint with valid token
- [ ] JWT decoded showing user claims and groups
- [ ] Admin group assignment in Cognito console
