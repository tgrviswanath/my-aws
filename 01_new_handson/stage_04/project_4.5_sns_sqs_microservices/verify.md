# Verification & Validation — Project 4.5 SNS/SQS Microservices

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| SNS Topic | SNS → Topics | `handson-order-events`, 3 SQS subscriptions |
| SQS Queues | SQS → Queues | `inventory-queue`, `email-queue`, `analytics-queue` |
| DLQ Queues | SQS → Queues | `inventory-dlq`, `email-dlq`, `analytics-dlq` |
| Lambda Triggers | Lambda → Functions → Triggers | Each Lambda has SQS trigger |
| SQS Redrive Policy | SQS → Queue → Dead-letter queue tab | DLQ configured with maxReceiveCount=3 |

📸 Screenshot: SNS topic showing 3 SQS subscriptions  
📸 Screenshot: All 3 Lambda logs firing simultaneously after one order  
📸 Screenshot: DLQ receiving failed message after retries

---

## 2. AWS CLI Verification

```bash
API_URL=$(cd terraform && terraform output -raw api_url)
SNS_ARN=$(cd terraform && terraform output -raw sns_topic_arn)

# 2.1 SNS topic has 3 SQS subscriptions
aws sns list-subscriptions-by-topic --topic-arn $SNS_ARN \
  --query "Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint}"
# Expected: 3 entries, all Protocol=sqs

# 2.2 SQS queues exist with DLQ configured
for QUEUE in inventory-queue email-queue analytics-queue; do
  URL=$(aws sqs get-queue-url --queue-name handson-$QUEUE --query "QueueUrl" --output text)
  DLQ=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names RedrivePolicy \
    --query "Attributes.RedrivePolicy" --output text)
  echo "$QUEUE DLQ: $DLQ"
done
# Expected: each queue has RedrivePolicy with maxReceiveCount=3

# 2.3 Place an order — triggers all 3 consumers
ORDER_ID=$(curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"verify@example.com","items":[{"product_id":"P1","quantity":1,"price":9.99}],"total":9.99}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")
echo "Order placed: $ORDER_ID"

# Wait for all consumers to process
sleep 10

# 2.4 Verify all 3 Lambda functions were invoked
for LAMBDA in handson-inventory-consumer handson-email-consumer handson-analytics-consumer; do
  COUNT=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=$LAMBDA \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 --statistics Sum \
    --query "Datapoints[0].Sum" --output text)
  echo "$LAMBDA invocations: $COUNT"
done
# Expected: each Lambda shows >= 1 invocation

# 2.5 SQS queues are empty after processing
for QUEUE in inventory-queue email-queue analytics-queue; do
  URL=$(aws sqs get-queue-url --queue-name handson-$QUEUE --query "QueueUrl" --output text)
  MSGS=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names ApproximateNumberOfMessages \
    --query "Attributes.ApproximateNumberOfMessages" --output text)
  echo "handson-$QUEUE messages: $MSGS"
done
# Expected: 0 messages (all processed)

# 2.6 DLQ test — publish bad message
aws sns publish \
  --topic-arn $SNS_ARN \
  --message '{"invalid":"data that will cause consumer to fail"}'

# Wait for retries (3 × visibility timeout)
sleep 60

# Check DLQ
DLQ_URL=$(aws sqs get-queue-url --queue-name handson-inventory-dlq --query "QueueUrl" --output text)
aws sqs receive-message --queue-url $DLQ_URL \
  --query "Messages[*].{Body:Body,ReceiptHandle:ReceiptHandle}"
# Expected: failed message visible in DLQ
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_sns_topic.orders
# aws_sqs_queue.inventory / .email / .analytics
# aws_sqs_queue.inventory_dlq / .email_dlq / .analytics_dlq
# aws_sns_topic_subscription.inventory / .email / .analytics
# aws_lambda_function.inventory_consumer / .email_consumer / .analytics_consumer
# aws_lambda_event_source_mapping.inventory / .email / .analytics

terraform state show aws_sqs_queue.inventory
# Shows: redrive_policy with deadLetterTargetArn and maxReceiveCount=3

terraform state show aws_lambda_event_source_mapping.inventory
# Shows: event_source_arn (SQS queue), batch_size=10

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Fan-out Confirmation

```bash
# Place order and immediately check all 3 log groups for simultaneous invocations
curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"fanout@test.com","items":[],"total":0}' > /dev/null

sleep 10

# All 3 should have log entries within seconds of each other
for LAMBDA in handson-inventory-consumer handson-email-consumer handson-analytics-consumer; do
  LAST_EVENT=$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/$LAMBDA \
    --order-by LastEventTime --descending \
    --query "logStreams[0].lastEventTimestamp" --output text)
  echo "$LAMBDA last event: $(python3 -c "import datetime; print(datetime.datetime.fromtimestamp($LAST_EVENT/1000))")"
done
# Expected: all 3 timestamps within seconds of each other (fan-out confirmed)
```

---

## 5. Expected Successful Outputs

**POST /orders (201):**
```json
{ "order_id": "ord-abc123", "status": "processing", "message": "Order placed successfully" }
```

**SNS subscriptions:**
```json
[
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-inventory-queue" },
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-email-queue" },
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-analytics-queue" }
]
```

**Lambda invocations (all 3 fire simultaneously):**
```
handson-inventory-consumer invocations: 1.0
handson-email-consumer invocations: 1.0
handson-analytics-consumer invocations: 1.0
```

---

## 6. Verification Checklist

- [ ] SNS topic has exactly 3 SQS subscriptions
- [ ] Each SQS queue has DLQ configured (maxReceiveCount=3)
- [ ] Each Lambda has SQS event source mapping (batch_size=10)
- [ ] POST /orders returns 201 with order_id
- [ ] All 3 consumer Lambdas invoked within seconds of each order
- [ ] SQS queues empty after processing (messages consumed)
- [ ] Bad message → moves to DLQ after 3 retries
- [ ] DLQ message visible via `sqs receive-message`
- [ ] `terraform plan` shows no changes
