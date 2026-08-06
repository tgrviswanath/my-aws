# Verification & Validation — Project 4.3 URL Shortener

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| API Gateway | API Gateway → APIs | `handson-url-shortener-api` HTTP API with `/shorten`, `/{code}`, `/stats/{code}` routes |
| Lambda Function | Lambda → Functions | `handson-url-shortener-handler`, Runtime = Python 3.11 |
| DynamoDB Table | DynamoDB → Tables | `handson-url-shortener-urls`, Status = **Active**, TTL enabled |
| TTL Attribute | DynamoDB → Table → Additional settings | TTL attribute = `ttl`, Status = **Enabled** |

📸 Screenshot: POST /shorten returning short code  
📸 Screenshot: Browser following redirect to original URL  
📸 Screenshot: DynamoDB item showing `clicks` counter and `ttl` attribute

---

## 2. AWS CLI Verification

```bash
API_URL=$(cd terraform && terraform output -raw api_url)
TABLE=$(cd terraform && terraform output -raw table_name)

# 2.1 DynamoDB TTL enabled
aws dynamodb describe-time-to-live --table-name $TABLE \
  --query "TimeToLiveDescription.{Status:TimeToLiveStatus,Attribute:AttributeName}"
# Expected: Status=ENABLED, Attribute=ttl

# 2.2 Shorten a URL
RESULT=$(curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}')
echo $RESULT | python3 -m json.tool
CODE=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")
echo "Short code: $CODE"
# Expected: 6-char alphanumeric code

# 2.3 Redirect — check 302 and Location header
curl -sI $API_URL/$CODE | grep -E "HTTP|Location"
# Expected: HTTP/2 302, Location: https://docs.aws.amazon.com/...

# 2.4 Stats — click counter
curl -s $API_URL/stats/$CODE | python3 -m json.tool
# Expected: {"code":"xxx","original_url":"https://...","clicks":"1","created_at":"..."}

# 2.5 Visit again — click counter increments
curl -sI $API_URL/$CODE > /dev/null
curl -s $API_URL/stats/$CODE | python3 -c "import sys,json; print('Clicks:', json.load(sys.stdin)['clicks'])"
# Expected: Clicks: 2

# 2.6 Non-existent code — 404
curl -s $API_URL/doesnotexist | python3 -m json.tool
# Expected: {"message":"Short URL not found"} with 404

# 2.7 DynamoDB item — verify TTL is set
aws dynamodb get-item \
  --table-name $TABLE \
  --key "{\"code\":{\"S\":\"$CODE\"}}" \
  --query "Item.{code:code.S,url:original_url.S,clicks:clicks.N,ttl:ttl.N}"
# Expected: ttl is ~30 days from now (Unix timestamp)

# 2.8 Verify TTL is ~30 days out
python3 -c "
import time, datetime
ttl = $(aws dynamodb get-item --table-name $TABLE \
  --key '{\"code\":{\"S\":\"$CODE\"}}' \
  --query 'Item.ttl.N' --output text)
exp = datetime.datetime.fromtimestamp(int(ttl))
days = (exp - datetime.datetime.now()).days
print(f'Expires: {exp}  ({days} days from now)')
"
# Expected: ~30 days from now
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
# aws_apigatewayv2_route.shorten
# aws_apigatewayv2_route.redirect
# aws_apigatewayv2_route.stats
# aws_lambda_function.shortener
# aws_lambda_permission.api_gw
# aws_dynamodb_table.urls
# aws_iam_role.lambda
# aws_iam_role_policy_attachment.lambda_basic
# aws_iam_role_policy.dynamodb

terraform state show aws_dynamodb_table.urls
# Shows: ttl.enabled=true, ttl.attribute_name=ttl

terraform output
# Expected: api_url, table_name

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Atomic Counter

```bash
# Visit the short URL 5 times and verify counter increments correctly
CODE="your-short-code"
for i in {1..5}; do
  curl -sI $API_URL/$CODE > /dev/null
done

curl -s $API_URL/stats/$CODE | python3 -c "import sys,json; print('Clicks:', json.load(sys.stdin)['clicks'])"
# Expected: Clicks: 5 (or 5 + previous visits)
# Confirms atomic counter (ADD clicks 1) works correctly under concurrent access
```

---

## 5. Expected Successful Outputs

**POST /shorten (201):**
```json
{ "code": "aB3xY9", "short_url": "https://api.../aB3xY9", "original_url": "https://docs.aws.amazon.com/..." }
```

**GET /{code} (302):**
```
HTTP/2 302
location: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
```

**GET /stats/{code} (200):**
```json
{ "code": "aB3xY9", "short_url": "https://api.../aB3xY9", "original_url": "https://docs.aws.amazon.com/...", "clicks": 3, "created_at": "2024-01-01T12:00:00Z" }
```

**GET /nonexistent (404):**
```json
{ "error": "Short URL 'nonexistent' not found or expired" }
```

---

## 6. Verification Checklist

- [ ] API Gateway deployed with `/shorten`, `/{code}`, `/stats/{code}` routes
- [ ] Lambda function `handson-url-shortener-handler` active, runtime = Python 3.11
- [ ] DynamoDB table `handson-url-shortener-urls` status = ACTIVE
- [ ] DynamoDB TTL enabled on `ttl` attribute
- [ ] POST /shorten returns 6-char short code
- [ ] GET /{code} returns 302 with correct Location header
- [ ] GET /stats/{code} returns click count as integer
- [ ] Click counter increments on each redirect visit
- [ ] GET /nonexistent returns 404 with `{"error": "Short URL 'nonexistent' not found or expired"}`
- [ ] DynamoDB item has `ttl` set to ~30 days from creation
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
