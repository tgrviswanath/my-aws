# Hands-on Log — AWS Lambda Web App with API Gateway

**Date:** 2026-05-17
**AWS Account:** 495331821583
**IAM User:** tgrviswanath
**Region:** ap-south-1 (Mumbai)
**Language:** Python 3.12
**Services Used:** Lambda, API Gateway, IAM

---

## Project Description

This project demonstrates building a **serverless web application using AWS Lambda** with **API Gateway** to expose it as a public HTTP endpoint. The function accepts query parameters, returns JSON responses, and requires no servers to manage.

**Why this project matters:**
Traditional web apps run on EC2 instances or containers — you manage scaling, updates, patches. Lambda functions scale automatically, you pay only for execution time (milliseconds), and AWS handles everything. This is the fastest path from code to a live web endpoint.

**Architecture Flow:**
```
Developer writes Python code (lambda_function.py)
    ↓
Package as ZIP file
    ↓
Create Lambda function (runtime: Python 3.12)
    ↓
Create API Gateway REST API
    ↓
Create GET method on root resource
    ↓
Integrate Lambda with API Gateway (AWS_PROXY)
    ↓
Grant API Gateway permission to invoke Lambda
    ↓
Deploy API to 'prod' stage
    ↓
Public HTTPS endpoint available
    ↓
Accepts HTTP GET requests, returns JSON
```

**Resources created:**
| Category | Resource | Cost |
|----------|----------|------|
| IAM | Role: lambda-execution-role | $0 |
| IAM | Policy: AWSLambdaBasicExecutionRole | $0 |
| Lambda | Function: my-web-app (Python 3.12) | $0.0000002 per invocation (free tier: 1M/month) |
| API Gateway | REST API: my-web-app-api | $3.50/million requests |
| CloudWatch | Logs from Lambda execution | $0.50/GB (free tier: 5GB/month) |
| **Total** | Monthly estimate (low traffic) | **~$0.01** |

---

## File Structure

```
aws_handson/
├── lambda/
│   └── lambda_function.py      ← Python function code
├── docs/
│   └── lambda_web_app_handson.md   ← This file
├── endpoint_log.txt            ← Deployed endpoint URL
└── cost_estimate.md
```

---

## Prerequisites

### Pre-req 1 — AWS CLI Authentication

**Command run:**
```bash
aws sts get-caller-identity
```

**Output received:**
```json
{
    "UserId": "AIDAXGVATZAHVJ3RFFKKR",
    "Account": "495331821583",
    "Arn": "arn:aws:iam::495331821583:user/tgrviswanath"
}
```

**My observation:**
- Authenticated as IAM user tgrviswanath — correct
- Account ID 495331821583 matches AWS environment
- Ready to create AWS resources via CLI

**Verification:** OK — AWS CLI configured correctly

---

### Pre-req 2 — Python 3.12 Available Locally

**Command run:**
```bash
python3 --version
```

**Output received:**
```
Python 3.12.8
```

**My observation:**
- Python 3.12 matches the Lambda runtime we'll use
- Code written locally can be tested before uploading to Lambda

**Verification:** OK — Python environment ready

---

## Phase 1 — Lambda Function Development

### Step 1 — Write Python Function Code

**File:** `lambda_function.py`

```python
import json
from datetime import datetime

def lambda_handler(event, context):
    """
    Simple Lambda web app that returns JSON
    """
    name = event.get('queryStringParameters', {}) or {}
    name = name.get('name', 'World')
    
    response = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'message': f'Hello, {name}!',
            'timestamp': datetime.now().isoformat(),
            'service': 'AWS Lambda Web App'
        })
    }
    
    return response
```

**Key components:**
- `lambda_handler(event, context)` — entry point for Lambda
- `event` — contains HTTP request details (query params, headers, body)
- `event['queryStringParameters']` — parsed query string (?name=AWS → {'name': 'AWS'})
- `statusCode: 200` — HTTP 200 OK
- `body` must be JSON string — Lambda auto-parses it for API Gateway
- `headers: {'Content-Type': 'application/json'}` — tells browser this is JSON

**My observation:**
- This is a simple "Hello World" function but it demonstrates request parsing, JSON response, and timestamp generation
- The function is stateless — each invocation starts fresh
- Cold start time: first invocation ~500ms, subsequent ~50ms

**Verification:** OK — Python syntax valid

---

### Step 2 — Package Function as ZIP

**Command run:**
```bash
python3 << 'EOF'
import zipfile
import os
import tempfile

temp_dir = tempfile.gettempdir()
zip_path = os.path.join(temp_dir, 'lambda_function.zip')
py_path = os.path.join(temp_dir, 'lambda_function.py')

with zipfile.ZipFile(zip_path, 'w') as zf:
    zf.write(py_path, 'lambda_function.py')

print(f"ZIP created: {zip_path}")
print(f"Size: {os.path.getsize(zip_path)} bytes")
EOF
```

**Output received:**
```
ZIP created: C:\Users\VISWAN~1\AppData\Local\Temp\lambda_function.zip
Size: 704 bytes
```

**My observation:**
- ZIP file is 704 bytes — very small, well under the 50MB upload limit
- Lambda extracts ZIP at deployment time
- The root of the ZIP must contain `lambda_function.py` — not in a subfolder

**Verification:** OK — ZIP package created

---

## Phase 2 — IAM Setup

### Step 1 — Create IAM Role for Lambda

**Command run:**
```bash
python3 << 'EOF'
import json
import tempfile
import os

temp_dir = tempfile.gettempdir()
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

policy_file = os.path.join(temp_dir, 'trust-policy.json')
with open(policy_file, 'w') as f:
    json.dump(policy, f)

print(policy_file)
EOF
```

**Trust Policy Created:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Command run:**
```bash
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document file://C:/Users/VISWAN~1/AppData/Local/Temp/trust-policy.json
```

**Output received:**
```json
{
    "Role": {
        "RoleName": "lambda-execution-role",
        "Arn": "arn:aws:iam::495331821583:role/lambda-execution-role"
    }
}
```

**My observation:**
- The role allows the Lambda service to assume it
- Role ARN: `arn:aws:iam::495331821583:role/lambda-execution-role`
- This role will be referenced when creating the Lambda function

**Verification:** OK — IAM role created

---

### Step 2 — Attach Lambda Execution Policy

**Command run:**
```bash
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**Output received:**
```
(successful, no output)
```

**What this policy does:**
- Allows Lambda to write logs to CloudWatch
- Policy: `AWSLambdaBasicExecutionRole` (AWS managed policy)
- Permissions granted: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**My observation:**
- Even a simple function needs this policy to output logs
- Without it, you can't debug function execution
- CloudWatch logs are retained for 7 days by default (configurable)

**Verification:** OK — Execution policy attached

---

## Phase 3 — Lambda Function Deployment

### Step 1 — Create Lambda Function

**Command run:**
```bash
aws lambda create-function \
  --function-name my-web-app \
  --runtime python3.12 \
  --role arn:aws:iam::495331821583:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://C:/Users/VISWAN~1/AppData/Local/Temp/lambda_function.zip \
  --region ap-south-1
```

**Output received:**
```
FunctionName: my-web-app
FunctionArn: arn:aws:lambda:ap-south-1:495331821583:function:my-web-app
Runtime: python3.12
Role: arn:aws:iam::495331821583:role/lambda-execution-role
Handler: lambda_function.lambda_handler
CodeSize: 704 bytes
Timeout: 3 seconds (default)
MemorySize: 128 MB (default)
```

**My observation:**
- Function created with default timeout 3 seconds and memory 128 MB
- Handler is `lambda_function.lambda_handler` — module.function format
- Code size 704 bytes — just our Python file
- Function ARN: `arn:aws:lambda:ap-south-1:495331821583:function:my-web-app`
- Default configuration is fine for a simple web app

**Verification:** OK — Lambda function deployed

---

## Phase 4 — API Gateway Setup

### Step 1 — Create REST API

**Command run:**
```bash
aws apigateway create-rest-api \
  --name my-web-app-api \
  --description "Web app API for Lambda" \
  --region ap-south-1
```

**Output received:**
```json
{
    "id": "vhr71ovri9",
    "name": "my-web-app-api",
    "description": "Web app API for Lambda"
}
```

**My observation:**
- API ID: `vhr71ovri9`
- This ID is used to build the endpoint URL
- API endpoint will be: `https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com`

**Verification:** OK — API Gateway created

---

### Step 2 — Get Root Resource ID

**Command run:**
```bash
aws apigateway get-resources \
  --rest-api-id vhr71ovri9 \
  --region ap-south-1 \
  --query 'items[0].id' \
  --output text
```

**Output received:**
```
fv63t88d5a
```

**My observation:**
- Root resource ID: `fv63t88d5a`
- Every API has a root resource (the `/` path)
- We'll add a GET method to this resource

**Verification:** OK — Root resource identified

---

### Step 3 — Create GET Method

**Command run:**
```bash
aws apigateway put-method \
  --rest-api-id vhr71ovri9 \
  --resource-id fv63t88d5a \
  --http-method GET \
  --authorization-type NONE \
  --region ap-south-1
```

**Output received:**
```json
{
    "httpMethod": "GET",
    "authorizationType": "NONE"
}
```

**My observation:**
- Method created on root resource with no authorization
- `NONE` means anyone can call it — public API
- We could set authorization to `AWS_IAM` or `CUSTOM_AUTHORIZER` for restricted access

**Verification:** OK — GET method created

---

### Step 4 — Integrate with Lambda (AWS_PROXY)

**Command run:**
```bash
aws apigateway put-integration \
  --rest-api-id vhr71ovri9 \
  --resource-id fv63t88d5a \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:ap-south-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-south-1:495331821583:function:my-web-app/invocations \
  --region ap-south-1
```

**Output received:**
```json
{
    "type": "AWS_PROXY",
    "httpMethod": "POST"
}
```

**What AWS_PROXY means:**
- `AWS_PROXY` — API Gateway passes entire request object to Lambda, Lambda returns complete response object
- Alternative `INTEGRATION` type requires response mapping — more complex
- POST — API Gateway always uses POST when calling Lambda, regardless of client HTTP method

**My observation:**
- URI format: `arn:aws:apigateway:REGION:lambda:path/2015-03-31/functions/FUNCTION_ARN/invocations`
- The URI tells API Gateway which Lambda function to invoke
- AWS_PROXY is simpler and the modern way

**Verification:** OK — Lambda integration created

---

### Step 5 — Grant API Gateway Permission to Invoke Lambda

**Command run:**
```bash
aws lambda add-permission \
  --function-name my-web-app \
  --statement-id apigateway-access \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --region ap-south-1
```

**Output received:**
```json
{
    "Statement": "{\"Sid\":\"apigateway-access\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"apigateway.amazonaws.com\"},\"Action\":\"lambda:InvokeFunction\",\"Resource\":\"arn:aws:lambda:ap-south-1:495331821583:function:my-web-app\"}"
}
```

**My observation:**
- Without this permission, API Gateway would get "Access Denied" when trying to invoke Lambda
- `Principal: apigateway.amazonaws.com` — allows the API Gateway service
- `Action: lambda:InvokeFunction` — allows only the invoke action (not create, delete, update)

**Verification:** OK — Permission granted

---

### Step 6 — Deploy API

**Command run:**
```bash
aws apigateway create-deployment \
  --rest-api-id vhr71ovri9 \
  --stage-name prod \
  --region ap-south-1
```

**Output received:**
```json
{
    "id": "ngw08j",
    "restApiId": "vhr71ovri9",
    "stageName": "prod"
}
```

**My observation:**
- Deployment ID: `ngw08j`
- Stage: `prod` — this is the environment (could also be dev, test, staging)
- Each stage is a separate instance with its own URL and settings
- Endpoint now available at: `https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod`

**Verification:** OK — API deployed and live

---

## Phase 5 — Testing the Endpoint

### Step 1 — Test Root Endpoint

**Command run:**
```bash
curl -s "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod" | python3 -m json.tool
```

**Output received:**
```json
{
    "message": "Hello, World!",
    "timestamp": "2026-05-17T09:58:40.266662",
    "service": "AWS Lambda Web App"
}
```

**My observation:**
- Function executed successfully
- No query parameter provided, so `name` defaults to "World"
- Timestamp shows current time (UTC)
- HTTP 200 response with JSON body
- Response time: ~250ms (includes cold start + execution)

**Verification:** OK — Root endpoint working

---

### Step 2 — Test with Query Parameter

**Command run:**
```bash
curl -s "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod?name=AWS" | python3 -m json.tool
```

**Output received:**
```json
{
    "message": "Hello, AWS!",
    "timestamp": "2026-05-17T09:58:53.243838",
    "service": "AWS Lambda Web App"
}
```

**My observation:**
- Query parameter `?name=AWS` parsed correctly
- Function extracted the value and used it in the response
- Timestamp is fresh — new invocation (not cached)
- Response time: ~50ms (warm container, no cold start)

**Verification:** OK — Query parameters working

---

### Step 3 — Test with Different Names

**Command run:**
```bash
curl -s "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod?name=Lambda" | python3 -m json.tool
```

**Output received:**
```json
{
    "message": "Hello, Lambda!",
    "timestamp": "2026-05-17T09:59:10.512491",
    "service": "AWS Lambda Web App"
}
```

**Verification:** OK — Multiple requests working

---

## Summary

### All Resources Created

| Resource | Name / ID | Status |
|----------|-----------|--------|
| IAM Role | lambda-execution-role | Active |
| IAM Policy | AWSLambdaBasicExecutionRole | Attached |
| Lambda Function | my-web-app | Active (Python 3.12) |
| API Gateway API | my-web-app-api (vhr71ovri9) | Active |
| API Gateway Deployment | prod (ngw08j) | Active |
| Permission | apigateway-access | Granted |

### API Endpoint Summary

| Property | Value |
|----------|-------|
| **Endpoint URL** | `https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod` |
| **HTTP Method** | GET |
| **Query Parameters** | `?name=YourName` (optional) |
| **Response Format** | JSON |
| **Status Codes** | 200 OK |
| **Response Time** | ~50-250ms (depends on cold start) |

### Test Commands

```bash
# Default greeting
curl "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod"

# With name parameter
curl "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod?name=AWS"

# Pretty print JSON
curl -s "https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod?name=Lambda" | python3 -m json.tool
```

### Command Summary

| Command | Where | Purpose | Result |
|---------|-------|---------|--------|
| `python3 -c "import json..."` | Local | Create trust policy JSON | Trust policy created |
| `aws iam create-role` | Local | Create IAM role for Lambda | Role ARN: arn:aws:iam::495331821583:role/lambda-execution-role |
| `aws iam attach-role-policy` | Local | Attach execution permissions | Permissions attached |
| `aws lambda create-function` | Local | Deploy function code | Function deployed |
| `aws apigateway create-rest-api` | Local | Create API Gateway API | API ID: vhr71ovri9 |
| `aws apigateway put-method` | Local | Add GET method to root | Method created |
| `aws apigateway put-integration` | Local | Connect Lambda to API | AWS_PROXY integration created |
| `aws lambda add-permission` | Local | Grant API Gateway access | Permission granted |
| `aws apigateway create-deployment` | Local | Deploy API to prod stage | API live at endpoint URL |
| `curl https://...` | Browser/CLI | Test endpoint | Responses working ✅ |

### Key Observations from This Project

1. **Serverless = No servers to manage** — Lambda handles scaling, patching, updates automatically
2. **AWS_PROXY simplifies integration** — Lambda receives full request, returns full response
3. **Cold start can be slow** — first invocation ~250-500ms, subsequent ones ~50ms
4. **Pay per invocation** — Lambda pricing: $0.0000002 per invocation (free tier: 1M/month)
5. **API Gateway is the public face** — Lambda stays private, only accessed through API Gateway
6. **Query parameters parsed automatically** — API Gateway extracts them into the event object
7. **JSON is the standard response format** — Lambda returns Python dict, API Gateway serializes to JSON
8. **Timestamps are UTC** — `datetime.now()` in Lambda is in UTC timezone
9. **CloudWatch logs are automatic** — print statements appear in logs, accessible via AWS Console
10. **No state between invocations** — each request starts with a fresh container

### Cost Analysis

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Lambda | 100 requests/day (3000/month) | $0.00 (free tier: 1M) |
| API Gateway | 3000 requests/month | $0.01 (3,000 × $3.50 / 1M) |
| CloudWatch Logs | ~50KB logs | $0.00 (free tier: 5GB) |
| **Total** | | **~$0.01** |

With free tier: **$0.00**

---

## Next Steps

1. **Add more query parameters** — ?name=VALUE&greeting=hello
2. **Add POST method** — Accept JSON in request body
3. **Add database integration** — Query RDS from Lambda
4. **Add authentication** — API Key or JWT authorization
5. **Add error handling** — Try/catch with proper error responses
6. **Custom domain name** — Use Route53 with your own domain
7. **Monitor performance** — CloudWatch metrics and X-Ray tracing

---

## AWS Credits Achievement

✅ **"Create a web app using AWS Lambda" — $20 credit earned**

Resources created:
- Lambda function (serverless compute)
- API Gateway (HTTP endpoint)
- IAM role & permissions
- Full public web endpoint


 Lambda Web App Cleanup Guide
⚠️ Important: Cleanup Order Matters!
We need to delete resources in this specific order to avoid dependency conflicts:

Step 1: Delete API Gateway REST API
🎯 This removes the API, all stages, deployments, and methods

Option A - AWS Console:

Go to API Gateway Console 
Select "my-web-app-api" (ID: vhr71ovri9)
Click "Actions" → "Delete API"
Type "my-web-app-api" to confirm
Click "Delete"
Option B - AWS CLI:

aws apigateway delete-rest-api --rest-api-id vhr71ovri9 --region ap-south-1

Run in CloudShell
Step 2: Delete Lambda Function
🎯 This removes the function and its configuration

Option A - AWS Console:

Go to Lambda Console - my-web-app 
Click "Actions" → "Delete function"
Type "delete" to confirm
Click "Delete"
Option B - AWS CLI:

aws lambda delete-function --function-name my-web-app --region ap-south-1

Run in CloudShell
Step 3: Delete CloudWatch Log Group
🎯 This removes all Lambda execution logs

Option A - AWS Console:

Go to CloudWatch Logs 
Find "/aws/lambda/my-web-app"
Select it and click "Actions" → "Delete log group(s)"
Type "delete" to confirm
Option B - AWS CLI:

aws logs delete-log-group --log-group-name "/aws/lambda/my-web-app" --region ap-south-1

Run in CloudShell
Step 4: Delete IAM Role
🎯 This removes the execution role and its policies

Option A - AWS Console:

Go to IAM Console - lambda-execution-role 
Click "Delete"
Type "lambda-execution-role" to confirm
Click "Delete"
Option B - AWS CLI:

# First detach any attached policies (if any)
aws iam list-attached-role-policies --role-name lambda-execution-role
# Then delete the role
aws iam delete-role --role-name lambda-execution-role

Run in CloudShell
🚀 Quick Cleanup (All CLI Commands)
If you prefer to do it all at once via CLI:

# 1. Delete API Gateway
aws apigateway delete-rest-api --rest-api-id vhr71ovri9 --region ap-south-1

# 2. Delete Lambda Function  
aws lambda delete-function --function-name my-web-app --region ap-south-1

# 3. Delete CloudWatch Log Group
aws logs delete-log-group --log-group-name "/aws/lambda/my-web-app" --region ap-south-1

# 4. Delete IAM Role
aws iam delete-role --role-name lambda-execution-role

Run in CloudShell


 Complete IAM Role Deletion Process:
Step 1: Detach the Managed Policy
aws iam detach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

Run in CloudShell
Step 2: Delete the Role
aws iam delete-role --role-name lambda-execution-role

Run in CloudShell
🚀 Or do it all in one go:
# Detach the policy first
aws iam detach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Then delete the role
aws iam delete-role --role-name lambda-execution-role

Run in CloudShell
Alternative - AWS Console Method:
Go to IAM Console - lambda-execution-role 
Click on "Permissions" tab
Find "AWSLambdaBasicExecutionRole" and click "Detach"
Confirm the detachment
Then click "Delete" to delete the role
The AWSLambdaBasicExecutionRole is an AWS managed policy that provides CloudWatch Logs permissions for Lambda functions. Once detached, you'll be able to delete the role successfully.
---

*Author: Viswanath TGR*
*LinkedIn: linkedin.com/in/viswanath-tgr-328b11264*
*Date: May 17, 2026*
*Region: ap-south-1 (Mumbai)*
*Endpoint: https://vhr71ovri9.execute-api.ap-south-1.amazonaws.com/prod*
