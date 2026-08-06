# Verification & Validation — Project 4.1 Serverless REST API

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| API Gateway | API Gateway → APIs | `handson-api-gateway` HTTP API, Stage = `$default` |
| Lambda Function | Lambda → Functions | `handson-api-handler`, Runtime = Python 3.11 |
| Lambda Trigger | Lambda → Configuration → Triggers | API Gateway trigger attached |
| DynamoDB Table | DynamoDB → Tables | `handson-api-items`, Status = **Active** |
| Lambda Logs | CloudWatch → Log Groups | `/aws/lambda/handson-api-handler` exists |
| IAM Role | IAM → Roles | `handson-api-lambda-role` with DynamoDB policy |

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
# Expected: State=Active, Runtime=python3.11, Timeout=30

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
# Expected: {"items": [{...}], "count": 1}

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
# Expected: {"message": "Item $ITEM_ID deleted"}

# 2.8 GET after delete — 404
curl -s $API_URL/items/$ITEM_ID | python3 -m json.tool
# Expected: {"error": "Item $ITEM_ID not found"} with 404 status

# 2.9 Error cases
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"description":"missing name"}' | python3 -m json.tool
# Expected: {"error": "Field 'name' is required"} with 400
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
# aws_apigatewayv2_route.list
# aws_apigatewayv2_route.get
# aws_apigatewayv2_route.create
# aws_apigatewayv2_route.update
# aws_apigatewayv2_route.delete
# aws_lambda_function.api
# aws_lambda_permission.api_gw
# aws_dynamodb_table.items
# aws_iam_role.lambda
# aws_iam_role_policy_attachment.lambda_basic
# aws_iam_role_policy.dynamodb
# aws_cloudwatch_log_group.lambda
# aws_cloudwatch_log_group.api_gw

terraform state show aws_lambda_function.api
# Shows: function_name=handson-api-handler, runtime=python3.11, timeout=30

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
{ "id": "abc-123-uuid", "name": "Test Item", "description": "verify test", "created_at": "2024-01-01T12:00:00Z", "updated_at": "2024-01-01T12:00:00Z" }
```

**GET /items (200):**
```json
{ "items": [{ "id": "abc-123-uuid", "name": "Test Item", "description": "verify test" }], "count": 1 }
```

**DELETE /items/{id} (200):**
```json
{ "message": "Item abc-123-uuid deleted" }
```

**GET /items/{id} after delete (404):**
```json
{ "error": "Item abc-123-uuid not found" }
```

**POST missing name (400):**
```json
{ "error": "Field 'name' is required" }
```

---

## 6. Verification Checklist

- [ ] API Gateway HTTP API deployed with invoke URL
- [ ] Lambda function `handson-api-handler` state = Active, runtime = Python 3.11
- [ ] DynamoDB table `handson-api-items` status = ACTIVE, billing = PAY_PER_REQUEST
- [ ] Lambda has API Gateway trigger
- [ ] Lambda execution role `handson-api-lambda-role` has DynamoDB read/write permissions
- [ ] POST /items returns 201 with item id
- [ ] GET /items returns `{"items": [...], "count": N}`
- [ ] GET /items/{id} returns specific item
- [ ] PUT /items/{id} updates item fields
- [ ] DELETE /items/{id} returns 200 with `{"message": "Item {id} deleted"}`
- [ ] GET /items/{id} after delete returns 404 with `{"error": "Item {id} not found"}`
- [ ] POST without `name` returns 400 with `{"error": "Field 'name' is required"}`
- [ ] CloudWatch log group `/aws/lambda/handson-api-handler` exists
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
