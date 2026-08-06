# Project 4.5 — SNS/SQS Microservices
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create SNS Topic

**Prerequisites Check:**
- ✅ Required permissions: `sns:CreateTopic`
- ✅ Services enabled: Amazon SNS
- ✅ Region availability: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [SNS Console](https://console.aws.amazon.com/sns)
2. Click **Topics** in left sidebar
3. **Expected View:** Topics list with "Create topic" button

**Step 1.2: Make Selections**

Click **Create topic**

**Decision Point 1:** Topic Type

| Option | Ordering | Delivery | For This Project |
|--------|----------|----------|-----------------|
| Standard | Best-effort | At-least-once | ✅ Use this — works with Standard SQS |
| FIFO | Strict order | Exactly-once | ❌ Requires FIFO SQS too, higher complexity |

Select **Standard**

**Step 1.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `handson-orders-events` | Topic name |
| Display name | `Order Events` | Visible in email notifications |
| Encryption | *(leave default)* | Not needed for lab |

Click **Create topic**

**Step 1.4: Validate Result**

**Expected Outcome:** Topic created. Copy the **Topic ARN** — you'll need it for subscriptions and Lambda env var.

**📸 Screenshot:** SNS topic detail page showing Topic ARN

---

#### Step 2 — Create DLQs First (must exist before main queues reference them)

**Prerequisites Check:**
- ✅ Required permissions: `sqs:CreateQueue`
- ✅ Services enabled: Amazon SQS

**Step 2.1: Navigate**
1. Go to [SQS Console](https://console.aws.amazon.com/sqs)
2. Click **Create queue** (you will do this 6 times total — 3 DLQs + 3 main queues)

**Step 2.2: Create Each DLQ**

**Decision Point 1:** Queue Type

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Standard | High throughput, best-effort ordering | ✅ Use this |
| FIFO | Strict ordering, exactly-once | ❌ Would require SNS FIFO topic |

For each of the 3 DLQs (repeat Create queue 3 times):

| Queue Name | Visibility Timeout | Message Retention |
|------------|-------------------|------------------|
| `handson-orders-inventory-dlq` | 30s | 14 days (maximum) |
| `handson-orders-email-dlq` | 30s | 14 days |
| `handson-orders-analytics-dlq` | 30s | 14 days |

Click **Create queue** for each.

**📸 Screenshot:** SQS queue list showing all 3 DLQs created

---

#### Step 3 — Create Main Queues with DLQ Redrive Policy

**Step 3.1: Create Each Main Queue**

For each of the 3 main queues (repeat Create queue 3 times):

| Queue Name |
|------------|
| `handson-orders-inventory` |
| `handson-orders-email` |
| `handson-orders-analytics` |

**Decision Point 2:** Visibility Timeout

| Value | Scenario | Risk |
|-------|----------|------|
| < Lambda timeout (30s) | Message becomes visible while Lambda still processing | ❌ Same message processed twice |
| = Lambda timeout | Borderline — risky on slow invocations | ❌ Not safe |
| > Lambda timeout | Message stays hidden until Lambda finishes | ✅ Set to 60s |

Set **Visibility timeout: 60 seconds** for each main queue.

**Step 3.2: Configure Dead-Letter Queue**

For each main queue, in the **Dead-letter queue** section:

| Setting | Value | Explanation |
|---------|-------|-------------|
| Dead-letter queue | ✅ Enabled | |
| Choose queue | Corresponding DLQ (e.g. `handson-orders-inventory-dlq`) | |
| Maximum receives | `3` | Retry 3 times before DLQ |

**📸 Screenshot:** Main queue creation showing Dead-letter queue configured with maxReceiveCount=3

---

#### Step 4 — Subscribe SQS Queues to SNS Topic

For each of the 3 main queues, create an SNS subscription:

**Step 4.1: Navigate to SNS Topic**
1. SNS Console → Topics → `handson-orders-events`
2. Click **Create subscription**

**Step 4.2: Configure (repeat for all 3 queues)**

| Field | Value |
|-------|-------|
| Protocol | **Amazon SQS** |
| Endpoint | ARN of the SQS queue (copy from SQS console) |

| Queue | ARN format |
|-------|-----------|
| inventory | `arn:aws:sqs:us-east-1:ACCOUNT:handson-orders-inventory` |
| email | `arn:aws:sqs:us-east-1:ACCOUNT:handson-orders-email` |
| analytics | `arn:aws:sqs:us-east-1:ACCOUNT:handson-orders-analytics` |

Click **Create subscription** for each.

**Step 4.3: Add SQS Access Policy for SNS**

For each main queue, you must allow SNS to send messages to it:

1. SQS Console → click queue → **Access policy** tab → **Edit**
2. Add this policy (replace ARNs with your values):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sns.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:handson-orders-inventory",
    "Condition": {
      "ArnEquals": {
        "aws:SourceArn": "arn:aws:sns:us-east-1:ACCOUNT_ID:handson-orders-events"
      }
    }
  }]
}
```

> Repeat for `handson-orders-email` and `handson-orders-analytics` queues, updating the `Resource` ARN each time.

**Step 4.4: Validate**

SNS Console → `handson-orders-events` → **Subscriptions** tab

**Expected Outcome:** 3 subscriptions, all Protocol = `sqs`, Status = `Confirmed`

**📸 Screenshot:** SNS topic Subscriptions tab showing all 3 SQS subscriptions Confirmed

---

#### Step 5 — Deploy Lambda Consumer Functions

All 3 consumer handlers are in `src/consumers.py`. Deploy 3 separate Lambda functions pointing to different handlers in the same file.

**Step 5.1: Create Each Consumer Lambda (repeat 3 times)**

Lambda Console → **Create function** → Author from scratch

| Function Name | Handler | SQS Queue |
|---------------|---------|-----------|
| `handson-orders-inventory-consumer` | `consumers.inventory_handler` | `handson-orders-inventory` |
| `handson-orders-email-consumer` | `consumers.email_handler` | `handson-orders-email` |
| `handson-orders-analytics-consumer` | `consumers.analytics_handler` | `handson-orders-analytics` |

For each:
- Runtime: Python 3.11
- Execution role: `handson-lambda-exec-role`
- Paste entire `src/consumers.py` as code
- Set handler to the specific handler name above
- Timeout: 30s
- Click **Deploy**

**📸 Screenshot:** Lambda functions list showing all 3 `handson-orders-*-consumer` functions

**Step 5.2: Add SQS Trigger to Each Consumer Lambda**

For each consumer Lambda:

1. Lambda → click function → **Configuration** → **Triggers** → **Add trigger**
2. Select **SQS**

**Decision Point 1:** Batch Size

| Batch Size | Use Case | For This Project |
|------------|----------|-----------------|
| 1 | Process one at a time, easiest to debug | ✅ Good for learning |
| 10 | Efficient bulk processing | ✅ Default — use in production |

| Field | Value |
|-------|-------|
| SQS queue | Select the corresponding queue |
| Batch size | 10 |
| Batch window | 0 seconds |

Click **Add**

**📸 Screenshot:** Consumer Lambda showing SQS trigger with queue name and batch size

---

#### Step 6 — Deploy Publisher Lambda and API

**Step 6.1: Create Publisher Lambda**

Lambda Console → **Create function**

| Field | Value |
|-------|-------|
| Function name | `handson-orders-publisher` |
| Runtime | Python 3.11 |
| Execution role | `handson-lambda-exec-role` (needs SNS publish permission) |

Paste `src/order_publisher.py` → Deploy

Environment variables:

| Key | Value |
|-----|-------|
| `SNS_TOPIC_ARN` | ARN of `handson-orders-events` (from Step 1.4) |

**Step 6.2: Create API Gateway**

API Gateway → HTTP API → Build

- Integration: Lambda → `handson-orders-publisher`
- API name: `handson-orders-api`
- Route: `POST /orders` → `handson-orders-publisher`
- Stage: `$default` → Create

**Step 6.3: Add SNS Publish Permission to Lambda Role**

Lambda needs permission to publish to SNS. Go to IAM → Role `handson-lambda-exec-role` → Add inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["sns:Publish"],
    "Resource": "arn:aws:sns:us-east-1:ACCOUNT_ID:handson-orders-events"
  }]
}
```

---

#### Step 7 — Test the Fan-out Pipeline

**Step 7.1: Place an Order**

```bash
API_URL="https://YOUR_ID.execute-api.us-east-1.amazonaws.com"

curl -s -X POST $API_URL/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer\": \"alice@example.com\",
    \"items\": [{\"product_id\": \"PROD-001\", \"quantity\": 2, \"price\": 29.99}],
    \"total\": 59.98
  }"
# Expected: {"order_id": "uuid", "status": "processing"}
```

**📸 Screenshot:** POST /orders returning 201 with order_id

**Step 7.2: Verify All 3 Consumers Fired**

Wait 10-15 seconds, then check CloudWatch:

1. CloudWatch → Log groups
2. Check ALL THREE log groups within seconds of each other:
   - `/aws/lambda/handson-orders-inventory-consumer`
   - `/aws/lambda/handson-orders-email-consumer`
   - `/aws/lambda/handson-orders-analytics-consumer`

**Decision Point 2:** What confirms fan-out?

| Observation | What it means |
|-------------|--------------|
| All 3 logs have entries with same order_id | ✅ Fan-out worked correctly |
| Only 1 or 2 logs have entries | ❌ Check SNS subscriptions and SQS access policy |
| All 3 logs have entries but timestamps differ by >10s | ❌ Not true fan-out — check SNS subscriptions |

**📸 Screenshot:** CloudWatch showing all 3 Lambda log groups with matching order_id and near-identical timestamps

**Step 7.3: Test DLQ**

```bash
# Send a bad message that will cause all consumers to fail
SNS_ARN="arn:aws:sns:us-east-1:ACCOUNT_ID:handson-orders-events"
aws sns publish \
  --topic-arn $SNS_ARN \
  --message '{"bad_field": "this causes KeyError in consumer"}'
```

Wait ~3 minutes (3 retries × 60s visibility timeout), then:

1. SQS Console → `handson-orders-inventory-dlq`
2. Click **Send and receive messages** → **Poll for messages**
3. **Expected Outcome:** Failed message visible in DLQ

**📸 Screenshot:** SQS DLQ showing failed message after retries exhausted


---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Messages not delivered to SQS | SNS subscription not confirmed | Check SQS queue policy allows SNS |
| Lambda not triggering | Event source mapping disabled | Enable the Lambda trigger on the SQS queue |
| Messages stuck in DLQ | Lambda throwing exceptions | Check CloudWatch Logs for error details |
| Duplicate message processing | SQS standard queue at-least-once delivery | Use idempotent processing logic |
| SNS topic policy error | Missing `sns:Publish` permission | Update IAM role with correct SNS permissions |
| SQS queue empty | Lambda processed too fast | Increase message visibility timeout |

```bash
# Debug SNS/SQS issues
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All
aws sqs receive-message --queue-url <dlq-url>
aws logs filter-log-events --log-group-name /aws/lambda/<function-name> --filter-pattern "ERROR"
```
