# Cost Estimate — Project 4.5: SNS + SQS Microservices Fan-Out

## Architecture Summary
SNS topic receives messages → fans out to 3 SQS queues (orders-queue, notifications-queue, analytics-queue) → dedicated Lambda consumer per queue → DLQ captures failed messages after 3 retries.

---

## Free Tier Coverage

| Service | Free Tier Allowance | Type | Notes |
|---|---|---|---|
| Amazon SNS | 1,000,000 publishes/month | Always free (perpetual) | Never expires |
| Amazon SNS | 1,000,000 HTTP/S deliveries | Always free (perpetual) | SQS deliveries count here |
| Amazon SNS | 100,000 email deliveries | Always free (perpetual) | If email endpoint added |
| Amazon SQS | 1,000,000 requests/month | Always free (perpetual) | SendMessage + ReceiveMessage + DeleteMessage |
| Amazon SQS (DLQ) | Included in 1M free requests | Always free (perpetual) | DLQ is just another SQS queue |
| AWS Lambda | 1,000,000 requests/month | Always free (perpetual) | Per function — 3 consumers + 3 DLQ handlers |
| AWS Lambda | 400,000 GB-seconds compute/month | Always free (perpetual) | Shared across all functions |
| CloudWatch Logs | 5 GB ingestion/month | First 12 months | All Lambda function logs |
| CloudWatch Metrics | 10 custom metrics | Always free | Queue depth, consumer lag |

---

## Estimated Monthly Cost for This Lab

| Component | Usage (Lab Scale) | Cost |
|---|---|---|
| SNS Topic | < 1M publishes | **$0.00** (Free Tier) |
| SQS Queue — orders-queue | < 1M requests total | **$0.00** (Free Tier) |
| SQS Queue — notifications-queue | < 1M requests total | **$0.00** (Free Tier) |
| SQS Queue — analytics-queue | < 1M requests total | **$0.00** (Free Tier) |
| SQS DLQ × 3 (one per queue) | Minimal failed messages | **$0.00** (Free Tier) |
| Lambda — orders-consumer | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — notifications-consumer | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — analytics-consumer | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| CloudWatch Logs | Minimal | **$0.00** (Free Tier) |
| **Total** | | **$0.00** |

> ✅ **This lab runs entirely within AWS Free Tier — $0 cost for typical hands-on usage.**

---

## SQS Request Count Calculation

Each message processed by Lambda consumes multiple SQS API calls:
```
1 message lifecycle = SendMessage (1) + ReceiveMessage (1) + DeleteMessage (1) = 3 requests
Fan-out × 3 queues = 9 SQS requests per SNS publish

1M SNS publishes × 3 queues × 3 requests = 9M SQS requests
9M requests = 9 × free tier → costs $0.40 per million above 1M = ~$3.20 if heavily used
```
For lab testing (< 10,000 messages), all within free tier.

---

## DLQ Configuration Note

| Parameter | Recommended Value |
|---|---|
| Max Receive Count | 3 (retry 3× before DLQ) |
| Visibility Timeout (main queue) | 6× Lambda timeout (e.g., 180s if Lambda = 30s) |
| Message Retention (DLQ) | 14 days (investigate failed messages) |

---

## Cost Beyond Free Tier

| Service | Pricing |
|---|---|
| SNS publishes (beyond 1M) | $0.50 per million (HTTP/S endpoints) |
| SNS data transfer | $0.09 per GB |
| SQS Standard (beyond 1M) | $0.40 per million requests |
| SQS FIFO (if needed) | $0.50 per million requests |
| Lambda requests (beyond 1M) | $0.20 per million |
| Lambda compute (beyond free) | $0.0000166667 per GB-second |

---

## Cleanup Commands

### Delete Lambda Consumer Functions
```bash
# Delete all 3 consumer Lambdas
for FUNCTION in orders-consumer notifications-consumer analytics-consumer; do
  echo "Deleting Lambda: ${FUNCTION}"
  aws lambda delete-function --function-name ${FUNCTION}
done

# Delete DLQ handler Lambdas (if created)
for FUNCTION in orders-dlq-handler notifications-dlq-handler analytics-dlq-handler; do
  aws lambda delete-function --function-name ${FUNCTION} 2>/dev/null || echo "${FUNCTION} not found, skipping"
done
```

### Delete SQS Queues (main + DLQs)
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

# Delete main queues
for QUEUE in orders-queue notifications-queue analytics-queue; do
  QUEUE_URL="https://sqs.${REGION}.amazonaws.com/${ACCOUNT_ID}/${QUEUE}"
  echo "Deleting SQS queue: ${QUEUE}"
  aws sqs delete-queue --queue-url ${QUEUE_URL}
done

# Delete DLQs
for QUEUE in orders-dlq notifications-dlq analytics-dlq; do
  QUEUE_URL="https://sqs.${REGION}.amazonaws.com/${ACCOUNT_ID}/${QUEUE}"
  echo "Deleting DLQ: ${QUEUE}"
  aws sqs delete-queue --queue-url ${QUEUE_URL}
done

# Note: SQS queues take up to 60 seconds to fully delete
echo "Waiting 60 seconds for SQS deletion to propagate..."
sleep 60
```

### Delete SNS Topic
```bash
# List SNS topics to find ARN
aws sns list-topics --query "Topics[].TopicArn" --output text | tr '\t' '\n' | grep microservices

# Delete the SNS topic (replace with actual ARN)
SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?ends_with(TopicArn, 'microservices-events')].TopicArn" --output text)
aws sns delete-topic --topic-arn ${SNS_TOPIC_ARN}
echo "SNS topic deleted"
```

### Delete IAM Roles
```bash
for ROLE in orders-consumer-role notifications-consumer-role analytics-consumer-role; do
  # Detach policies
  aws iam detach-role-policy \
    --role-name ${ROLE} \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null
  
  aws iam detach-role-policy \
    --role-name ${ROLE} \
    --policy-arn arn:aws:iam::aws:policy/AmazonSQSFullAccess 2>/dev/null

  # Delete role
  aws iam delete-role --role-name ${ROLE} 2>/dev/null
  echo "Deleted role: ${ROLE}"
done
```

### Delete CloudWatch Log Groups
```bash
for FUNCTION in orders-consumer notifications-consumer analytics-consumer; do
  aws logs delete-log-group --log-group-name /aws/lambda/${FUNCTION}
done
echo "Log groups deleted"
```

---

## Cleanup Verification
```bash
echo "=== SNS Topics ==="
aws sns list-topics --query "Topics[?contains(TopicArn, 'microservices')]" --output text

echo "=== SQS Queues ==="
aws sqs list-queues --query "QueueUrls[?contains(@, 'queue') || contains(@, 'dlq')]" --output text

echo "=== Lambda Functions ==="
aws lambda list-functions \
  --query "Functions[?contains(FunctionName, 'consumer') || contains(FunctionName, 'handler')].FunctionName" \
  --output text

echo "All clear if outputs are empty."
```

---

*Region: us-east-1 | Prices as of 2024 — verify at https://aws.amazon.com/pricing/*
