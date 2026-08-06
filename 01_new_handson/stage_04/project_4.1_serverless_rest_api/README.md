# Project 4.1 — Serverless REST API

**Stage:** 04 | **Level:** Intermediate | **Est. Time:** 45 min | **Cost:** ~$0.50/month

This project builds a fully serverless CRUD REST API using AWS Lambda, API Gateway (HTTP API), and DynamoDB.
A single Python 3.12 Lambda function handles all three operations: POST /items creates a new item with a
caller-supplied or auto-generated `id`, GET /items/{id} retrieves it by partition key, and DELETE /items/{id}
removes it. API Gateway is configured as an HTTP API (not REST API) with Lambda proxy integration, meaning
the full HTTP request arrives as a JSON event and the Lambda response becomes the HTTP response verbatim.
An IAM execution role scoped to the single DynamoDB table grants the function PutItem, GetItem, and DeleteItem.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS Lambda (Python 3.12) | Executes CRUD logic for all three routes | $0.20/1M requests (free tier: 1M/month) |
| API Gateway HTTP API | Routes HTTP requests to Lambda, returns responses | $1.00/1M calls (free tier: 1M/month) |
| DynamoDB (on-demand) | Stores items with partition key `id` (String) | $1.25/WCU, $0.25/RCU per million; $0 when idle |
| IAM Role | Grants Lambda permission to call DynamoDB | Free |
| CloudWatch Logs | Lambda execution logs and error traces | $0.50/GB ingested (minimal at low traffic) |

## Input / Output

### Input

| Parameter | Type | Where | Example |
|---|---|---|---|
| Python Lambda source file | `.py` file | Deployed as Lambda function code | `lambda_function.py` |
| DynamoDB table name | String | Lambda env var `TABLE_NAME` | `items-table` |
| POST body `id` field | String (JSON) | HTTP request body | `{"id": "item-001", "name": "wrench"}` |
| GET path parameter `id` | String | URL path `/items/{id}` | `/items/item-001` |
| DELETE path parameter `id` | String | URL path `/items/{id}` | `/items/item-001` |

### Output

| Operation | Status Code | Response Body |
|---|---|---|
| POST /items (created) | 201 | `{"message": "Created", "id": "item-001"}` |
| GET /items/{id} (found) | 200 | `{"id": "item-001", "name": "wrench"}` |
| GET /items/{id} (not found) | 404 | `{"message": "Item not found"}` |
| DELETE /items/{id} | 200 | `{"message": "Deleted"}` |
| API Gateway invoke URL | — | `https://abc123.execute-api.us-east-1.amazonaws.com` |

## Architecture

```
Client (curl / Postman)
        |
        v
+-------------------------+
|  API Gateway HTTP API   |
|  POST /items            |
|  GET  /items/{id}       |
|  DELETE /items/{id}     |
+-------------------------+
        |  Lambda Proxy Integration
        v
+-------------------------+
|  Lambda Function        |
|  Python 3.12            |
|  handler: lambda_handler|
+-------------------------+
        |  boto3 DynamoDB calls
        v
+-------------------------+
|  DynamoDB Table         |
|  items-table            |
|  PK: id (String)        |
+-------------------------+
        |
  IAM Role (Lambda)
  PutItem / GetItem / DeleteItem
```

## Quick Start

```cmd
REM 1. Create DynamoDB table with partition key "id" (String)
aws dynamodb create-table ^
  --table-name items-table ^
  --attribute-definitions AttributeName=id,AttributeType=S ^
  --key-schema AttributeName=id,KeyType=HASH ^
  --billing-mode PAY_PER_REQUEST ^
  --region us-east-1

REM 2. Create IAM role for Lambda execution
aws iam create-role ^
  --role-name lambda-dynamo-role ^
  --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"

REM 3. Attach DynamoDB and basic execution policies
aws iam attach-role-policy --role-name lambda-dynamo-role ^
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name lambda-dynamo-role ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

REM 4. Zip and deploy Lambda function
powershell Compress-Archive -Path lambda_function.py -DestinationPath function.zip -Force
aws lambda create-function ^
  --function-name crud-api-handler ^
  --runtime python3.12 ^
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-dynamo-role ^
  --handler lambda_function.lambda_handler ^
  --zip-file fileb://function.zip ^
  --environment Variables={TABLE_NAME=items-table} ^
  --region us-east-1

REM 5. Create HTTP API and connect to Lambda
aws apigatewayv2 create-api ^
  --name crud-http-api ^
  --protocol-type HTTP ^
  --target arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:crud-api-handler ^
  --region us-east-1

REM 6. Test the deployed API
curl -X POST https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/items ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"item-001\",\"name\":\"wrench\"}"

curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/items/item-001

curl -X DELETE https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/items/item-001
```

## Data Flow

1. Client sends HTTP request to the API Gateway HTTP API invoke URL.
2. API Gateway matches the route (POST /items, GET /items/{id}, or DELETE /items/{id}).
3. API Gateway constructs a Lambda proxy event JSON containing method, path, pathParameters, and body.
4. Lambda function receives the event, reads `httpMethod` and `pathParameters` to branch logic.
5. For POST: Lambda calls `dynamodb.put_item()` with the parsed JSON body as the DynamoDB item.
6. For GET: Lambda calls `dynamodb.get_item()` with the `id` path parameter as the key.
7. For DELETE: Lambda calls `dynamodb.delete_item()` with the `id` path parameter as the key.
8. Lambda returns a dict with `statusCode`, `headers`, and `body` (JSON string).
9. API Gateway forwards that dict directly as the HTTP response to the client.

## Project Files

| File | Description |
|---|---|
| `lambda_function.py` | Python 3.12 Lambda handler — routes POST/GET/DELETE to DynamoDB operations |
| `function.zip` | Deployment package created from `lambda_function.py` |
| `README.md` | This file |

## Lessons Learned

- HTTP API is 70% cheaper than REST API for simple Lambda proxy use cases — REST API adds features like request validation and usage plans that add cost but are unnecessary here.
- DynamoDB on-demand pricing means the table costs exactly $0 when no requests are made — ideal for dev/test environments that sit idle overnight.
- Lambda cold start for Python 3.12 is 200–500ms; subsequent warm invocations drop to under 10ms — cold starts are visible on the first request after a period of inactivity.
- DynamoDB requires the partition key attribute type declared at table creation to match exactly on every write — passing a number for an `id` declared as String (`S`) raises a `ValidationException`.
- API Gateway HTTP API with `--target` auto-creates a Lambda integration and `$default` route, which proxies all unmatched paths — useful for a single-function API but requires careful routing logic inside Lambda.
- The Lambda function must return `statusCode` as an integer and `body` as a JSON string, not a dict — forgetting `json.dumps()` on the body causes API Gateway to return a 502 Internal Server Error.
- Granting `AmazonDynamoDBFullAccess` is convenient for learning but in production the IAM policy should be scoped to specific actions (`dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:DeleteItem`) on the specific table ARN.
