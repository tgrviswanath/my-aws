# Project 4.3 — URL Shortener
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** Serverless URL Shortener with DynamoDB TTL & Atomic Counters

**Business / Problem Statement:**
Long URLs are hard to share, especially in SMS, printed materials, or tweets. A URL shortener takes a long URL, assigns a short code, and redirects visitors to the original. This project builds a production-quality serverless URL shortener using DynamoDB's advanced features: TTL for automatic link expiry and atomic counters for click tracking. Companies like Bitly and TinyURL use this exact architecture pattern.

**Learning Objectives:**
- Use DynamoDB TTL to automatically expire records without any cron job
- Implement atomic counters using DynamoDB's `ADD` expression (safe for concurrent writes)
- Return HTTP 302 redirects directly from Lambda via API Gateway
- Understand DynamoDB conditional writes to prevent duplicate short codes
- Practice DynamoDB single-table design patterns

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| API Gateway (HTTP API) | Receives shorten/redirect/stats requests |
| Lambda (handler.py) | Shorten URLs, redirect, serve stats |
| DynamoDB | Stores URL mappings with TTL and click counter |

**Service Interaction Flow:**
```
POST /shorten {"url": "https://long-url.com"}
    → Lambda generates random 6-char code
    → Stores in DynamoDB with TTL (+30 days)
    → Returns: {"short_url": "https://api.../abc123"}

GET /{code}
    → Lambda looks up code in DynamoDB
    → Atomically increments click counter (ADD clicks 1)
    → Returns 302 redirect to original URL

GET /stats/{code}
    → Lambda returns: {code, original_url, clicks, created_at}
```

**DynamoDB Table Design:**
```
Table: handson-url-shortener-urls
Primary Key: code (String)   ← "abc123"

Item:
{
  "code":         "abc123",
  "original_url": "https://very-long-url.com/page?param=value",
  "created_at":   "2024-01-15T10:00:00Z",
  "clicks":       42,
  "ttl":          1708000000   ← Unix timestamp; DynamoDB auto-deletes after this
}
```

**Best Practices Followed:**
- 302 (temporary) redirect instead of 301 (permanent) — ensures clicks are always tracked
- Atomic counter using `ADD clicks 1` — safe for concurrent requests
- Collision detection using `attribute_not_exists(code)` conditional write
- TTL for automatic cleanup — no cron jobs or Lambda cleanup functions needed
- `Cache-Control: no-cache` on redirects — forces every visit to go through Lambda

---

## 3. Prerequisites

Same as Project 4.1. Additionally:
- `python3 -c "from PIL import Image"` — NOT needed (that's project 4.4)
- Understand Unix timestamps: `python3 -c "import time; print(int(time.time()))"`

---

## 4. Project Folder Structure

```
project_4.3_url_shortener/
│
├── README.md               ← DynamoDB design, business logic, lessons learned
├── GUIDE.md                ← This file
├── steps.md                ← Deploy, shorten, redirect, stats test commands
├── verify.md               ← Verification: TTL check, atomic counter test
├── cost_estimate.md        ← $0 (all free tier)
│
├── src/
│   └── handler.py          ← Shorten, redirect, stats — all in one Lambda
│
├── docs/
│   └── architecture.md     ← Collision avoidance pattern, TTL explanation
│
└── terraform/
    └── main.tf             ← API Gateway, Lambda, DynamoDB with TTL enabled
```

---

## 5. Project Input & Output

**INPUT:**
```
POST /shorten
{"url": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}

GET /aB3xY9         ← Short code from previous response

GET /stats/aB3xY9   ← Get click stats
```

**OUTPUT:**
```
POST /shorten → 201
{
  "short_url":    "https://api.../aB3xY9",
  "code":         "aB3xY9",
  "original_url": "https://docs.aws.amazon.com/lambda/...",
  "expires_days": 30
}

GET /aB3xY9 → 302 Redirect
HTTP/2 302
location: https://docs.aws.amazon.com/lambda/...
cache-control: no-cache

GET /stats/aB3xY9 → 200
{
  "code":         "aB3xY9",
  "short_url":    "https://api.../aB3xY9",
  "original_url": "https://docs.aws.amazon.com/lambda/...",
  "clicks":       5,
  "created_at":   "2024-01-15T10:00:00Z"
}

GET /nonexistent → 404
{"error": "Short URL 'nonexistent' not found or expired"}

POST /shorten (missing url) → 400
{"error": "Field 'url' is required"}
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create DynamoDB Table with TTL

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`, `dynamodb:UpdateTimeToLive`
- ✅ Region: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb)
2. Click **Create table**

**Step 1.2: Configure Table**

| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-url-shortener-urls` | Descriptive name |
| Partition key | `code` | Type: **String** — the short code |
| Billing mode | **On-demand** | Pay per request |

Click **Create table** and wait for Active status.

**Step 1.3: Enable TTL**

**Decision Point 1:** Why TTL?

| Option | Approach | For This Project |
|--------|----------|-----------------|
| Manual cleanup | Lambda cron job to delete old items | ❌ Complex, adds cost |
| DynamoDB TTL | DynamoDB auto-deletes items after Unix timestamp | ✅ Free, zero maintenance |

1. Click on table `handson-url-shortener-urls`
2. Go to **Additional settings** tab
3. Find **Time to Live (TTL)** section → Click **Enable**
4. TTL attribute name: `ttl`
5. Click **Enable TTL**

**📸 Screenshot:** DynamoDB table Additional settings showing TTL enabled with attribute `ttl`

**Step 1.4: Validate**

**Expected Outcome:** TTL status shows **Enabled**, attribute = `ttl`

> **What TTL does internally:** DynamoDB runs a background process that scans for items where `ttl < current_unix_timestamp`. Those items are deleted for free — no Lambda, no cron, no cost.

---

#### Step 2 — Deploy Lambda Function

Same process as Project 4.1 Step 3. Key differences:

| Setting | Value |
|---------|-------|
| Function name | `handson-url-shortener-handler` |
| Handler | `handler.handler` |
| Code | Paste `src/handler.py` |

**Environment variables:**

| Key | Value |
|-----|-------|
| `TABLE_NAME` | `handson-url-shortener-urls` |
| `BASE_URL` | `https://[YOUR_API_ID].execute-api.us-east-1.amazonaws.com` (set after Step 3) |
| `TTL_DAYS` | `30` |

> **Note:** `BASE_URL` cannot be set until after the API is created. Create a placeholder and update it after Step 3.

---

#### Step 3 — Create API Gateway

Routes needed:

| Method | Path | Notes |
|--------|------|-------|
| POST | `/shorten` | Create short URL |
| GET | `/{code}` | Redirect (302) |
| GET | `/stats/{code}` | View click stats |

> **Routing conflict:** Both `/stats/{code}` and `/{code}` use a path parameter. API Gateway matches `/stats/{code}` as a more specific route. This works correctly.

After creating the API, copy the Invoke URL and update Lambda's `BASE_URL` environment variable.

---

### METHOD B — AWS CLI Method

```bash
# ── 1. Create DynamoDB table ──────────────────────────────────────────────────
aws dynamodb create-table \
  --table-name handson-url-shortener-urls \
  --attribute-definitions AttributeName=code,AttributeType=S \
  --key-schema AttributeName=code,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb wait table-exists --table-name handson-url-shortener-urls

# ── 2. Enable TTL ─────────────────────────────────────────────────────────────
aws dynamodb update-time-to-live \
  --table-name handson-url-shortener-urls \
  --time-to-live-specification "Enabled=true,AttributeName=ttl"

# Verify TTL enabled
aws dynamodb describe-time-to-live \
  --table-name handson-url-shortener-urls
# Expected: {"TimeToLiveDescription": {"TimeToLiveStatus": "ENABLED", "AttributeName": "ttl"}}

echo "✅ DynamoDB with TTL ready"

# ── 3. Deploy Lambda ──────────────────────────────────────────────────────────
ROLE_ARN=$(aws iam get-role --role-name handson-lambda-exec-role \
  --query Role.Arn --output text)

cd src && zip ../shortener.zip handler.py && cd ..

aws lambda create-function \
  --function-name handson-url-shortener-handler \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.handler \
  --zip-file fileb://shortener.zip \
  --timeout 30 \
  --environment Variables="{TABLE_NAME=handson-url-shortener-urls,BASE_URL=placeholder,TTL_DAYS=30}"

aws lambda wait function-active --function-name handson-url-shortener-handler
echo "✅ Lambda deployed"

LAMBDA_ARN=$(aws lambda get-function --function-name handson-url-shortener-handler \
  --query Configuration.FunctionArn --output text)

# ── 4. Create API Gateway ─────────────────────────────────────────────────────
API_ID=$(aws apigatewayv2 create-api \
  --name handson-url-shortener-api \
  --protocol-type HTTP \
  --query ApiId --output text)

INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $LAMBDA_ARN \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

# Create all routes
for ROUTE in "POST /shorten" "GET /{code}" "GET /stats/{code}"; do
  aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "$ROUTE" \
    --target "integrations/$INT_ID"
done

aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --auto-deploy

API_URL=$(aws apigatewayv2 get-api --api-id $API_ID \
  --query ApiEndpoint --output text)

# Update Lambda with actual BASE_URL
aws lambda update-function-configuration \
  --function-name handson-url-shortener-handler \
  --environment Variables="{TABLE_NAME=handson-url-shortener-urls,BASE_URL=$API_URL,TTL_DAYS=30}"

# Grant API Gateway invoke permission
aws lambda add-permission \
  --function-name handson-url-shortener-handler \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"

echo "✅ URL Shortener ready at: $API_URL"
```

---

## 7. Code Deep Dive

**`src/handler.py` — Key Sections:**

```python
# Collision-safe code generation using conditional write
table.put_item(
    Item={
        "code":         code,
        "original_url": original_url,
        "ttl":          int(time.time()) + (TTL_DAYS * 86400),  # Unix timestamp
        "clicks":       0,
    },
    ConditionExpression="attribute_not_exists(code)",  # FAIL if code already exists
)
# If code exists → ConditionalCheckFailedException → catch it → try new code
# This is the CORRECT way to avoid code collisions in DynamoDB
# Do NOT read-then-write (race condition between read and write)
```

```python
# Atomic counter — safe for concurrent requests
table.update_item(
    Key={"code": code},
    UpdateExpression="ADD clicks :one",
    ExpressionAttributeValues={":one": 1},
)
# ADD is atomic in DynamoDB — no race condition even if 100 users click simultaneously
# DO NOT do: item["clicks"] += 1; table.put_item(item)  ← this has a race condition
```

```python
# 302 Redirect — notice there's NO "body" key
return {
    "statusCode": 302,
    "headers": {
        "Location": item["original_url"],    # Where browser goes
        "Cache-Control": "no-cache",         # IMPORTANT: prevents browser caching
    },
}
# If you used 301 instead: browser caches the redirect and never calls your API again
# → clicks would not be tracked after the first visit
```

```python
# TTL calculation
"ttl": int(time.time()) + (TTL_DAYS * 86400)
# time.time()   = current Unix timestamp (seconds since epoch)
# 86400         = seconds in one day
# TTL_DAYS * 86400 = TTL_DAYS days from now in seconds
# DynamoDB compares item's ttl against current time — auto-deletes when expired
```

**Common Mistakes:**

| Mistake | Fix |
|---------|-----|
| Using 301 redirect | Use 302 — 301 is cached by browser, no click tracking |
| `clicks += 1` (read-modify-write) | Use `ADD clicks :one` — atomic |
| Not setting `Cache-Control: no-cache` | Stats won't track repeat visitors |
| Using `attribute_exists` in condition | Use `attribute_not_exists` to detect collision |

---

## 8. Verification & Validation

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"
TABLE="handson-url-shortener-urls"

# 1. Shorten a URL
RESULT=$(curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}')
echo $RESULT | python3 -m json.tool
CODE=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")
echo "Code: $CODE"

# 2. Test redirect — check 302 and Location header
curl -sI $API_URL/$CODE | head -5
# Expected: HTTP/2 302
# Expected: location: https://docs.aws.amazon.com/...

# 3. Follow redirect (should land on actual page)
curl -sL -o /dev/null -w "%{url_effective}\n" $API_URL/$CODE
# Expected: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html

# 4. Check stats (1 click counted)
curl -s $API_URL/stats/$CODE | python3 -m json.tool
# Expected: "clicks": 1

# 5. Click 4 more times and verify counter increments
for i in 1 2 3 4; do curl -sI $API_URL/$CODE > /dev/null; done
curl -s $API_URL/stats/$CODE | python3 -c "import sys,json; print('Clicks:', json.load(sys.stdin)['clicks'])"
# Expected: Clicks: 5

# 6. Verify DynamoDB item with TTL
aws dynamodb get-item \
  --table-name $TABLE \
  --key "{\"code\":{\"S\":\"$CODE\"}}"
# Check ttl attribute is set

# 7. Verify TTL is ~30 days out
python3 -c "
import time, datetime
ttl = $(aws dynamodb get-item --table-name $TABLE \
  --key '{\"code\":{\"S\":\"$CODE\"}}' \
  --query 'Item.ttl.N' --output text)
exp = datetime.datetime.fromtimestamp(int(ttl))
days = (exp - datetime.datetime.now()).days
print(f'Expires in {days} days: {exp}')
"
# Expected: Expires in 29 days: 2024-02-14 ...

# 8. Test 404 for non-existent code
curl -s $API_URL/nonexistent | python3 -m json.tool
# Expected: {"error": "Short URL 'nonexistent' not found or expired"} with 404
```

**Console Verification:**

| Resource | Where to Check | Expected State |
|----------|---------------|---------------|
| DynamoDB Table | DynamoDB → Tables | `handson-url-shortener-urls` Active |
| TTL Enabled | Table → Additional settings | TTL = Enabled, attribute = `ttl` |
| DynamoDB Items | Table → Explore items | Items with `code`, `original_url`, `ttl`, `clicks` |
| Lambda | Lambda → Functions | `handson-url-shortener-handler` Active |
| API Gateway | API Gateway | 3 routes: POST /shorten, GET /{code}, GET /stats/{code} |

---

## 9. Observations & Learning Notes

1. **TTL is not instant:** DynamoDB TTL deletion is eventually consistent — items may persist up to 48 hours after the TTL timestamp passes. Don't rely on TTL for time-critical expiry.

2. **TTL doesn't count as capacity consumption:** TTL deletes are free — they don't consume any WCU.

3. **302 vs 301 redirect difference:** Open browser DevTools → Network tab. With 302, every visit calls the API. With 301, the browser caches the redirect and never calls the API again after the first visit — clicks would stop counting.

4. **Collision probability:** With 6 alphanumeric characters (62^6 = 56 billion possible codes), collisions are extremely rare but possible. The retry loop handles up to 5 collisions before giving up.

5. **DynamoDB conditional writes:** `attribute_not_exists(code)` is DynamoDB's way of doing an atomic "check and insert" — equivalent to SQL's `INSERT ... WHERE NOT EXISTS`. This prevents race conditions.

---

## 10. Screenshots Guidance

| When | What to Capture |
|------|----------------|
| After Step 1.3 | DynamoDB Additional settings showing TTL Enabled |
| After deploy | Lambda function with BASE_URL and TABLE_NAME env vars |
| Testing | POST /shorten returning 201 with short_url |
| Testing | `curl -I` showing HTTP/2 302 and location header |
| Testing | GET /stats showing click count incrementing |
| DynamoDB | Explore items showing code, ttl, clicks columns |
| DynamoDB | Item detail showing TTL timestamp |

---

## 11. Cleanup Steps

```bash
aws apigatewayv2 delete-api --api-id $API_ID
aws lambda delete-function --function-name handson-url-shortener-handler
aws dynamodb delete-table --table-name handson-url-shortener-urls
aws logs delete-log-group --log-group-name /aws/lambda/handson-url-shortener-handler
echo "✅ URL Shortener resources deleted"
```

---

## 12. Estimated AWS Cost

| Resource | Cost |
|----------|------|
| Lambda | $0 (free tier) |
| API Gateway | $0 (free tier) |
| DynamoDB | $0 (free tier) |
| **Total** | **$0** |

> ✅ **Fully within AWS Free Tier.** DynamoDB TTL deletion is free. This project costs $0 at lab scale.

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
