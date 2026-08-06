# Project 4.5 — SNS/SQS Microservices
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** Async Microservices with SNS Fan-out + SQS + Dead Letter Queues

**Business / Problem Statement:**
In a monolithic app, when an order is placed, the same function updates inventory, sends an email, and records analytics — all synchronously. If the email service is slow, the customer waits. If analytics is down, the order fails. Microservices with message queues solve this: the order service publishes one event, and independent services consume it at their own pace. This project builds a real-world order processing pipeline where one SNS publish triggers three independent Lambda consumers via SQS queues — with built-in retry logic and Dead Letter Queues for failure handling.

**Learning Objectives:**
- Understand SNS fan-out pattern (1 publish → many subscribers)
- Understand SQS visibility timeout and retry behavior
- Configure Dead Letter Queues (DLQ) for failed message handling
- Build Lambda functions triggered by SQS events
- Understand the difference between SNS and SQS and when to use each
- Practice designing for idempotency (safe to process same message twice)

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| SNS Topic | Pub/Sub hub — publishes one message to all subscribers |
| SQS Queues (×3) | Buffers messages for each consumer service |
| SQS DLQ (×3) | Receives messages that failed after max retries |
| Lambda (×3) | Consumer functions — inventory, email, analytics |
| API Gateway | Receives order requests, triggers publisher Lambda |

**SNS Fan-out Architecture:**
```
POST /orders
      │
      ▼
 Order Lambda ──publish──► SNS Topic: handson-orders-events
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
        SQS: handson-orders-inventory   SQS: handson-orders-email   SQS: handson-orders-analytics
        + DLQ                           + DLQ                       + DLQ
               │                │                │
               ▼                ▼                ▼
        Lambda:           Lambda:          Lambda:
        inventory_handler email_handler    analytics_handler
        (update stock)    (send email)     (record metrics)
```

**Message Flow with Retry:**
```
SNS delivers to SQS queue
    │
Lambda polls SQS (auto-managed)
    │
    ├── SUCCESS → message deleted from queue ✅
    └── FAILURE → message becomes visible again after visibility timeout
                  → retried up to maxReceiveCount (3) times
                  → after 3 failures → moved to DLQ ⚠️
```

**Best Practices Followed:**
- SQS visibility timeout > Lambda timeout (prevents duplicate processing)
- DLQ retention = 14 days (time to investigate and replay)
- Lambda re-raises exceptions (triggers SQS retry instead of silent failure)
- Idempotent consumers (processing same message twice = same result)
- SNS filter policies can route messages to specific queues (not used here but pattern to know)

---

## 3. Prerequisites

Same as Project 4.1. No additional libraries needed (consumers use only boto3).

**Key Concepts to Understand:**

| Concept | Explanation |
|---------|-------------|
| SQS Visibility Timeout | How long message is hidden from other consumers while being processed |
| MaxReceiveCount | How many times SQS delivers a message before sending to DLQ |
| Batch Size | How many SQS messages Lambda processes per invocation (max 10) |
| SNS Message Envelope | SNS wraps messages in JSON — `{"Message": "{...actual payload...}"}` |

---

## 4. Project Folder Structure

```
project_4.5_sns_sqs_microservices/
│
├── README.md               ← Fan-out architecture, SQS concepts, lessons learned
├── GUIDE.md                ← This file
├── steps.md                ← Deploy, place order, verify fan-out, DLQ test
├── verify.md               ← 3 Lambda logs simultaneously, DLQ message check
├── cost_estimate.md        ← $0 (all free tier)
│
├── src/
│   ├── consumers.py        ← inventory_handler, email_handler, analytics_handler
│   └── order_publisher.py  ← Publishes order event to SNS
│
├── docs/
│   └── architecture.md     ← Fan-out diagram, SQS retry flow, DLQ pattern
│
└── terraform/
    └── main.tf             ← SNS, SQS ×3, DLQ ×3, subscriptions, Lambda ×3+1
```

---

## 5. Project Input & Output

**INPUT:**
```
POST /orders
{
  "customer": "alice@example.com",
  "items": [
    {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
    {"product_id": "PROD-002", "quantity": 1, "price": 49.99}
  ],
  "total": 109.97
}
```

**OUTPUT — API:**
```json
201 Created
{"order_id": "ord-abc123-uuid", "status": "processing"}
```

**OUTPUT — SNS message published:**
```json
{
  "order_id": "ord-abc123-uuid",
  "customer": "alice@example.com",
  "items": [...],
  "total": 109.97,
  "created_at": "2024-01-15T12:00:00Z"
}
```

**OUTPUT — Lambda logs (all 3 fire within seconds):**
```
[INVENTORY] Processing order ord-abc123 → Reducing stock: PROD-001 by 2
[EMAIL]     Sending confirmation to alice@example.com — Total: $109.97
[ANALYTICS] Recording metrics — Revenue: $109.97, Items: 2
```

**OUTPUT — DLQ (on failure):**
```
SQS message appears in handson-orders-inventory-dlq after 3 failed attempts
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create SNS Topic

**Prerequisites Check:**
- ✅ Required permissions: `sns:CreateTopic`, `sns:Subscribe`
- ✅ Services enabled: Amazon SNS
- ✅ Region: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [SNS Console](https://console.aws.amazon.com/sns)
2. Click **Topics** in left sidebar
3. Click **Create topic**

**Step 1.2: Make Selections**

**Decision Point 1:** Topic Type

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Standard | High throughput, at-least-once, any order | ✅ Use this |
| FIFO | Strict ordering, exactly-once | ❌ Not needed (SQS handles ordering) |

Select **Standard**

**Step 1.3: Configure**

| Field | Value |
|-------|-------|
| Name | `handson-orders-events` |
| Display name | `Order Events` |
| Encryption | Disabled (lab simplicity) |
| Access policy | Default |

Click **Create topic** → Copy the **Topic ARN** — needed for subscriptions and Lambda env var.

**📸 Screenshot:** SNS topic created showing Topic ARN

---

#### Step 2 — Create SQS Queues and DLQs

You need to create 6 queues total: 3 DLQs first, then 3 main queues.

**Step 2.1: Navigate**
1. Go to [SQS Console](https://console.aws.amazon.com/sqs)
2. Click **Create queue**

**Step 2.2: Create DLQs First (DLQs must exist before main queues can reference them)**

**Decision Point 1:** Queue Type

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Standard | High throughput, best-effort ordering | ✅ Use this |
| FIFO | Strict ordering, exactly-once | ❌ Would require SNS FIFO topic too |

For each DLQ (repeat 3 times):

| Queue Name | Visibility Timeout | Message Retention |
|------------|-------------------|------------------|
| `handson-orders-inventory-dlq` | 30 seconds | 14 days |
| `handson-orders-email-dlq` | 30 seconds | 14 days |
| `handson-orders-analytics-dlq` | 30 seconds | 14 days |

Click **Create queue** for each.

**Step 2.3: Create Main Queues with DLQ Redrive Policy**

For each main queue (repeat 3 times):

| Queue Name | DLQ |
|------------|-----|
| `handson-orders-inventory` | `handson-orders-inventory-dlq` |
| `handson-orders-email` | `handson-orders-email-dlq` |
| `handson-orders-analytics` | `handson-orders-analytics-dlq` |

**Decision Point 2:** Visibility Timeout

| Value | Risk |
|-------|------|
| Less than Lambda timeout | Message processed twice (Lambda still running, SQS makes it visible again) |
| Equal to Lambda timeout | Borderline — risky |
| Greater than Lambda timeout | ✅ Safe — message stays hidden until Lambda finishes |

Set Visibility Timeout: **60 seconds** (Lambda timeout = 30s, so 60s provides safety margin)

**Decision Point 3:** Dead Letter Queue Configuration

| Field | Value | Explanation |
|-------|-------|-------------|
| Dead-letter queue | ✅ Enabled | |
| Choose queue | corresponding DLQ (e.g. `handson-orders-inventory-dlq`) | |
| Maximum receives | `3` | Retry 3 times before DLQ |

**📸 Screenshot:** SQS queue creation showing DLQ configuration with maxReceiveCount=3

---

#### Step 3 — Subscribe SQS Queues to SNS Topic

For each SQS queue, subscribe it to the SNS topic:

**Step 3.1: Navigate**
1. Go back to SNS Console → `handson-orders-events` topic
2. Click **Create subscription**

**Step 3.2: Configure (repeat for all 3 queues)**

| Field | Value |
|-------|-------|
| Protocol | **Amazon SQS** |
| Endpoint | ARN of the SQS queue |

Copy each queue ARN from SQS console.

**Important:** After creating each subscription, go to the SQS queue and add a policy allowing SNS to send messages.

**Expected SQS access policy (update Resource and SourceArn for each queue):**
```json
{
  "Effect": "Allow",
  "Principal": {"Service": "sns.amazonaws.com"},
  "Action": "sqs:SendMessage",
  "Resource": "arn:aws:sqs:us-east-1:ACCOUNT:handson-orders-inventory",
  "Condition": {
    "ArnEquals": {"aws:SourceArn": "arn:aws:sns:us-east-1:ACCOUNT:handson-orders-events"}
  }
}
```

**📸 Screenshot:** SNS topic Subscriptions tab showing all 3 SQS subscriptions with Status = Confirmed

---

#### Step 4 — Deploy Lambda Consumer Functions

Deploy 3 Lambda functions from `src/consumers.py`:

| Function Name | Handler | SQS Queue |
|---------------|---------|-----------|
| `handson-orders-inventory-consumer` | `consumers.inventory_handler` | `handson-orders-inventory` |
| `handson-orders-email-consumer` | `consumers.email_handler` | `handson-orders-email` |
| `handson-orders-analytics-consumer` | `consumers.analytics_handler` | `handson-orders-analytics` |

For each:
1. Create Lambda function with the name and handler above
2. Paste `src/consumers.py` as code
3. Set handler to the appropriate function name
4. Timeout: 30s
5. Add SQS Event Source Mapping (see Step 5)

---

#### Step 5 — Add SQS Triggers to Lambda Functions

For each Lambda consumer:

1. Go to Lambda → function → **Configuration** → **Triggers**
2. Click **Add trigger**
3. Select **SQS**

**Decision Point 1:** Batch Size

| Batch Size | Use Case | For This Project |
|------------|----------|-----------------|
| 1 | Process one message at a time, easier debugging | ✅ Use for learning |
| 10 | Efficient bulk processing | ✅ Default, good for production |

| Field | Value |
|-------|-------|
| SQS queue | Select corresponding queue (e.g. `handson-orders-inventory`) |
| Batch size | 10 |
| Batch window | 0 seconds |

**📸 Screenshot:** Lambda function showing SQS trigger with queue name

---

#### Step 6 — Deploy Publisher Lambda and API

Deploy `src/order_publisher.py` as `handson-orders-publisher`:

| Setting | Value |
|---------|-------|
| Function name | `handson-orders-publisher` |
| Handler | `order_publisher.handler` |
| Environment variable `SNS_TOPIC_ARN` | ARN of `handson-orders-events` |

Create API Gateway HTTP API with route `POST /orders` → `handson-orders-publisher`.

### METHOD B — AWS CLI Method

```bash
# ── Set variables ─────────────────────────────────────────────────────────────
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT="handson-orders"

# ── 1. Create SNS Topic ───────────────────────────────────────────────────────
SNS_ARN=$(aws sns create-topic \
  --name ${PROJECT}-events \
  --query TopicArn --output text)

echo "✅ SNS Topic ARN: $SNS_ARN"

# ── 2. Create DLQs (must exist before main queues reference them) ─────────────
for SVC in inventory email analytics; do
  aws sqs create-queue \
    --queue-name ${PROJECT}-${SVC}-dlq \
    --attributes MessageRetentionPeriod=1209600   # 14 days
  echo "✅ DLQ created: ${PROJECT}-${SVC}-dlq"
done

# Get DLQ ARNs
INV_DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name ${PROJECT}-inventory-dlq --query QueueUrl --output text) \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)
EMAIL_DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name ${PROJECT}-email-dlq --query QueueUrl --output text) \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)
ANALYTICS_DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name ${PROJECT}-analytics-dlq --query QueueUrl --output text) \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)

# ── 3. Create main queues with redrive policy ─────────────────────────────────
declare -A DLQ_ARNS=(
  ["inventory"]="$INV_DLQ_ARN"
  ["email"]="$EMAIL_DLQ_ARN"
  ["analytics"]="$ANALYTICS_DLQ_ARN"
)

declare -A QUEUE_ARNS=()
declare -A QUEUE_URLS=()

for SVC in inventory email analytics; do
  QUEUE_URL=$(aws sqs create-queue \
    --queue-name ${PROJECT}-${SVC} \
    --attributes "VisibilityTimeout=60,MessageRetentionPeriod=345600,RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARNS[$SVC]}\",\"maxReceiveCount\":\"3\"}" \
    --query QueueUrl --output text)

  QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query Attributes.QueueArn --output text)

  QUEUE_ARNS[$SVC]=$QUEUE_ARN
  QUEUE_URLS[$SVC]=$QUEUE_URL

  # Allow SNS to send messages to this queue
  aws sqs set-queue-attributes \
    --queue-url $QUEUE_URL \
    --attributes "Policy={\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"$QUEUE_ARN\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"$SNS_ARN\"}}}]}"

  echo "✅ Queue created: ${PROJECT}-${SVC}"
done

# ── 4. Subscribe all queues to SNS topic ──────────────────────────────────────
for SVC in inventory email analytics; do
  aws sns subscribe \
    --topic-arn $SNS_ARN \
    --protocol sqs \
    --notification-endpoint ${QUEUE_ARNS[$SVC]}
  echo "✅ Subscribed: ${PROJECT}-${SVC} → SNS"
done

# Verify 3 subscriptions
aws sns list-subscriptions-by-topic --topic-arn $SNS_ARN \
  --query "Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint}"
# Expected: 3 rows, all Protocol=sqs

# ── 5. Create Lambda IAM role ─────────────────────────────────────────────────
ROLE_ARN=$(aws iam get-role --role-name handson-lambda-exec-role \
  --query Role.Arn --output text 2>/dev/null)

if [ -z "$ROLE_ARN" ]; then
  ROLE_ARN=$(aws iam create-role \
    --role-name handson-lambda-exec-role \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
    --query Role.Arn --output text)
  aws iam attach-role-policy --role-name handson-lambda-exec-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  sleep 10
fi
echo "Role ARN: $ROLE_ARN"

# ── 6. Deploy consumer Lambda functions ──────────────────────────────────────
cd src && zip ../consumers.zip consumers.py && cd ..

declare -A HANDLER_MAP=(
  ["inventory"]="consumers.inventory_handler"
  ["email"]="consumers.email_handler"
  ["analytics"]="consumers.analytics_handler"
)

for SVC in inventory email analytics; do
  aws lambda create-function \
    --function-name ${PROJECT}-${SVC}-consumer \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler ${HANDLER_MAP[$SVC]} \
    --zip-file fileb://consumers.zip \
    --timeout 30
  aws lambda wait function-active --function-name ${PROJECT}-${SVC}-consumer
  echo "✅ Lambda deployed: ${PROJECT}-${SVC}-consumer"
done

# ── 7. Connect SQS queues to Lambda (event source mapping) ────────────────────
for SVC in inventory email analytics; do
  LAMBDA_ARN=$(aws lambda get-function \
    --function-name ${PROJECT}-${SVC}-consumer \
    --query Configuration.FunctionArn --output text)
  aws lambda create-event-source-mapping \
    --function-name ${PROJECT}-${SVC}-consumer \
    --event-source-arn ${QUEUE_ARNS[$SVC]} \
    --batch-size 10
  echo "✅ SQS trigger connected: ${PROJECT}-${SVC} → Lambda"
done

# ── 8. Deploy publisher Lambda + API Gateway ──────────────────────────────────
cd src && zip ../publisher.zip order_publisher.py && cd ..

aws lambda create-function \
  --function-name ${PROJECT}-publisher \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler order_publisher.handler \
  --zip-file fileb://publisher.zip \
  --timeout 30 \
  --environment Variables="{SNS_TOPIC_ARN=$SNS_ARN}"

aws lambda wait function-active --function-name ${PROJECT}-publisher

PUBLISHER_ARN=$(aws lambda get-function \
  --function-name ${PROJECT}-publisher \
  --query Configuration.FunctionArn --output text)

API_ID=$(aws apigatewayv2 create-api \
  --name ${PROJECT}-api \
  --protocol-type HTTP \
  --query ApiId --output text)

INT_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $PUBLISHER_ARN \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "POST /orders" \
  --target "integrations/$INT_ID"

aws apigatewayv2 create-stage \
  --api-id $API_ID --stage-name '$default' --auto-deploy

aws lambda add-permission \
  --function-name ${PROJECT}-publisher \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"

API_URL=$(aws apigatewayv2 get-api --api-id $API_ID \
  --query ApiEndpoint --output text)
echo "✅ All resources deployed!"
echo "API URL: $API_URL"
```

---

## 7. Code Deep Dive

**`src/order_publisher.py` — Publisher Lambda:**

```python
# sns.publish() — sends one message to ALL subscribers simultaneously
sns.publish(
    TopicArn=SNS_TOPIC_ARN,
    Message=json.dumps(order),       # Actual payload — serialized to JSON string
    Subject="NewOrder",              # Optional — appears in email notifications
    MessageAttributes={
        "event_type": {
            "DataType": "String",
            "StringValue": "ORDER_CREATED",
        }
    },
)
# MessageAttributes allow SNS filter policies:
# A subscriber can say "only send me messages where event_type=ORDER_CANCELLED"
# Without filter policies, ALL subscribers get ALL messages (our case here)
```

**`src/consumers.py` — Consumer Lambdas:**

```python
# parse_order() — CRITICAL: SNS wraps messages in an envelope when delivering to SQS
def parse_order(record: dict) -> dict:
    sqs_body = json.loads(record["body"])      # SQS body is a JSON string
    if "Message" in sqs_body:
        return json.loads(sqs_body["Message"]) # SNS envelope: actual payload is in "Message"
    return sqs_body                            # Direct SQS message (no SNS envelope)

# The full SQS record["body"] looks like this when coming from SNS:
# {
#   "Type": "Notification",
#   "TopicArn": "arn:aws:sns:...",
#   "Subject": "NewOrder",
#   "Message": "{\"order_id\": \"abc\", ...}",  ← actual payload (double-encoded!)
#   "Timestamp": "2024-01-15T12:00:00Z",
#   "MessageId": "uuid"
# }
# You MUST parse record["body"] first, then parse ["Message"] again
```

```python
# Re-raise exceptions — ESSENTIAL for DLQ to work correctly
except Exception as e:
    print(f"[INVENTORY] Error: {e}")
    raise  # ← This is critical!
# If you DON'T raise: Lambda returns success → SQS deletes the message → data LOST silently
# If you DO raise: Lambda returns failure → SQS keeps message → retries up to maxReceiveCount → DLQ
```

**Terraform Resources Cross-Reference:**

| Terraform Resource | Purpose | Key Config |
|-------------------|---------|-----------|
| `aws_sns_topic.order_events` | SNS fan-out hub | Standard type |
| `aws_sqs_queue.dlq[each]` | Dead letter queue per service | Retention 14 days |
| `aws_sqs_queue.consumer[each]` | Main queue per service | `redrive_policy` points to DLQ, maxReceiveCount=3 |
| `aws_sqs_queue_policy.consumer[each]` | Allow SNS to write to SQS | Source condition = SNS ARN |
| `aws_sns_topic_subscription.consumer[each]` | Wire SNS → SQS | Protocol = "sqs" |
| `aws_lambda_function.consumer[each]` | One Lambda per service | Handler matches function in consumers.py |
| `aws_lambda_event_source_mapping.sqs[each]` | SQS polls → Lambda | batch_size=10 |
| `aws_lambda_function.publisher` | Order publisher | `SNS_TOPIC_ARN` env var |

**Common Mistakes:**

| Mistake | Fix |
|---------|-----|
| Forgetting SQS queue policy | SNS cannot deliver messages — subscription confirmed but no messages arrive |
| Visibility timeout ≤ Lambda timeout | Message processed twice by concurrent Lambda invocations |
| Not re-raising exceptions | Failures silently swallowed — DLQ never receives messages |
| Parsing SNS body as direct order | Double-encoded JSON — must parse `sqs_body["Message"]` again |
| DLQ created after main queue | Terraform/console redrive policy requires DLQ to exist first |

---

## 8. Verification & Validation

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"
SNS_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn,'handson-orders')].TopicArn" --output text)

# 1. Verify SNS has 3 SQS subscriptions
aws sns list-subscriptions-by-topic --topic-arn $SNS_ARN \
  --query "Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint}" --output table
# Expected: 3 rows, Protocol=sqs for all

# 2. Verify DLQ is configured on each queue
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC} --query QueueUrl --output text)
  POLICY=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names RedrivePolicy --query "Attributes.RedrivePolicy" --output text)
  echo "$SVC DLQ policy: $POLICY"
done
# Expected: JSON with deadLetterTargetArn and maxReceiveCount=3 for each

# 3. Place a real order and watch the fan-out
ORDER_ID=$(curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "alice@example.com",
    "items": [
      {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
      {"product_id": "PROD-002", "quantity": 1, "price": 49.99}
    ],
    "total": 109.97
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")
echo "Order placed: $ORDER_ID"

# Wait for all 3 Lambda consumers to process
sleep 15

# 4. Check all 3 Lambda logs fired simultaneously
for SVC in inventory email analytics; do
  echo "=== $SVC logs ==="
  aws logs tail /aws/lambda/handson-orders-${SVC}-consumer --since 2m 2>/dev/null | head -5
done
# Expected: [INVENTORY] Processing order ... / [EMAIL] Sending ... / [ANALYTICS] Recording ...

# 5. Verify queues are empty (messages consumed)
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC} --query QueueUrl --output text)
  COUNT=$(aws sqs get-queue-attributes --queue-url $URL \
    --attribute-names ApproximateNumberOfMessages \
    --query "Attributes.ApproximateNumberOfMessages" --output text)
  echo "handson-orders-${SVC} messages remaining: $COUNT"
done
# Expected: 0 for all queues

# 6. Test DLQ — publish malformed message that will fail consumers
aws sns publish \
  --topic-arn $SNS_ARN \
  --message '{"bad_field": "this will cause KeyError in consumers"}'
echo "Bad message published — waiting for 3 retries..."
sleep 90   # visibility timeout × 3 retries

# 7. Check DLQ for failed message
DLQ_URL=$(aws sqs get-queue-url --queue-name handson-orders-inventory-dlq --query QueueUrl --output text)
aws sqs receive-message --queue-url $DLQ_URL \
  --query "Messages[*].{MessageId:MessageId,Body:Body}"
# Expected: message visible in DLQ after 3 failed delivery attempts
```

**Console Verification:**

| Resource | Where to Check | Expected State |
|----------|---------------|---------------|
| SNS Topic | SNS → Topics | `handson-orders-events`, Standard type |
| SNS Subscriptions | Topic → Subscriptions tab | 3 subscriptions, all Protocol=sqs, Status=Confirmed |
| SQS Queues | SQS → Queues | 3 main + 3 DLQ = 6 queues |
| DLQ Config | Queue → Dead-letter queue tab | DLQ ARN set, maxReceiveCount=3 |
| Lambda Triggers | Lambda → Configuration → Triggers | SQS trigger shown for each consumer |
| CloudWatch | CloudWatch → Log Groups | `/aws/lambda/handson-orders-*-consumer` for all 3 |

---

## 9. Observations & Learning Notes

1. **Fan-out is simultaneous:** When SNS delivers to SQS, all 3 queues receive the message within milliseconds. Lambda then processes them in parallel. Check CloudWatch log timestamps — all 3 consumers log within ~1 second of each other.

2. **Lambda polling SQS:** Lambda does NOT push to SQS — Lambda service polls SQS every few seconds. This is invisible to you. The `event_source_mapping` resource tells Lambda which queue to poll and with what batch size.

3. **SQS batching:** With `batch_size=10`, if 10 orders arrive quickly, Lambda processes them in one invocation with 10 records in `event["Records"]`. Each record is one SQS message.

4. **Visibility timeout gap:** If Lambda takes 25s to process and visibility timeout is 30s, the message becomes visible again with only 5s for Lambda to finish. A crash at second 29 = duplicate processing. Always set visibility timeout to 6× Lambda timeout for safety.

5. **SNS raw message delivery:** By default, SNS wraps messages in an envelope (Type, Subject, Message, etc.). Enable "Raw message delivery" on the subscription to skip the envelope — then `record["body"]` IS the order directly. Terraform supports this via `raw_message_delivery = true` on `aws_sns_topic_subscription`.

6. **DLQ alarm:** In production, always set a CloudWatch alarm on `NumberOfMessagesSent` to DLQ. A message in the DLQ means a consumer has a bug — you want to know immediately.

---

## 10. Screenshots Guidance

| When | What to Capture |
|------|----------------|
| After Step 1 | SNS topic created with ARN |
| After Step 2 | SQS queue list showing all 6 queues (3 main + 3 DLQ) |
| After Step 2.3 | DLQ tab in queue settings showing maxReceiveCount=3 |
| After Step 3 | SNS Subscriptions tab showing 3 Confirmed SQS subscriptions |
| After Step 5 | Each Lambda showing SQS trigger in Triggers tab |
| Testing | POST /orders returning 201 with order_id |
| Testing | CloudWatch showing all 3 Lambda logs with matching order_id |
| Testing | Parallel timestamps confirming simultaneous execution |
| DLQ test | SQS DLQ console showing failed message after retries |

---

## 11. Cleanup Steps

```bash
# Order matters — subscriptions before topic, queues after mappings

# 1. Delete Lambda event source mappings
for SVC in inventory email analytics; do
  UUID=$(aws lambda list-event-source-mappings \
    --function-name handson-orders-${SVC}-consumer \
    --query "EventSourceMappings[0].UUID" --output text)
  aws lambda delete-event-source-mapping --uuid $UUID
done

# 2. Delete SNS subscriptions
for SUB_ARN in $(aws sns list-subscriptions-by-topic --topic-arn $SNS_ARN \
  --query "Subscriptions[*].SubscriptionArn" --output text); do
  aws sns unsubscribe --subscription-arn $SUB_ARN
done

# 3. Delete SNS topic
aws sns delete-topic --topic-arn $SNS_ARN

# 4. Delete Lambda functions
for SVC in inventory email analytics; do
  aws lambda delete-function --function-name handson-orders-${SVC}-consumer
done
aws lambda delete-function --function-name handson-orders-publisher

# 5. Delete SQS queues (DLQs after main queues)
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC} --query QueueUrl --output text 2>/dev/null)
  [ -n "$URL" ] && aws sqs delete-queue --queue-url $URL
done
for SVC in inventory email analytics; do
  URL=$(aws sqs get-queue-url --queue-name handson-orders-${SVC}-dlq --query QueueUrl --output text 2>/dev/null)
  [ -n "$URL" ] && aws sqs delete-queue --queue-url $URL
done

# 6. Delete API Gateway
aws apigatewayv2 delete-api --api-id $API_ID

echo "✅ All SNS/SQS resources deleted"

# 7. Verify cost is zero
aws sqs list-queues --queue-name-prefix handson-orders
# Expected: empty
```

---

## 12. Estimated AWS Cost

| Resource | Free Tier | Notes |
|----------|-----------|-------|
| SNS (publishes) | 1M free/month — permanent | |
| SQS (requests) | 1M free/month — permanent | Each poll counts as a request |
| Lambda (×4 functions) | 1M requests/month free | |
| API Gateway | 1M calls/month free (12 months) | |
| **Total for lab** | **$0** | All within free tier |

> ✅ **Fully Free Tier Eligible.** SNS and SQS free tiers are permanent (not 12-month). At lab scale this project costs nothing.

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
