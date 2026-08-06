# Project 4.1 — Serverless REST API
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** Serverless REST API with API Gateway + Lambda + DynamoDB

**Business / Problem Statement:**
Traditional REST APIs require servers — you provision EC2 instances, manage OS patches, handle scaling, and pay 24/7 even when idle. A serverless REST API eliminates all of that. You write business logic, AWS handles the rest: scaling from 0 to millions of requests, zero server management, and you pay only per request. This project builds a fully functional CRUD API that any frontend or mobile app can consume.

**Learning Objectives:**
- Understand how API Gateway routes HTTP requests to Lambda
- Build a complete CRUD API (Create, Read, Update, Delete) without any servers
- Learn DynamoDB as a serverless NoSQL database
- Understand Lambda cold starts, timeouts, and environment variables
- Practice IAM least-privilege permissions for Lambda
- Learn the difference between HTTP API (v2) and REST API (v1)

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| API Gateway (HTTP API v2) | Receives HTTP requests, routes to Lambda |
| Lambda (Python 3.11) | Executes CRUD business logic — stateless |
| DynamoDB | Serverless NoSQL database — stores items |
| IAM Role | Grants Lambda permission to access DynamoDB |
| CloudWatch Logs | Captures all Lambda logs automatically |

**Service Interaction Flow:**
```
Client (curl/browser/app)
    │  HTTPS Request (GET/POST/PUT/DELETE)
    ▼
API Gateway HTTP API
    │  Invokes Lambda with event payload
    ▼
Lambda Function (handler.py)
    │  Reads/Writes data
    ▼
DynamoDB Table (handson-items)
    │  Returns data
    ▼
Lambda → API Gateway → Client (JSON response)
```

**High-Level Architecture:**
```
┌───────────────────────────────────────────────────────────┐
│                        AWS Cloud                           │
│                                                            │
│   Client ──HTTPS──► API Gateway HTTP API                   │
│                           │                                │
│              ┌────────────┴───────────────┐                │
│              │     Lambda: handler.py      │                │
│              │  Python 3.11 | 128MB | 30s │                │
│              └────────────┬───────────────┘                │
│                           │ boto3 SDK                       │
│              ┌────────────▼───────────────┐                │
│              │  DynamoDB: handson-items    │                │
│              │  PK: id (String)            │                │
│              │  Billing: PAY_PER_REQUEST   │                │
│              └────────────────────────────┘                │
│                                                            │
│   CloudWatch Logs: /aws/lambda/handson-items               │
└───────────────────────────────────────────────────────────┘
```

**Best Practices Followed:**
- HTTP API v2 used (3x cheaper than REST API v1)
- DynamoDB PAY_PER_REQUEST billing (no capacity planning)
- Lambda environment variables for table name (no hardcoding)
- IAM least-privilege: Lambda only has DynamoDB read/write, nothing else
- Proper HTTP status codes (201 for create, 404 for not found, 400 for bad input)
- CORS headers included for browser compatibility

---

## 3. Prerequisites

**AWS Account Setup:**
- Active AWS account with billing enabled
- Sign in at: https://console.aws.amazon.com

**IAM Permissions Required:**
Your IAM user needs these permissions to deploy this project:
```
lambda:CreateFunction, lambda:UpdateFunctionCode, lambda:InvokeFunction
apigateway:* (create API, routes, integrations, stages)
dynamodb:CreateTable, dynamodb:DescribeTable
iam:CreateRole, iam:AttachRolePolicy, iam:PassRole
logs:CreateLogGroup, logs:DescribeLogGroups
```
Easiest approach for learning: attach `AdministratorAccess` to your IAM user.

**Local Machine Requirements:**

| Tool | Version | Install |
|------|---------|---------|
| AWS CLI | v2.x | https://aws.amazon.com/cli/ |
| Python | 3.11+ | https://python.org |
| Terraform | 1.6+ | https://terraform.io/downloads |
| Git | Any | https://git-scm.com |
| VS Code | Any | https://code.visualstudio.com |
| curl | Any | Pre-installed on Mac/Linux; use Git Bash on Windows |

**AWS CLI Configuration:**
```bash
aws configure
# AWS Access Key ID: [your key]
# AWS Secret Access Key: [your secret]
# Default region name: us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
```

**Required AWS Region:** `us-east-1` (N. Virginia) — all free tier benefits apply

**Environment Variable Setup:**
```bash
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $AWS_ACCOUNT_ID"
```

---

## 4. Project Folder Structure

```
project_4.1_serverless_rest_api/
│
├── README.md               ← What this project does, architecture summary
├── GUIDE.md                ← This file — complete implementation guide
├── steps.md                ← Quick step-by-step deploy and test commands
├── verify.md               ← Verification checklist with expected outputs
├── cost_estimate.md        ← AWS cost breakdown per resource
│
├── src/
│   └── handler.py          ← Lambda function — all CRUD logic lives here
│
├── docs/
│   └── architecture.md     ← Architecture diagrams and design notes
│
└── terraform/
    └── main.tf             ← Infrastructure as Code — creates all AWS resources
```

**File-by-File Explanation:**

| File | Purpose | When to edit |
|------|---------|-------------|
| `src/handler.py` | Lambda code — handles all HTTP methods and DynamoDB operations | When changing API behavior |
| `terraform/main.tf` | Declares API Gateway, Lambda, DynamoDB, IAM in code | When changing infrastructure |
| `steps.md` | Practical deploy + test commands | Reference during lab |
| `verify.md` | Checklist to confirm everything works | After deployment |
| `cost_estimate.md` | Cost per resource | Before deploying to production |

**Naming Conventions Used:**
- Lambda function: `handson-api-handler` (prefix `handson-` for all lab resources)
- DynamoDB table: `handson-api-items`
- IAM role: `handson-lambda-exec-role`
- Log group: `/aws/lambda/handson-api-handler` (auto-created by Lambda)

---

## 5. Project Input & Output

**INPUT — What you provide:**
```
HTTP Request with JSON body

POST /items
{"name": "Widget A", "description": "A blue widget"}

PUT /items/{id}
{"description": "Updated description"}
```

**OUTPUT — What you get back:**
```
POST /items  → 201 Created
{"id": "uuid-abc123", "name": "Widget A", "description": "A blue widget", "created_at": "2024-01-01T12:00:00Z"}

GET /items   → 200 OK
{"items": [...], "count": 2}

GET /items/{id} → 200 OK | 404 Not Found
{"id": "...", "name": "...", "description": "...", "created_at": "...", "updated_at": "..."}

DELETE /items/{id} → 200 OK | 404 Not Found
{"message": "Item uuid-abc123 deleted"}

Error cases:
POST /items (missing name) → 400 {"error": "Field 'name' is required"}
GET /items/bad-id          → 404 {"error": "Item bad-id not found"}
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create the DynamoDB Table

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`
- ✅ Services enabled: DynamoDB (available in all regions)
- ✅ Region: us-east-1 selected in console top-right

**Step 1.1: Navigate and Verify**
1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb)
2. **Expected View:** DynamoDB dashboard with "Create table" button
3. **If Different:** Ensure region = us-east-1 in top-right selector

**Step 1.2: Make Selections**

**Decision Point 1:** Table Class

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| DynamoDB Standard | General purpose, frequent access | ✅ Use this |
| DynamoDB Standard-IA | Infrequent access, lower cost | ❌ Not needed for lab |

**📸 Screenshot:** DynamoDB console showing "Create table" button and us-east-1 region

**Step 1.3: Configure Details**

Click **Create table** and fill in:

| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-api-items` | Prefix `handson-` for easy cleanup later |
| Partition key | `id` | Type: **String** — unique identifier per item |
| Sort key | *(leave empty)* | Not needed — we look up by ID only |

Scroll to **Table settings:**

| Setting | Value | Explanation |
|---------|-------|-------------|
| Table class | DynamoDB Standard | Default, best for lab |
| Read/Write capacity | **On-demand** | Pay per request — no capacity planning |

> **Why On-demand?** With provisioned capacity you must predict traffic. On-demand scales automatically and charges only for actual reads/writes — perfect for unpredictable lab usage.

Click **Create table**

**Step 1.4: Validate Result**

**Expected Outcome:** Table status changes from **Creating** → **Active** (takes ~30 seconds)

**📸 Screenshot:** DynamoDB table list showing `handson-api-items` with Status = Active

**Troubleshooting:**
- `Table already exists`: Add a suffix like `handson-api-items-2`
- `Access denied`: Check your IAM user has `dynamodb:CreateTable` permission

---

#### Step 2 — Create the Lambda IAM Role

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global service)

**Step 2.1: Navigate and Verify**
1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Click **Roles** in left sidebar
3. **Expected View:** List of existing roles with "Create role" button

**Step 2.2: Make Selections**

**Decision Point 1:** Trusted Entity Type

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | Service (like Lambda) assumes this role | ✅ Select this |
| AWS account | Cross-account access | ❌ Not needed |
| Web identity | Federated/OIDC | ❌ Not needed |

Select: **AWS service** → Choose **Lambda** → Click **Next**

**📸 Screenshot:** Role creation showing "AWS service" and "Lambda" selected

**Step 2.3: Configure Details**

On the "Add permissions" page, search and attach:

1. Search: `AWSLambdaBasicExecutionRole` → ✅ Check it
   - This gives Lambda permission to write logs to CloudWatch

2. Search: `AmazonDynamoDBFullAccess` → ✅ Check it
   - This gives Lambda read/write access to DynamoDB

> **Production note:** For production, create a custom policy that only allows access to the specific table. `AmazonDynamoDBFullAccess` is used here for simplicity.

Click **Next** → Enter role details:

| Field | Value |
|-------|-------|
| Role name | `handson-lambda-exec-role` |
| Description | `Lambda execution role for serverless REST API` |

Click **Create role**

**Step 2.4: Validate Result**

**Expected Outcome:** Role appears in the roles list with 2 attached policies

**📸 Screenshot:** Role details showing both attached policies

---

#### Step 3 — Create and Deploy the Lambda Function

**Prerequisites Check:**
- ✅ Required permissions: `lambda:CreateFunction`
- ✅ IAM role created: `handson-lambda-exec-role`
- ✅ DynamoDB table created: `handson-api-items`

**Step 3.1: Navigate and Verify**
1. Go to [Lambda Console](https://console.aws.amazon.com/lambda)
2. **Expected View:** Lambda functions list with "Create function" button

**Step 3.2: Make Selections**

**Decision Point 1:** Creation Method

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Author from scratch | Write code in console | ✅ Use this |
| Use a blueprint | Pre-built templates | ❌ We have our own code |
| Container image | Docker-based Lambda | ❌ Not needed here |

Select **Author from scratch**

**Step 3.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Function name | `handson-api-handler` | Descriptive name |
| Runtime | **Python 3.11** | Matches our code |
| Architecture | x86_64 | Default, lowest cost |
| Execution role | **Use an existing role** | Select `handson-lambda-exec-role` |

Click **Create function**

**Step 3.4: Upload the Code**

1. In the function page, scroll to **Code source**
2. Click the file `lambda_function.py` in the editor
3. **Delete all existing code**
4. Copy the entire content of `src/handler.py` and paste it in
5. Click **Deploy** (orange button)

**Step 3.5: Set Environment Variables**

1. Go to **Configuration** tab → **Environment variables**
2. Click **Edit** → **Add environment variable**

| Key | Value |
|-----|-------|
| `TABLE_NAME` | `handson-api-items` |

Click **Save**

**Step 3.6: Update Timeout**

1. Go to **Configuration** tab → **General configuration**
2. Click **Edit**
3. Set **Timeout** to `30` seconds (default 3s is too short for DynamoDB)
4. Click **Save**

**Step 3.7: Validate Result**

**Expected Outcome:** Lambda shows "Changes deployed" and configuration shows TABLE_NAME env var

**📸 Screenshot:** Lambda function with code deployed and TABLE_NAME environment variable set

**Troubleshooting:**
- `Execution role not found`: Make sure the role name matches exactly
- Deploy button greyed out: Check for syntax errors in the code

---

#### Step 4 — Create the API Gateway (HTTP API)

**Prerequisites Check:**
- ✅ Required permissions: `apigateway:*`
- ✅ Lambda function created: `handson-api-handler`

**Step 4.1: Navigate and Verify**
1. Go to [API Gateway Console](https://console.aws.amazon.com/apigateway)
2. **Expected View:** API Gateway dashboard showing existing APIs

**Step 4.2: Make Selections**

**Decision Point 1:** API Type

| Option | Cost | Features | For This Project |
|--------|------|----------|-----------------|
| HTTP API | ~$1/million | Core routing, JWT auth, CORS | ✅ Use this |
| REST API | ~$3.50/million | Full features, API keys, usage plans | ❌ More expensive |
| WebSocket API | Variable | Real-time bidirectional | ❌ Not needed |

Click **Build** under **HTTP API**

**Step 4.3: Configure Details**

1. Click **Add integration** → Select **Lambda**
2. Select region: `us-east-1`
3. Select Lambda function: `handson-api-handler`
4. API name: `handson-rest-api`
5. Click **Next**

**Configure routes:**
- Click **Add route** for each:

| Method | Resource path |
|--------|--------------|
| GET | `/items` |
| POST | `/items` |
| GET | `/items/{id}` |
| PUT | `/items/{id}` |
| DELETE | `/items/{id}` |

- For each route, set Integration target = `handson-api-handler`

Click **Next** → Stage name: `$default` → Click **Next** → Click **Create**

**Step 4.4: Validate Result**

**Expected Outcome:** API created with Invoke URL shown (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com`)

**📸 Screenshot:** API Gateway showing Invoke URL and all 5 routes

**Troubleshooting:**
- `Lambda not found`: Ensure Lambda is in the same region
- Routes returning 500: Check Lambda logs in CloudWatch

---

### METHOD B — AWS CLI Method

```bash
# ── 1. Set variables ──────────────────────────────────────────────────────────
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
TABLE_NAME="handson-api-items"
LAMBDA_NAME="handson-api-handler"
ROLE_NAME="handson-lambda-exec-role"
API_NAME="handson-rest-api"

echo "Account: $ACCOUNT_ID | Region: $REGION"

# ── 2. Create DynamoDB table ──────────────────────────────────────────────────
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION

# Expected output:
# {
#   "TableDescription": {
#     "TableName": "handson-api-items",
#     "TableStatus": "CREATING",
#     "BillingModeSummary": {"BillingMode": "PAY_PER_REQUEST"}
#   }
# }

# Wait for table to become ACTIVE
aws dynamodb wait table-exists --table-name $TABLE_NAME
echo "✅ DynamoDB table created"

# ── 3. Create IAM role for Lambda ─────────────────────────────────────────────
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed policies
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Wait for role to propagate
sleep 10
echo "✅ IAM role created"

# Get role ARN for later use
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"

# ── 4. Package and deploy Lambda ──────────────────────────────────────────────
# Create deployment package (zip the source file)
cd src
zip ../function.zip handler.py
cd ..

# Create Lambda function
aws lambda create-function \
  --function-name $LAMBDA_NAME \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 128 \
  --environment Variables="{TABLE_NAME=$TABLE_NAME}" \
  --region $REGION

# Expected output:
# {
#   "FunctionName": "handson-api-handler",
#   "Runtime": "python3.11",
#   "State": "Pending"
# }

# Wait for Lambda to become Active
aws lambda wait function-active --function-name $LAMBDA_NAME
echo "✅ Lambda function deployed"

LAMBDA_ARN=$(aws lambda get-function \
  --function-name $LAMBDA_NAME \
  --query Configuration.FunctionArn --output text)
echo "Lambda ARN: $LAMBDA_ARN"

# ── 5. Create HTTP API Gateway ────────────────────────────────────────────────
API_ID=$(aws apigatewayv2 create-api \
  --name $API_NAME \
  --protocol-type HTTP \
  --target $LAMBDA_ARN \
  --query ApiId --output text)

echo "API ID: $API_ID"

# Get Invoke URL
API_URL=$(aws apigatewayv2 get-api \
  --api-id $API_ID \
  --query ApiEndpoint --output text)

echo "✅ API URL: $API_URL"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name $LAMBDA_NAME \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"

echo "✅ All resources created successfully!"
echo "API URL: $API_URL"
```

---

## 7. Code Deep Dive

**`src/handler.py` — Key Sections Explained:**

```python
# Line 1-15: Imports and table setup
TABLE_NAME = os.environ["TABLE_NAME"]  # Never hardcode — use env vars
dynamodb = boto3.resource("dynamodb")  # boto3 resource = high-level ORM-like API
table = dynamodb.Table(TABLE_NAME)     # Table object for operations
```

```python
# handler() function — the Lambda entry point
# event: contains HTTP method, path, body, headers
# context: Lambda runtime info (timeout remaining, request ID, etc.)
def handler(event: dict, context) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path   = event.get("rawPath", "")
    # API Gateway HTTP API v2 puts method inside requestContext.http.method
    # REST API v1 puts method in event["httpMethod"] — different structure!
```

```python
# DynamoDB write — create_item()
table.put_item(Item={
    "id":         str(uuid.uuid4()),  # Generate unique ID
    "name":       body["name"],
    "created_at": datetime.now(timezone.utc).isoformat(),  # Always UTC
})
# put_item() creates OR overwrites — no duplicate protection by default
```

```python
# DynamoDB update — update_item()
expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
# Why #k (ExpressionAttributeNames)?
# Because "name", "status" etc. are reserved words in DynamoDB
# #k is a placeholder that maps to the actual attribute name
# This prevents "ValidationException: reserved keyword" errors
```

**Common Syntax Mistakes:**

| Mistake | Correct |
|---------|---------|
| `event["httpMethod"]` | `event["requestContext"]["http"]["method"]` (HTTP API v2) |
| Hardcoding table name | Use `os.environ["TABLE_NAME"]` |
| `json.dumps(Decimal(...))` | Add `default=str` to handle DynamoDB Decimal type |
| Using `put_item` to update | Use `update_item` with UpdateExpression |

**Debugging Tips:**
- Add `print(f"Event: {json.dumps(event)}")` at the top of handler() to see full event structure
- Check CloudWatch Logs → `/aws/lambda/handson-api-handler` for all print() output
- DynamoDB `ClientError` codes: `ResourceNotFoundException` = table doesn't exist, `ValidationException` = bad expression syntax

---

## 8. Verification & Validation

```bash
# Get API URL (from terraform output or console)
API_URL="https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com"

# ── Test all endpoints ────────────────────────────────────────────────────────

# 1. Create two items
ID1=$(curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget A","description":"Blue widget"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created: $ID1"

ID2=$(curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget B","description":"Red widget"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created: $ID2"

# 2. List all items (should show 2)
curl -s $API_URL/items | python3 -m json.tool

# 3. Get specific item
curl -s $API_URL/items/$ID1 | python3 -m json.tool

# 4. Update item
curl -s -X PUT $API_URL/items/$ID1 \
  -H "Content-Type: application/json" \
  -d '{"description":"Updated blue widget"}' | python3 -m json.tool

# 5. Delete item
curl -s -X DELETE $API_URL/items/$ID1 | python3 -m json.tool

# 6. Verify 404 after delete
curl -s $API_URL/items/$ID1 | python3 -m json.tool
# Expected: {"error": "Item ... not found"} with status 404

# 7. Verify DynamoDB directly
aws dynamodb scan \
  --table-name handson-api-items \
  --query "Items[*].{id:id.S,name:name.S}"
```

**Console Verification:**

| Resource | Where to Check | Expected State |
|----------|---------------|---------------|
| API Gateway | API Gateway → APIs | `handson-rest-api`, Protocol = HTTP |
| Lambda | Lambda → Functions | `handson-api-handler`, State = Active |
| Lambda Trigger | Lambda → Configuration → Triggers | API Gateway trigger shown |
| DynamoDB | DynamoDB → Tables | `handson-api-items`, Status = Active |
| Log Group | CloudWatch → Log Groups | `/aws/lambda/handson-api-handler` exists |

**📸 Screenshot Guidance:**
- Before: Empty DynamoDB table
- During: Terminal showing POST returning 201 with item ID
- After: DynamoDB table showing created items
- Validation: All CRUD responses with correct status codes
- Error: 404 response for deleted item

---

## 9. Observations & Learning Notes

**What to observe during execution:**

1. **Cold start:** The first Lambda invocation after ~15 min idle takes 200-500ms longer. Subsequent calls are fast (< 50ms). You'll see this in CloudWatch logs as "Init Duration".

2. **DynamoDB eventual consistency:** `scan()` uses eventually consistent reads by default. If you write and immediately scan, you might not see the item for a split second. Use `ConsistentRead=True` for strongly consistent reads (costs 2x).

3. **API Gateway logs Lambda as integration:** In API Gateway → Logs, you see the Lambda function as the integration target. API Gateway is just a proxy — all logic lives in Lambda.

4. **IAM role propagation:** After creating an IAM role, there's a 10-15 second delay before Lambda can use it. This is why we add `sleep 10` in scripts.

5. **DynamoDB scan vs query:** `scan()` reads every item (expensive at scale). For production, always use `query()` with a partition key. Our API uses scan only for list-all, which is acceptable for small tables.

**Billing observations:**
- First invocation after deployment: Lambda bills for "init duration" separately
- DynamoDB: Each `get_item` = 0.5 RCU, `put_item` = 1 WCU, `scan` = 0.5 RCU per KB scanned
- API Gateway: Billed per request after free tier

**Networking observations:**
- Lambda runs inside AWS's managed network — it has internet access by default
- No VPC needed for this project (DynamoDB has public endpoints)
- HTTPS is terminated at API Gateway — Lambda only receives the decrypted payload

---

## 10. Screenshots Guidance

| When | What to Capture | Why |
|------|----------------|-----|
| Before | DynamoDB empty table view | Baseline |
| Before | Lambda function list (empty) | Baseline |
| During Step 1 | DynamoDB table creation form | Document config |
| During Step 3 | Lambda code editor with handler.py | Validate code |
| During Step 3 | Environment variables set | Validate config |
| During Step 4 | API Gateway routes configured | Document all 5 routes |
| After | API Gateway Invoke URL | Save for testing |
| After | POST /items returning 201 response | Prove it works |
| After | GET /items showing items list | Prove reads work |
| After | 404 response for deleted item | Prove delete works |
| After | Lambda CloudWatch log showing execution | Prove observability |
| After | DynamoDB console showing items | Prove data persisted |

---

## 11. Cleanup Steps

**AWS Console Cleanup:**
1. **API Gateway:** API Gateway → APIs → Select `handson-rest-api` → Actions → Delete
2. **Lambda:** Lambda → Functions → Select `handson-api-handler` → Actions → Delete
3. **DynamoDB:** DynamoDB → Tables → Select `handson-api-items` → Delete table
4. **IAM Role:** IAM → Roles → Select `handson-lambda-exec-role` → Delete
5. **CloudWatch:** CloudWatch → Log Groups → `/aws/lambda/handson-api-handler` → Delete

**AWS CLI Cleanup:**
```bash
# Delete in reverse dependency order
aws apigatewayv2 delete-api --api-id $API_ID
aws lambda delete-function --function-name handson-api-handler
aws dynamodb delete-table --table-name handson-api-items
aws iam detach-role-policy --role-name handson-lambda-exec-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name handson-lambda-exec-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam delete-role --role-name handson-lambda-exec-role
aws logs delete-log-group --log-group-name /aws/lambda/handson-api-handler

echo "✅ All resources deleted"
```

**Terraform Cleanup (if using Terraform):**
```bash
cd terraform
terraform destroy -auto-approve
# Expected: All resources destroyed
```

**Cost Verification:**
```bash
# Check for any remaining resources
aws lambda list-functions --query "Functions[?starts_with(FunctionName,'handson')]"
aws dynamodb list-tables --query "TableNames[?starts_with(@,'handson')]"
aws apigatewayv2 get-apis --query "Items[?Name=='handson-rest-api']"
```

---

## 12. Estimated AWS Cost

| Resource | Free Tier | After Free Tier |
|----------|-----------|----------------|
| Lambda | 1M requests + 400K GB-s/month **forever** | $0.20/million requests |
| API Gateway HTTP API | 1M calls/month for 12 months | ~$1/million |
| DynamoDB | 25 GB + 25 RCU/WCU **forever** | $0.25/GB/month |
| CloudWatch Logs | 5 GB ingestion free | $0.50/GB |
| **Total for lab (100K requests)** | **$0** | ~$0.10/month |

> ✅ **Free Tier Eligible:** This entire project runs within AWS Free Tier for typical lab usage (< 1M requests/month, < 400K GB-seconds Lambda compute).

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
