# Project 4.3 — URL Shortener
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create DynamoDB Table with TTL

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`, `dynamodb:UpdateTimeToLive`
- ✅ Services enabled: Amazon DynamoDB
- ✅ Region availability: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb)
2. **Expected View:** DynamoDB dashboard with "Create table" button
3. Click **Create table**

**Step 1.2: Configure Table**

| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-url-shortener-urls` | Contains all short URL mappings |
| Partition key | `code` | Type: **String** — the 6-char short code (e.g. `aB3xY9`) |
| Sort key | *(leave empty)* | Single-key lookup only |

Under Table settings → **Customize settings** → Capacity mode: **On-demand**

Click **Create table** → Wait for Status = **Active**

**📸 Screenshot:** DynamoDB table `handson-url-shortener-urls` Status = Active

**Step 1.3: Enable TTL**

**Decision Point 1:** Why TTL?

| Approach | Mechanism | For This Project |
|----------|-----------|-----------------|
| Manual deletion | Lambda cron job | ❌ Adds cost and complexity |
| DynamoDB TTL | Automatic — free | ✅ Use this |

1. Click on table `handson-url-shortener-urls`
2. Click **Additional settings** tab
3. Find **Time to Live (TTL)** section
4. Click **Enable**
5. TTL attribute name: `ttl`
6. Click **Enable TTL**

**Expected Outcome:** TTL status = **Enabled**, attribute name = `ttl`

**📸 Screenshot:** DynamoDB Additional settings tab showing TTL Enabled with attribute `ttl`

**Troubleshooting:**
- TTL option not visible: Refresh page — table must be Active first
- Cannot enable: Check `dynamodb:UpdateTimeToLive` permission

---

#### Step 2 — Create Lambda IAM Role

Reuse `handson-lambda-exec-role` from Project 4.1, or create fresh with:
- `AWSLambdaBasicExecutionRole`
- `AmazonDynamoDBFullAccess`

---

#### Step 3 — Deploy Lambda Function

**Step 3.1: Create Function**

Lambda Console → **Create function** → Author from scratch

| Field | Value |
|-------|-------|
| Function name | `handson-url-shortener-handler` |
| Runtime | Python 3.11 |
| Execution role | `handson-lambda-exec-role` |

**Step 3.2: Upload Code**

Paste entire content of `src/handler.py` → Click **Deploy**

**Step 3.3: Set Environment Variables**

Configuration → Environment variables → Edit → Add:

| Key | Value | Explanation |
|-----|-------|-------------|
| `TABLE_NAME` | `handson-url-shortener-urls` | DynamoDB table name |
| `BASE_URL` | `https://PLACEHOLDER` | Will update after API Gateway is created |
| `TTL_DAYS` | `30` | Links expire after 30 days |

Click **Save** → Set Timeout: 30s

**📸 Screenshot:** Lambda env vars showing TABLE_NAME, BASE_URL, TTL_DAYS

---

#### Step 4 — Create API Gateway

**Step 4.1: Create HTTP API**

API Gateway → **Create API** → **HTTP API** → **Build**

Add integration: Lambda → `handson-url-shortener-handler`

API name: `handson-url-shortener-api`

**Step 4.2: Configure Routes**

**Decision Point 1:** Route conflict concern

| Route | Note |
|-------|------|
| `POST /shorten` | Specific path — matched first |
| `GET /stats/{code}` | More specific than `/{code}` — matched correctly |
| `GET /{code}` | Catches everything else |

API Gateway matches more specific routes first, so `/stats/{code}` is matched before `/{code}`.

| Method | Path | Integration |
|--------|------|-------------|
| POST | `/shorten` | `handson-url-shortener-handler` |
| GET | `/{code}` | `handson-url-shortener-handler` |
| GET | `/stats/{code}` | `handson-url-shortener-handler` |

Stage: `$default` → Create

**Step 4.3: Update BASE_URL Environment Variable**

After API is created:
1. Copy the **Invoke URL** from API Gateway detail page
2. Go back to Lambda → `handson-url-shortener-handler` → Configuration → Environment variables → Edit
3. Update `BASE_URL` to the actual Invoke URL (remove trailing slash)
4. Click **Save**

**📸 Screenshot:** Lambda `handson-url-shortener-handler` updated BASE_URL environment variable matching the API Gateway Invoke URL

---

#### Step 5 — Test the URL Shortener

**Step 5.1: Shorten a URL**

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"

# Shorten a long URL
curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://docs.aws.amazon.com/lambda/latest/dg/welcome.html\"}"
# Expected: {"short_url": "https://.../aB3xY9", "code": "aB3xY9", "expires_days": 30}
```

**📸 Screenshot:** POST /shorten returning 201 with short_url and code

**Step 5.2: Test Redirect**

```bash
CODE="aB3xY9"   # Use your actual code

# Check redirect headers (don't follow redirect)
curl -sI $API_URL/$CODE | head -4
# Expected: HTTP/2 302
# Expected: location: https://docs.aws.amazon.com/...
```

**Decision Point 2:** Why 302 not 301?

| Redirect Type | Browser behaviour | Stats tracking | For This Project |
|--------------|------------------|----------------|-----------------|
| 301 Permanent | Browser caches it — never calls API again | ❌ After first visit, no more clicks tracked | ❌ |
| 302 Temporary | Browser calls API every time | ✅ Every visit tracked | ✅ |

**📸 Screenshot:** `curl -I` output showing `HTTP/2 302` and `location:` header

**Step 5.3: Check Click Stats**

```bash
curl -s $API_URL/stats/$CODE
# Expected: {"code": "aB3xY9", "clicks": 1, "original_url": "...", "created_at": "..."}

# Click 4 more times — verify counter increments
for i in 1 2 3 4; do curl -sI $API_URL/$CODE > /dev/null; done
curl -s $API_URL/stats/$CODE | python3 -c "import sys,json; print('Clicks:', json.load(sys.stdin)['clicks'])"
# Expected: Clicks: 5
```

**📸 Screenshot:** GET /stats showing click count incrementing

**Step 5.4: Verify DynamoDB Item**

1. DynamoDB Console → Tables → `handson-url-shortener-urls`
2. Click **Explore table items**
3. **Expected Outcome:** Item showing `code`, `original_url`, `clicks`, `ttl` attributes

**📸 Screenshot:** DynamoDB item showing all attributes including numeric `ttl` timestamp

**Step 5.5: Verify TTL Value**

```bash
python3 -c "
import datetime
ttl = 1737000000   # Replace with your item's actual ttl value from DynamoDB
exp = datetime.datetime.fromtimestamp(ttl)
print('Expires:', exp)
print('Days from now:', (exp - datetime.datetime.now()).days)
"
# Expected: ~30 days from now
```

---

#### Step 6 — Test Error Cases

```bash
# Test 404 for non-existent code
curl -s $API_URL/nonexistent
# Expected: {"error": "Short URL 'nonexistent' not found or expired"} with 404

# Test 400 for missing URL
curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d "{}"
# Expected: {"error": "Field 'url' is required"} with 400

# Test 400 for invalid URL format
curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"not-a-valid-url\"}"
# Expected: {"error": "URL must start with http:// or https://"} with 400
```

**📸 Screenshot:** 404 response for non-existent short code
