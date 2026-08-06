# Project 4.2 — API Authentication & Authorization
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create Cognito User Pool

**Prerequisites Check:**
- ✅ Required permissions: `cognito-idp:CreateUserPool`, `cognito-idp:CreateUserPoolClient`
- ✅ Services enabled: Amazon Cognito
- ✅ Region availability: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [Cognito Console](https://console.aws.amazon.com/cognito)
2. **Expected View:** Cognito home with "Create user pool" button
3. **If Different:** Verify region is us-east-1

**Step 1.2: Make Selections**

Click **Create user pool**

**Decision Point 1:** Sign-in Options

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Username | Traditional username-based login | ✅ Check this |
| Email | Login with email as username | ✅ Check this too |
| Phone number | SMS-based login | ❌ Adds SMS cost |

Check both **Username** and **Email** → Click **Next**

**📸 Screenshot:** Step 1 "Configure sign-in experience" with Username + Email checked

**Step 1.3: Configure Password Policy**

**Decision Point 2:** Password Strength

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Cognito defaults | 8 chars, upper/lower/numbers | ✅ Keep defaults |
| Custom | Stricter requirements | ❌ Unnecessary for lab |

Leave all defaults → Click **Next**

**Step 1.4: Configure MFA**

| Setting | Value | Why |
|---------|-------|-----|
| MFA enforcement | **No MFA** | Simplify for learning |
| User account recovery | **Email only** | Simple self-service recovery |

Click **Next**

**Step 1.5: Configure Sign-up Experience**

| Setting | Value |
|---------|-------|
| Self-registration | ✅ Allow users to register |
| Required attributes | `email` |
| Custom attributes | *(none)* |

Click **Next**

**Step 1.6: Configure Message Delivery**

**Decision Point 3:** Email Provider

| Option | Cost | Setup | For This Project |
|--------|------|-------|-----------------|
| Send email with Cognito | Free (up to 50/day) | None | ✅ Use this |
| Send email with SES | Requires SES setup | Complex | ❌ Unnecessary |

Select **Send email with Cognito** → Click **Next**

**Step 1.7: Integrate Your App**

| Field | Value | Explanation |
|-------|-------|-------------|
| User pool name | `handson-auth-user-pool` | Matches terraform naming |
| Hosted UI | **Don't use Hosted UI** | We build our own login |
| App type | **Public client** | For SPA/mobile (no secret) |
| App client name | `handson-auth-client` | Matches terraform naming |

Under **Authentication flows** — make sure these are enabled:
- ✅ `ALLOW_USER_PASSWORD_AUTH` — username/password flow
- ✅ `ALLOW_REFRESH_TOKEN_AUTH` — refresh token support

Click **Next** → Review all settings → Click **Create user pool**

**Step 1.8: Validate Result and Copy IDs**

**Expected Outcome:** User pool created. You will need two values — copy them now:

| Value | Where to find it | Example |
|-------|-----------------|---------|
| **User Pool ID** | User pool → top of page | `us-east-1_AbCdEfGhI` |
| **Client ID** | User pool → App clients tab → click app client | `3abc123defghijklmnop456789` |

**📸 Screenshot:** Cognito User Pool `handson-auth-user-pool` overview page showing User Pool ID and Status = Active

---

#### Step 2 — Create Admin Group

**Step 2.1: Navigate**
1. Click on your user pool `handson-auth-user-pool`
2. Click **Groups** tab
3. Click **Create group**

**Step 2.2: Configure**

| Field | Value | Explanation |
|-------|-------|-------------|
| Group name | `admin` | Lambda checks `cognito:groups` claim for this value |
| Description | `Administrator group with full access` | |
| IAM role | *(leave empty)* | Not needed — we check groups in Lambda code |
| Precedence | *(leave empty)* | |

Click **Create group**

**Step 2.3: Validate Result**

**Expected Outcome:** Groups tab shows `admin` group

**📸 Screenshot:** Cognito Groups tab showing `admin` group created

---

#### Step 3 — Create Lambda IAM Role

Same process as Project 4.1 Step 2. Role needs these policies:

| Policy | Why |
|--------|-----|
| `AWSLambdaBasicExecutionRole` | CloudWatch logs |
| `AmazonCognitoPowerUser` | Call Cognito APIs (register, login) |

Role name: `handson-auth-lambda-role`

---

#### Step 4 — Deploy auth Lambda

**Step 4.1: Create Function**

Lambda Console → **Create function** → Author from scratch

| Field | Value |
|-------|-------|
| Function name | `handson-auth-auth` |
| Runtime | Python 3.11 |
| Execution role | `handson-auth-lambda-role` |

**Step 4.2: Upload Code**

Paste entire content of `src/auth_handler.py` → Click **Deploy**

**Step 4.3: Set Environment Variables**

Configuration → Environment variables → Edit → Add:

| Key | Value |
|-----|-------|
| `COGNITO_CLIENT_ID` | Your App Client ID from Step 1.8 |
| `USER_POOL_ID` | Your User Pool ID from Step 1.8 |

Click **Save** → Set Timeout to 30s

**📸 Screenshot:** `handson-auth-auth` Lambda showing both Cognito environment variables

---

#### Step 5 — Deploy protected Lambda

Same process — create `handson-auth-protected`:

| Field | Value |
|-------|-------|
| Function name | `handson-auth-protected` |
| Runtime | Python 3.11 |
| Execution role | `handson-auth-lambda-role` |
| Code | Paste entire `src/protected_handler.py` |
| Environment variables | *(none needed)* |

---

#### Step 6 — Create HTTP API with JWT Authorizer

**Prerequisites Check:**
- ✅ Required permissions: `apigateway:POST`
- ✅ Both Lambda functions deployed
- ✅ Cognito User Pool and Client IDs ready

**Step 6.1: Create HTTP API**

1. API Gateway Console → **Create API** → **HTTP API** → **Build**
2. Add integration: Lambda → `handson-auth-auth`
3. API name: `handson-auth-gateway`
4. Configure routes:

| Method | Path | Integration |
|--------|------|-------------|
| POST | `/auth/register` | `handson-auth-auth` |
| POST | `/auth/login` | `handson-auth-auth` |
| GET | `/protected` | `handson-auth-protected` |

> **Note:** The `auth_handler.py` code also handles `POST /auth/refresh` but this route is NOT created by Terraform. If you need token refresh via the API, add this route manually in the console pointing to `handson-auth-auth`.

5. Stage: `$default` → Create

**Step 6.2: Add JWT Authorizer**

**Decision Point 1:** Authorizer Type

| Option | How it works | For This Project |
|--------|-------------|-----------------|
| JWT | API Gateway validates token automatically (free) | ✅ Use this |
| Lambda | Custom Lambda validates token ($0.20/million) | ❌ More expensive |

1. In your API → **Authorization** (left sidebar) → **Manage authorizers**
2. Click **Create**

| Field | Value | Explanation |
|-------|-------|-------------|
| Authorizer type | **JWT** | Built-in token validation |
| Name | `cognito-authorizer` | |
| Identity source | `$request.header.Authorization` | Where token is in request |
| Issuer URL | `https://cognito-idp.us-east-1.amazonaws.com/[YOUR_POOL_ID]` | Replaceе `[YOUR_POOL_ID]` |
| Audience | `[YOUR_CLIENT_ID]` | Replace with App Client ID |

Click **Create**

**📸 Screenshot:** JWT Authorizer creation form filled with Issuer URL and Audience

**Step 6.3: Attach Authorizer to Protected Route**

1. **Authorization** → **Attach authorizers to routes**
2. Click route `GET /protected`
3. Select `cognito-authorizer` from dropdown
4. Click **Attach authorizer**

**Decision Point 2:** Scope requirement

| Setting | Use Case | For This Project |
|---------|----------|-----------------|
| Authorization scopes empty | Any valid token works | ✅ Use this — we check groups in Lambda |
| Authorization scopes set | Only tokens with specific OAuth scopes | ❌ Not using OAuth scopes |

Leave scopes empty → Click **Attach authorizer**

**Step 6.4: Validate Result**

1. Copy the Invoke URL from API details page
2. Test without token — should get 401:
```bash
curl -s https://YOUR_ID.execute-api.us-east-1.amazonaws.com/protected
# Expected: {"message":"Unauthorized"}
```

**📸 Screenshot:** GET /protected route showing `cognito-authorizer` in Authorization column

---

#### Step 7 — Test the Full Auth Flow

**Step 7.1: Register a User**

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"

curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"Test@1234\", \"email\": \"test@example.com\"}"
# Expected: 201 {"message": "User testuser registered successfully"}
```

**📸 Screenshot:** POST /auth/register returning 201

**Step 7.2: Login and Get Token**

```bash
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"Test@1234\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")
echo "Token: ${TOKEN:0:60}..."
```

**📸 Screenshot:** POST /auth/login returning id_token, access_token, refresh_token

**Step 7.3: Access Protected Endpoint**

```bash
# Without token — 401
curl -s $API_URL/protected
# Expected: {"message":"Unauthorized"}

# With valid token — 200
curl -s $API_URL/protected \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"message": "Hello, testuser!", "user": {...}}
```

**📸 Screenshot:** Side-by-side — 401 without token vs 200 with valid token

**Step 7.4: Assign Admin Group and Verify RBAC**

1. Cognito Console → `handson-auth-user-pool` → **Users** tab
2. Click on `testuser`
3. **Group memberships** section → Click **Add user to group**
4. Select `admin` → Click **Add**

```bash
# Re-login to get new token with admin group claim
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"Test@1234\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# Decode JWT payload to verify group claim
python3 -c "
import base64, json
parts = '$TOKEN'.split('.')
payload = json.loads(base64.b64decode(parts[1] + '=='))
print('Username:', payload.get('cognito:username'))
print('Groups:', payload.get('cognito:groups'))
print('Expires in (mins):', (payload.get('exp',0) - __import__('time').time()) // 60)
"
# Expected: Groups: ['admin']
```

**📸 Screenshot:** JWT payload decoded showing `cognito:groups: ["admin"]`


---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| JWT token rejected (401) | Wrong audience claim | Verify `aud` matches your App Client ID in Cognito |
| Token expired (401) | Access token TTL passed | Re-authenticate to get a new token |
| CORS error in browser | API Gateway CORS not configured | Enable CORS on the API Gateway route |
| "Not authorized to access this resource" | Missing IAM policy | Check Lambda execution role permissions |
| Cognito user not confirmed | Email verification pending | Check inbox and confirm the account |
| API Gateway 502 | Lambda function error | Check CloudWatch Logs for the Lambda function |

```bash
# Debug auth issues
aws cognito-idp describe-user-pool --user-pool-id <pool-id>
aws cognito-idp list-user-pool-clients --user-pool-id <pool-id>
aws logs get-log-events --log-group-name /aws/lambda/<function-name> --log-stream-name <stream>
```
