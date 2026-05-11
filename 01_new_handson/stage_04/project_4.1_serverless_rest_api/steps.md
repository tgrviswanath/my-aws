# Steps — Project 4.1 Serverless REST API

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -auto-approve

API_URL=$(terraform output -raw api_url)
echo "API URL: $API_URL"
```

---

## Phase 2 — Test All Endpoints

```bash
# Create items
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Item One", "description": "First item"}' | python3 -m json.tool

curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Item Two", "description": "Second item"}' | python3 -m json.tool

# List all items
curl -s $API_URL/items | python3 -m json.tool

# Get specific item (use ID from create response)
ITEM_ID="paste-id-here"
curl -s $API_URL/items/$ITEM_ID | python3 -m json.tool

# Update item
curl -s -X PUT $API_URL/items/$ITEM_ID \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}' | python3 -m json.tool

# Delete item
curl -s -X DELETE $API_URL/items/$ITEM_ID | python3 -m json.tool

# Verify deleted
curl -s $API_URL/items/$ITEM_ID | python3 -m json.tool
# Expected: 404 not found
```

---

## Phase 3 — View Lambda Logs

```bash
LAMBDA_NAME=$(terraform output -raw lambda_name)

# Tail logs in real time
aws logs tail /aws/lambda/$LAMBDA_NAME --follow

# View recent logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/$LAMBDA_NAME \
  --start-time $(date -d '5 minutes ago' +%s000)
```

---

## Phase 4 — Test Error Cases

```bash
# Missing required field
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"description": "no name field"}' | python3 -m json.tool
# Expected: 400 Bad Request

# Non-existent item
curl -s $API_URL/items/does-not-exist | python3 -m json.tool
# Expected: 404 Not Found

# Invalid JSON
curl -s -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d 'not valid json' | python3 -m json.tool
# Expected: 400 Bad Request
```

---

## Phase 5 — Test Locally with LocalStack

```bash
# Start LocalStack (from Project 0.1)
docker compose up -d

# Deploy to LocalStack
cd terraform
terraform init
terraform apply \
  -var="region=us-east-1" \
  -auto-approve

# Test locally
curl http://localhost:4566/restapis/.../items
```

---

## Screenshots to Take
- [ ] `terraform apply` output with API URL
- [ ] POST /items returning 201 with item ID
- [ ] GET /items listing all items
- [ ] GET /items/{id} returning specific item
- [ ] PUT /items/{id} showing updated fields
- [ ] DELETE /items/{id} returning 200
- [ ] 404 response for non-existent item
- [ ] Lambda logs in CloudWatch
