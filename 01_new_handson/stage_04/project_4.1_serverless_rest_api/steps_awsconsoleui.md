# Project 4.1 — Serverless REST API
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create DynamoDB Table

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`
- ✅ Services enabled: Amazon DynamoDB (available in all regions)
- ✅ Region availability: us-east-1 selected in top-right console selector

**Step 1.1: Navigate and Verify**
1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb)
2. **Expected View:** DynamoDB dashboard with orange "Create table" button top-right
3. **If Different:** Check region selector (top-right) is set to `us-east-1`

**Step 1.2: Make Selections**

Click **Create table**

**Decision Point 1:** Billing Mode

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Provisioned | Predictable, steady traffic | ❌ Requires capacity planning |
| On-demand | Variable/unpredictable traffic | ✅ Select this — pay per request |

**📸 Screenshot:** DynamoDB "Create table" form before filling in values

**Step 1.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-api-items` | Prefix `handson-` for easy cleanup |
| Partition key | `id` | Type: **String** — unique item identifier |
| Sort key | *(leave empty)* | Not needed — single-key lookup |

Scroll to **Table settings** → Select **Customize settings**

Under **Read/write capacity settings:**
- Capacity mode: **On-demand**

Click **Create table**

**Step 1.4: Validate Result**

**Expected Outcome:** Table status shows **Creating** → then **Active** (30–60 seconds)

**Troubleshooting:**
- `Table already exists`: Add a suffix e.g. `handson-api-items-2`
- `Access denied`: Your IAM user needs `dynamodb:CreateTable`

**📸 Screenshot:** DynamoDB table list showing `handson-api-items` Status = Active

---

#### Step 2 — Create Lambda IAM Role

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global service, no region needed)

**Step 2.1: Navigate and Verify**
1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Click **Roles** in left sidebar
3. **Expected View:** Roles list with "Create role" button

**Step 2.2: Make Selections**

Click **Create role**

**Decision Point 1:** Trusted Entity Type

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | A service (Lambda) assumes this role | ✅ Select this |
| AWS account | Cross-account access | ❌ Not needed |
| Web identity | Federated auth | ❌ Not needed |

Select **AWS service** → Under "Use case" choose **Lambda** → Click **Next**

**📸 Screenshot:** Role creation step 1 — "AWS service" and "Lambda" selected

**Step 2.3: Configure Details**

On "Add permissions" page, search and attach these two policies:

| Policy | Search for | Why |
|--------|-----------|-----|
| `AWSLambdaBasicExecutionRole` | AWSLambdaBasicExecution | Allows Lambda to write CloudWatch logs |
| `AmazonDynamoDBFullAccess` | AmazonDynamoDBFull | Allows Lambda to read/write DynamoDB |

Check both → Click **Next**

| Field | Value |
|-------|-------|
| Role name | `handson-lambda-exec-role` |
| Description | Lambda execution role for handson projects |

Click **Create role**

**Step 2.4: Validate Result**

**Expected Outcome:** Role appears in list. Click it — should show 2 attached policies.

**📸 Screenshot:** Role detail page showing AWSLambdaBasicExecutionRole + AmazonDynamoDBFullAccess

---

#### Step 3 — Create and Deploy Lambda Function

**Prerequisites Check:**
- ✅ Required permissions: `lambda:CreateFunction`
- ✅ IAM role exists: `handson-lambda-exec-role`
- ✅ DynamoDB table exists: `handson-api-items`

**Step 3.1: Navigate and Verify**
1. Go to [Lambda Console](https://console.aws.amazon.com/lambda)
2. **Expected View:** Functions list with "Create function" button
3. **If Different:** Verify us-east-1 region is selected

**Step 3.2: Make Selections**

Click **Create function**

**Decision Point 1:** Creation Method

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Author from scratch | Write your own code | ✅ Select this |
| Use a blueprint | AWS templates | ❌ We have our own code |
| Container image | Docker-based Lambda | ❌ Not needed |

**Step 3.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Function name | `handson-api-handler` | Descriptive, matches project |
| Runtime | **Python 3.11** | Matches `src/handler.py` |
| Architecture | x86_64 | Default, lowest cost |
| Execution role | **Use an existing role** | |
| Existing role | `handson-lambda-exec-role` | Role created in Step 2 |

Click **Create function**

**📸 Screenshot:** Lambda function creation form filled in

**Step 3.4: Upload Code**

1. In the function page → **Code source** section
2. Click on `lambda_function.py` in the file tree
3. **Select all existing code and delete it**
4. Open `src/handler.py` from your local machine → Copy all content → Paste it
5. Click **Deploy** (orange button top-right of editor)

**Expected Outcome:** "Changes deployed" message appears

**Step 3.5: Set Environment Variables**

1. Click **Configuration** tab → **Environment variables** → **Edit**
2. Click **Add environment variable**

| Key | Value |
|-----|-------|
| `TABLE_NAME` | `handson-api-items` |

Click **Save**

**Step 3.6: Update Timeout and Memory**

1. **Configuration** tab → **General configuration** → **Edit**

| Setting | Value | Why |
|---------|-------|-----|
| Timeout | `30` seconds | Default 3s is too short for DynamoDB calls |
| Memory | `128` MB | Sufficient for this API |

Click **Save**

**Step 3.7: Validate Result**

**Expected Outcome:** Function shows Runtime = Python 3.11, TABLE_NAME env var set, Timeout = 30s

**📸 Screenshot:** Lambda Configuration tab showing TABLE_NAME environment variable

**Troubleshooting:**
- `Deploy` button greyed out: check for Python syntax errors in the editor (red underlines)
- `InvalidParameterValueException` on save: verify role name is exactly `handson-lambda-exec-role`

---

#### Step 4 — Create API Gateway HTTP API

**Prerequisites Check:**
- ✅ Required permissions: `apigateway:POST`
- ✅ Lambda function deployed: `handson-api-handler`

**Step 4.1: Navigate and Verify**
1. Go to [API Gateway Console](https://console.aws.amazon.com/apigateway)
2. **Expected View:** API types listed — HTTP API, REST API, WebSocket API

**Step 4.2: Make Selections**

**Decision Point 1:** API Type

| Option | Cost/million | Features | For This Project |
|--------|-------------|----------|-----------------|
| HTTP API | ~$1 | Core routing, JWT auth, CORS | ✅ Use this |
| REST API | ~$3.50 | Full features, API keys, usage plans | ❌ More expensive, overkill |
| WebSocket API | Variable | Real-time bidirectional | ❌ Not needed |

Click **Build** under **HTTP API**

**Step 4.3: Configure Integrations and Routes**

1. Click **Add integration**
   - Integration type: **Lambda**
   - Region: `us-east-1`
   - Lambda function: `handson-api-handler`
2. API name: `handson-rest-api`
3. Click **Next** → Configure routes:

Click **Add route** for each endpoint:

| Method | Resource path | Integration target |
|--------|--------------|-------------------|
| GET | `/items` | handson-api-handler |
| POST | `/items` | handson-api-handler |
| GET | `/items/{id}` | handson-api-handler |
| PUT | `/items/{id}` | handson-api-handler |
| DELETE | `/items/{id}` | handson-api-handler |

**📸 Screenshot:** API Gateway routes configuration showing all 5 routes

**Step 4.4: Configure Stage**

Click **Next** → Stage name: `$default` (auto-deploy enabled) → Click **Next** → **Create**

**Step 4.5: Validate Result**

**Expected Outcome:** API created with Invoke URL like `https://abc123xyz.execute-api.us-east-1.amazonaws.com`

**📸 Screenshot:** API Gateway detail page showing Invoke URL

**Troubleshooting:**
- Routes returning 500: Check Lambda logs in CloudWatch → `/aws/lambda/handson-api-handler`
- Routes returning 403: Lambda permission for API Gateway may not have been added — check Lambda → Configuration → Resource-based policy
- Routes returning 404: Verify route path matches exactly (e.g. `/items/{id}` not `/items/:id`)

---

#### Step 5 — Test the API

**Step 5.1: Copy the Invoke URL**

From API Gateway → your API → copy the Invoke URL from the top of the page.

**Step 5.2: Run Tests from Terminal**

Open a terminal (PowerShell, Git Bash, or cmd):

```bash
# Set your API URL
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"

# Test 1: Create an item
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Test Item\", \"description\": \"Hello from console\"}"
# Expected: 201 with id, name, description, created_at

# Test 2: List all items
curl -s $API_URL/items
# Expected: {"items": [...], "count": 1}

# Test 3: Get specific item (paste the id from Test 1)
curl -s $API_URL/items/PASTE_ID_HERE

# Test 4: Update
curl -s -X PUT $API_URL/items/PASTE_ID_HERE \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"Updated!\"}"

# Test 5: Delete
curl -s -X DELETE $API_URL/items/PASTE_ID_HERE

# Test 6: Verify 404 after delete
curl -s $API_URL/items/PASTE_ID_HERE
# Expected: {"error": "Item ... not found"} with 404
```

**Step 5.3: Check CloudWatch Logs**

1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch)
2. Left sidebar → **Log groups**
3. Click `/aws/lambda/handson-api-handler`
4. Click the latest log stream
5. **Expected Outcome:** Log entries for each API call

**📸 Screenshot:** CloudWatch log stream showing Lambda invocation logs

**Step 5.4: Validate DynamoDB Data**

1. Go to DynamoDB → Tables → `handson-api-items`
2. Click **Explore table items** tab
3. **Expected Outcome:** Items created via POST are visible here

**📸 Screenshot:** DynamoDB Explore Items view showing created items

---

#### Step 6 — Verify Everything is Connected

**Step 6.1: Check Lambda Trigger**

1. Lambda → `handson-api-handler` → **Configuration** tab → **Triggers**
2. **Expected Outcome:** API Gateway trigger listed with your API name

**Decision Point 1:** If trigger is missing

| Situation | Fix |
|-----------|-----|
| Trigger not shown but API works | AWS auto-added it — no action needed |
| API returns 403 | Manually add resource-based policy via Lambda → Permissions → Add permission |

**📸 Screenshot:** Lambda Triggers tab showing API Gateway trigger

**Step 6.2: Final Architecture Check**

Verify this chain in the console:

```
API Gateway (handson-rest-api)
    → Routes: GET/POST/PUT/DELETE /items and /items/{id}
    → Integration: handson-api-handler Lambda
        → Environment: TABLE_NAME = handson-api-items
        → Role: handson-lambda-exec-role
            → Policies: AWSLambdaBasicExecutionRole + AmazonDynamoDBFullAccess
        → DynamoDB: handson-api-items (Active, On-demand)
    → CloudWatch Logs: /aws/lambda/handson-api-handler
```

**📸 Screenshot:** Final — Lambda function page showing trigger, code, and environment variables all visible
