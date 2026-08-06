# Steps — Project 4.5 SNS/SQS Microservices

## Phase 1 — Deploy

```bash
cd terraform
terraform init && terraform apply -auto-approve
API_URL=$(terraform output -raw api_url)
SNS_ARN=$(terraform output -raw sns_topic_arn)
```

---

## Phase 2 — Place an Order (Trigger the Pipeline)

```bash
# Place an order — this publishes to SNS
curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "alice@example.com",
    "items": [
      {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
      {"product_id": "PROD-002", "quantity": 1, "price": 49.99}
    ],
    "total": 109.97
  }' | python3 -m json.tool
```

---

## Phase 3 — Verify All Consumers Ran

```bash
# Check inventory Lambda logs
aws logs tail /aws/lambda/handson-orders-inventory-consumer --follow &

# Check email Lambda logs
aws logs tail /aws/lambda/handson-orders-email-consumer --follow &

# Check analytics Lambda logs
aws logs tail /aws/lambda/handson-orders-analytics-consumer --follow &

# Place another order and watch all three fire simultaneously
curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{"customer": "bob@example.com", "items": [], "total": 19.99}'
```

---

## Phase 4 — Test DLQ (Simulate Failure)

```bash
# Temporarily break the inventory consumer by sending bad data
aws sns publish \
  --topic-arn $SNS_ARN \
  --message '{"invalid": "data that will cause consumer to fail"}'

# After 3 retries, message moves to DLQ (wait ~3 × visibility timeout = ~180 seconds)
echo "Waiting for 3 retries to complete (approx 3 minutes)..."
sleep 180

# Check DLQ — Terraform outputs dlq_urls as a map
DLQ_URL=$(terraform -chdir=terraform output -json dlq_urls | python3 -c "import sys,json; print(json.load(sys.stdin)['inventory'])")
aws sqs receive-message --queue-url $DLQ_URL | python3 -m json.tool
```

---

## Phase 5 — Check SQS Queue Depths

```bash
# Check how many messages are in each queue
for QUEUE_URL in $(terraform output -json queue_urls | python3 -c "import sys,json; [print(v) for v in json.load(sys.stdin).values()]"); do
  aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names ApproximateNumberOfMessages \
    --query "Attributes.ApproximateNumberOfMessages"
done
```

---

## Screenshots to Take
- [ ] SNS topic with 3 SQS subscriptions
- [ ] Order placed → all 3 consumer logs firing simultaneously
- [ ] SQS queue depth (messages in flight)
- [ ] DLQ receiving failed message after retries
- [ ] CloudWatch showing all 3 Lambda invocations from one SNS publish
