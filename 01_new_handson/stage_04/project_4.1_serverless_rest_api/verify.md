# Verification & Validation — Project 4.1 Serverless REST API

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| API Gateway | API Gateway → APIs | HTTP API exists, Stage = `$default` |
| Lambda Function | Lambda → Functions | `handson-items` function, Runtime = Python 3.11 |
| Lambda Trigger | Lambda → Configuration → Triggers | API Gateway trigger attached |
| DynamoDB Table | DynamoDB → Tables | `handson-items`, Status = **Active** |
| Lambda Logs | CloudWatch → Log Groups | `/aws/lambda/handson-items` exists |
| IAM Role | IAM → Roles | Lambda execution role with DynamoDB policy |

📸 Screenshot: API Gateway showing invoke URL  
📸 Screenshot: Lambda function with API Gateway trigger  
📸 Screenshot: DynamoDB table with items after POST requests

---

## 2. AWS CLI Verification

```bash
API_URL=$(cd terraform && terraform output -raw api_url)
LAMBDA_NAME=$(cd terraform && terraform output -raw lambda_name)
TABLE=$(cd terraform && terraform output -raw table_name)

# 2.1 Lambda exists and active
aws lambda get-function --function-name $LAMBDA_NAME \
  --query "Configuration.{State:State,Runtime:Runtime,Timeout:Timeout,Memory:MemorySize}"
# Expected: State=Active, Runtime=python3.11

# 2.2 DynamoDB table active
aws dynamodb describe-table --table-name $TABLE \
  --query "Table.{Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}"
# Expected: Status=ACTIVE, BillingMode=PAY_PER_REQUEST

# 2.3 POST — create item
ITEM_ID=$(curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Item","description":"verify test"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created item: $ITEM_ID"
# Expected: UUID string

# 2.4 GET — list items
curl -s $API_URL/items | python3 -m json.tool
# Expected: array containing the created item

# 2.5 GET — specific item
curl -s $API_URL/items/$ITEM_ID | python3 -m json.tool
# Expected: item with correct name and description

# 2.6 PUT — update item
curl -s -X PUT $API_URL/items/$ITEM_ID \
  -H "Content-Type: application/json" \
  -d '{"description":"updated"}' | python3 -m json.tool
# Expected: updated item with new description

# 2.7 DELETE — remove item
curl -s -X DELETE $API_URL/items/$ITEM_ID | python3 -m json.tool
# Expected: 200 with success message

# 2.8 GET after delete — 404
curl -s $API_URL/items/$ITEM_ID | python3 -m json.tool
# Expected: {"message": "Item not found"} with 404 status

# 2.9 Error cases
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"description":"missing name"}' | python3 -m json.tool
# Expected: 400 Bad Request
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_apigatewayv2_api.main
# aws_apigatewayv2_stage.default
# aws_apigatewayv2_integration.lambda
# aws_apigatewayv2_route.items
# aws_lambda_function.handler
# aws_lambda_permission.apigw
# aws_dynamodb_table.items
# aws_iam_role.lambda_exec
# aws_iam_role_policy_attachment.dynamodb

terraform state show aws_lambda_function.handler
# Shows: runtime=python3.11, timeout, environment variables (TABLE_NAME)

terraform output
# Expected: api_url, lambda_name, table_name

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Lambda Logs

```bash
# Invoke Lambda directly and check logs
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload '{"requestContext":{"http":{"method":"GET"}},"rawPath":"/items"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json | python3 -m json.tool
# Expected: statusCode=200, body contains items array

# Check CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/$LAMBDA_NAME \
  --filter-pattern "ERROR" \
  --start-time $(date -d '10 minutes ago' +%s000 2>/dev/null || date -v-10M +%s000)
# Expected: no ERROR entries after successful test
```

---

## 5. Expected Successful Outputs

**POST /items (201):**
```json
{ "id": "abc-123-uuid", "name": "Test Item", "description": "verify test", "created_at": "2024-01-01T12:00:00Z" }
```

**GET /items (200):**
```json
[{ "id": "abc-123-uuid", "name": "Test Item", "description": "verify test" }]
```

**DELETE /items/{id} (200):**
```json
{ "message": "Item deleted" }
```

**GET /items/{id} after delete (404):**
```json
{ "message": "Item not found" }
```

**POST missing name (400):**
```json
{ "message": "name is required" }
```

---

## 6. Verification Checklist

- [ ] API Gateway HTTP API deployed with invoke URL
- [ ] Lambda function state = Active, runtime = Python 3.11
- [ ] DynamoDB table status = ACTIVE, billing = PAY_PER_REQUEST
- [ ] Lambda has API Gateway trigger
- [ ] Lambda execution role has DynamoDB read/write permissions
- [ ] POST /items returns 201 with item ID
- [ ] GET /items returns array of items
- [ ] GET /items/{id} returns specific item
- [ ] PUT /items/{id} updates item fields
- [ ] DELETE /items/{id} returns 200
- [ ] GET /items/{id} after delete returns 404
- [ ] POST without `name` returns 400
- [ ] CloudWatch log group `/aws/lambda/handson-items` exists
- [ ] `terraform plan` shows no changes
