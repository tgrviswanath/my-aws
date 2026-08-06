# Verification & Validation — Project 4.5 SNS/SQS Microservices

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| SNS Topic | SNS → Topics | `handson-orders-events`, Standard type |
| SQS Main Queues | SQS → Queues | `handson-orders-inventory`, `handson-orders-email`, `handson-orders-analytics` |
| DLQ Queues | SQS → Queues | `handson-orders-inventory-dlq`, `handson-orders-email-dlq`, `handson-orders-analytics-dlq` |
| DLQ Config | SQS → Queue → Dead-letter queue tab | DLQ ARN set, maxReceiveCount = 3 |
| SNS Subscriptions | SNS → Topic → Subscriptions | 3 subscriptions, all Protocol = sqs, Status = Confirmed |
| Lambda Consumers | Lambda → Functions → Triggers | Each consumer has SQS trigger attached |
| Lambda Publisher | Lambda → Functions | `handson-orders-publisher`, env var SNS_TOPIC_ARN set |

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
# Expected: 3 entries, all Protocol=sqs pointing to handson-orders-* queues

# 2.2 SQS main queues exist with DLQ configured
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC} --query "QueueUrl" --output text)
  DLQ=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names RedrivePolicy \
    --query "Attributes.RedrivePolicy" --output text)
  echo "handson-orders-${SVC} DLQ policy: $DLQ"
done
# Expected: each queue has RedrivePolicy with maxReceiveCount=3, pointing to corresponding DLQ

# 2.3 Place an order — triggers all 3 consumers
ORDER_ID=$(curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"verify@example.com","items":[{"product_id":"P1","quantity":1,"price":9.99}],"total":9.99}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")
echo "Order placed: $ORDER_ID"

# Wait for all consumers to process
sleep 15

# 2.4 Verify all 3 Lambda functions were invoked (check CloudWatch logs)
for SVC in inventory email analytics; do
  LAST=$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/handson-orders-${SVC}-consumer \
    --order-by LastEventTime --descending --max-items 1 \
    --query "logStreams[0].lastEventTimestamp" --output text 2>/dev/null)
  echo "handson-orders-${SVC}-consumer last log: $LAST"
done
# Expected: recent timestamps for all 3 (within seconds of each other = fan-out confirmed)

# 2.5 SQS queues are empty after processing (messages consumed by Lambda)
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC} --query "QueueUrl" --output text)
  MSGS=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names ApproximateNumberOfMessages \
    --query "Attributes.ApproximateNumberOfMessages" --output text)
  echo "handson-orders-${SVC} messages: $MSGS"
done
# Expected: 0 messages (all processed by Lambda)

# 2.6 DLQ test — publish malformed message that will fail consumers
aws sns publish \
  --topic-arn $SNS_ARN \
  --message '{"invalid":"data that will cause KeyError in consumer"}'
echo "Bad message published — waiting for 3 retries (~3 min)..."
sleep 180

# 2.7 Check DLQ for failed message
DLQ_URL=$(aws sqs get-queue-url --queue-name handson-orders-inventory-dlq \
  --query "QueueUrl" --output text)
aws sqs receive-message --queue-url $DLQ_URL \
  --query "Messages[*].{MessageId:MessageId,Body:Body}"
# Expected: failed message visible in DLQ after 3 failed attempts
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected (for_each resources use map key notation):
# aws_sns_topic.order_events
# aws_sqs_queue.consumer["inventory"]
# aws_sqs_queue.consumer["email"]
# aws_sqs_queue.consumer["analytics"]
# aws_sqs_queue.dlq["inventory"]
# aws_sqs_queue.dlq["email"]
# aws_sqs_queue.dlq["analytics"]
# aws_sqs_queue_policy.consumer["inventory"]
# aws_sqs_queue_policy.consumer["email"]
# aws_sqs_queue_policy.consumer["analytics"]
# aws_sns_topic_subscription.consumer["inventory"]
# aws_sns_topic_subscription.consumer["email"]
# aws_sns_topic_subscription.consumer["analytics"]
# aws_lambda_function.consumer["inventory"]
# aws_lambda_function.consumer["email"]
# aws_lambda_function.consumer["analytics"]
# aws_lambda_event_source_mapping.sqs["inventory"]
# aws_lambda_event_source_mapping.sqs["email"]
# aws_lambda_event_source_mapping.sqs["analytics"]
# aws_lambda_function.publisher
# aws_iam_role.lambda
# aws_iam_role_policy_attachment.lambda_basic
# aws_iam_role_policy.sqs_access
# aws_iam_role_policy.sns_publish
# aws_apigatewayv2_api.main
# aws_apigatewayv2_integration.publisher
# aws_apigatewayv2_route.orders
# aws_apigatewayv2_stage.default
# aws_lambda_permission.api_gw

terraform state show 'aws_sqs_queue.consumer["inventory"]'
# Shows: name=handson-orders-inventory, visibility_timeout_seconds=60, redrive_policy with maxReceiveCount=3

terraform state show 'aws_lambda_event_source_mapping.sqs["inventory"]'
# Shows: event_source_arn (SQS queue ARN), batch_size=10

terraform output
# Expected: api_url, sns_topic_arn, queue_urls (map), dlq_urls (map)

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Fan-out Confirmation

```bash
# Place order and check all 3 Lambda logs fired simultaneously
curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{"customer":"fanout@test.com","items":[],"total":0}' > /dev/null

sleep 15

# Check all 3 log groups for entries within seconds of each other
for SVC in inventory email analytics; do
  LAST=$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/handson-orders-${SVC}-consumer \
    --order-by LastEventTime --descending --max-items 1 \
    --query "logStreams[0].lastEventTimestamp" --output text)
  python3 -c "
import datetime
ts = int('$LAST') / 1000
print('handson-orders-${SVC}-consumer:', datetime.datetime.fromtimestamp(ts))
"
done
# Expected: all 3 timestamps within ~2 seconds of each other = true fan-out
```

---

## 5. Expected Successful Outputs

**POST /orders (201):**
```json
{ "order_id": "uuid-abc-123", "status": "processing" }
```

**SNS subscriptions (3 entries):**
```json
[
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-orders-inventory" },
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-orders-email" },
  { "Protocol": "sqs", "Endpoint": "arn:aws:sqs:...:handson-orders-analytics" }
]
```

**CloudWatch logs — inventory consumer:**
```
[INVENTORY] Processing order uuid-abc-123
  Reducing stock: PROD-001 by 2
[INVENTORY] Done: order uuid-abc-123
```

**CloudWatch logs — email consumer:**
```
[EMAIL] Sending confirmation for order uuid-abc-123
  To: alice@example.com
  Total: $109.97
```

**CloudWatch logs — analytics consumer:**
```
[ANALYTICS] Recording metrics for order uuid-abc-123
  Revenue: $109.97
  Items: 2
```

---

## 6. Verification Checklist

- [ ] SNS topic `handson-orders-events` has exactly 3 SQS subscriptions, Status = Confirmed
- [ ] Main queues: `handson-orders-inventory`, `handson-orders-email`, `handson-orders-analytics`
- [ ] Each main queue has DLQ configured (maxReceiveCount=3, visibilityTimeout=60s)
- [ ] DLQs: `handson-orders-inventory-dlq`, `handson-orders-email-dlq`, `handson-orders-analytics-dlq`
- [ ] Each Lambda has SQS event source mapping (batch_size=10)
- [ ] POST /orders returns 201 with `{"order_id": "...", "status": "processing"}`
- [ ] All 3 consumer Lambdas invoked within seconds of each order
- [ ] SQS main queues empty after processing (messages consumed)
- [ ] Bad message → all 3 consumers fail → moves to DLQs after 3 retries
- [ ] DLQ message visible via `sqs receive-message`
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
