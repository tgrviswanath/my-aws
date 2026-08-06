# Project 4.3 — URL Shortener Service

**Stage:** 04 | **Level:** Intermediate | **Est. Time:** 50 min | **Cost:** ~$0.45/month

This project builds a serverless URL shortener using Lambda, API Gateway (HTTP API), and DynamoDB.
Clients POST a long URL to `/shorten` and receive back a short URL containing a 6-character alphanumeric
code generated with Python's `secrets` module. The short code and original URL are stored in DynamoDB
with an optional TTL attribute so items auto-expire. A GET request to `/{code}` looks up the code in
DynamoDB and returns an HTTP 302 redirect to the original URL via the `Location` response header — no
HTML, just a redirect. The Lambda function handles both routes and is deployed with a proxy integration,
so it controls the exact `statusCode` and `headers` returned to the client. Collision detection on write
uses a DynamoDB conditional expression to guarantee uniqueness across 62^6 = ~56 billion possible codes.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS Lambda (Python 3.12) | Generates short codes, writes to DynamoDB, returns 302 redirects | $0.20/1M requests |
| API Gateway HTTP API | Exposes POST /shorten and GET /{code} to the internet | $1.00/1M calls |
| DynamoDB (on-demand) | Stores short code → original URL mappings with optional TTL | $0 at low volume; $1.25/WCU per million |
| IAM Role | Grants Lambda PutItem and GetItem on the URL table | Free |
| CloudWatch Logs | Lambda logs for debugging redirect failures and collision events | $0.50/GB ingested |

## Input / Output

### Input

| Parameter | Type | Where | Example |
|---|---|---|---|
| Long URL to shorten | String (JSON body) | POST /shorten request body | `{"url": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}` |
| TTL (optional) | Integer (Unix epoch) | JSON body field `expiry` | `{"url": "...", "expiry": 1735689600}` |
| Short code lookup | String (URL path) | GET /{code} path parameter | `/xK9mP2` |

### Output

| Operation | Status Code | Response / Behavior |
|---|---|---|
| POST /shorten (success) | 201 | `{"short_url": "https://abc123.execute-api.us-east-1.amazonaws.com/xK9mP2", "code": "xK9mP2"}` |
| POST /shorten (collision retry succeeded) | 201 | Same as above; collision logged, new code generated transparently |
| POST /shorten (invalid body) | 400 | `{"message": "Missing url field in request body"}` |
| GET /{code} (found) | 302 | Empty body; `Location: https://docs.aws.amazon.com/...` header set |
| GET /{code} (not found or expired) | 404 | `{"message": "Short code not found"}` |

## Architecture

```
Client
  |
  |  POST /shorten  {"url": "https://very-long-url.com/..."}
  |  GET /xK9mP2
  v
+----------------------------------+
|   API Gateway HTTP API           |
|   POST /shorten                  |
|   GET  /{code}                   |
+----------------------------------+
           | Lambda Proxy Integration
           v
+----------------------------------+
|   Lambda Function (Python 3.12)  |
|                                  |
|   POST branch:                   |
|   - Parse URL from body          |
|   - Generate 6-char code         |
|     (secrets.choice, base62)     |
|   - ConditionalPutItem to DDB    |
|   - Return 201 + short_url       |
|                                  |
|   GET branch:                    |
|   - GetItem by code from path    |
|   - Return 302 + Location header |
+----------------------------------+
           | boto3
           v
+----------------------------------+
|   DynamoDB Table: url-table      |
|   PK: code (String, 6 chars)     |
|   Attr: original_url (String)    |
|   Attr: expiry (Number, TTL)     |
+----------------------------------+
```

## Quick Start

```cmd
REM 1. Create DynamoDB table with TTL enabled
aws dynamodb create-table ^
  --table-name url-table ^
  --attribute-definitions AttributeName=code,AttributeType=S ^
  --key-schema AttributeName=code,KeyType=HASH ^
  --billing-mode PAY_PER_REQUEST ^
  --region us-east-1

REM 2. Enable TTL on the "expiry" attribute
aws dynamodb update-time-to-live ^
  --table-name url-table ^
  --time-to-live-specification "Enabled=true,AttributeName=expiry" ^
  --region us-east-1

REM 3. Create IAM role (reuse lambda-dynamo-role from 4.1 if available)
REM    Or create a new scoped role with PutItem and GetItem only
aws iam create-role ^
  --role-name lambda-urlshortener-role ^
  --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
aws iam attach-role-policy --role-name lambda-urlshortener-role ^
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name lambda-urlshortener-role ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

REM 4. Package and deploy the Lambda function
powershell Compress-Archive -Path lambda_function.py -DestinationPath shortener.zip -Force
aws lambda create-function ^
  --function-name url-shortener ^
  --runtime python3.12 ^
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-urlshortener-role ^
  --handler lambda_function.lambda_handler ^
  --zip-file fileb://shortener.zip ^
  --environment Variables={TABLE_NAME=url-table,BASE_URL=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com} ^
  --region us-east-1

REM 5. Create HTTP API connected to Lambda
aws apigatewayv2 create-api ^
  --name url-shortener-api ^
  --protocol-type HTTP ^
  --target arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:url-shortener ^
  --region us-east-1

REM 6. Test: shorten a URL
curl -X POST https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/shorten ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://docs.aws.amazon.com/lambda/latest/dg/welcome.html\"}"

REM 7. Test: follow the redirect (use -L to follow, or -v to see 302 Location header)
curl -v https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/xK9mP2
```

## Data Flow

1. Client POSTs `{"url": "https://original-long-url.com"}` to `POST /shorten`.
2. API Gateway proxies the request as a JSON event to the Lambda function.
3. Lambda parses the JSON body and extracts the `url` field.
4. Lambda generates a 6-character code using `secrets.choice()` over the 62-character alphabet `[A-Za-z0-9]`.
5. Lambda calls `dynamodb.put_item()` with `ConditionExpression=attribute_not_exists(code)` to prevent overwriting an existing code — if a collision occurs, a new code is generated and retried.
6. DynamoDB stores the item: `{code: "xK9mP2", original_url: "https://...", expiry: 1735689600}`.
7. Lambda returns HTTP 201 with body `{"short_url": "https://api.../xK9mP2", "code": "xK9mP2"}`.
8. Client later sends `GET /xK9mP2` to API Gateway.
9. Lambda calls `dynamodb.get_item(Key={"code": "xK9mP2"})` and retrieves the original URL.
10. Lambda returns HTTP 302 with `Location: https://original-long-url.com` header — the browser follows the redirect automatically.

## Project Files

| File | Description |
|---|---|
| `lambda_function.py` | Lambda handler — POST /shorten generates code + writes DynamoDB; GET /{code} reads and returns 302 |
| `shortener.zip` | Deployment package created from `lambda_function.py` |
| `test_requests.sh` | Sample curl commands to shorten a URL and test the redirect flow |
| `README.md` | This file |

## Lessons Learned

- API Gateway proxy integration passes the Lambda response verbatim — `statusCode` must be an integer, `headers` a dict, and `body` a JSON string; forgetting `json.dumps()` on the body returns a 502.
- HTTP 302 (temporary redirect) is correct over 301 (permanent) — browsers cache 301 permanently, so if the short code ever points to a new destination, users with a cached 301 will never see the update.
- DynamoDB TTL (`expiry` as a Unix epoch number) auto-deletes expired items within 48 hours at no cost — no scheduled cleanup Lambda or cron job needed to implement link expiration.
- Short codes from a 62-char alphabet at 6 characters give 62^6 ≈ 56 billion combinations — collisions are rare, but `ConditionExpression=attribute_not_exists(code)` on `PutItem` is still required for correctness.
- `ConditionalCheckFailedException` on `PutItem` confirms a collision — catch it, generate a new code, and retry; never surface it as a 500 to the caller.
- The `BASE_URL` env var holds the API Gateway invoke URL for building the short URL in the response — hardcoding it breaks on every redeployment or stage promotion.
- Returning an empty body on a 302 is correct — some HTTP clients reject redirects with a non-empty body, so `"body": ""` maximises compatibility.
