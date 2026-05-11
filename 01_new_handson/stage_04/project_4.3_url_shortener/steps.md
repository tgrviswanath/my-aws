# Steps — Project 4.3 URL Shortener

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -auto-approve
API_URL=$(terraform output -raw api_url)
```

---

## Phase 2 — Test

```bash
# Shorten a URL
RESULT=$(curl -s -X POST $API_URL/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}')
echo $RESULT | python3 -m json.tool

CODE=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")
echo "Short code: $CODE"

# Test redirect (follow the redirect)
curl -v $API_URL/$CODE
# Expected: 302 Location: https://docs.aws.amazon.com/...

# Test redirect without following (see the 302)
curl -I $API_URL/$CODE

# Check stats
curl -s $API_URL/stats/$CODE | python3 -m json.tool
# Expected: clicks: 1 (or however many times you visited)

# Test non-existent code
curl -s $API_URL/nonexistent | python3 -m json.tool
# Expected: 404
```

---

## Phase 3 — Verify DynamoDB

```bash
TABLE=$(terraform output -raw table_name)

# Scan the table
aws dynamodb scan --table-name $TABLE \
  --query "Items[*].{code:code.S,url:original_url.S,clicks:clicks.N,ttl:ttl.N}"

# Check TTL is set correctly (should be ~30 days from now)
python3 -c "
import time
ttl = $(aws dynamodb get-item --table-name $TABLE --key '{\"code\":{\"S\":\"$CODE\"}}' \
  --query 'Item.ttl.N' --output text)
import datetime
print('Expires:', datetime.datetime.fromtimestamp(int(ttl)))
"
```

---

## Screenshots to Take
- [ ] POST /shorten returning short URL
- [ ] Browser following redirect to original URL
- [ ] GET /stats showing click count
- [ ] DynamoDB item with TTL attribute set
- [ ] Click counter incrementing on each visit
