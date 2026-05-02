# Lab 06 — CloudWatch: Metrics, Alarms, Dashboards & Logs Insights

## Objective
Set up comprehensive monitoring for a Lambda function and API Gateway: custom metrics, alarms, dashboards, and Logs Insights queries.

## Prerequisites
- AWS CLI configured
- Estimated time: 45 minutes
- Estimated cost: ~$0.00 (basic monitoring is free)

---

## Step 1: Create Lambda Function to Monitor

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_NAME="lab06-monitored-function"

# Create Lambda execution role
aws iam create-role \
  --role-name lab06-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'

aws iam attach-role-policy \
  --role-name lab06-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

sleep 10

# Create Lambda function with structured logging
cat > /tmp/lambda_lab06.py << 'EOF'
import json
import time
import random
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

def handler(event, context):
    start = time.time()
    request_id = context.aws_request_id

    # Simulate processing
    processing_time = random.uniform(50, 500)
    time.sleep(processing_time / 1000)

    # Simulate occasional errors (10% chance)
    if random.random() < 0.1:
        logger.error(json.dumps({
            "level": "ERROR",
            "requestId": request_id,
            "message": "Simulated processing error",
            "errorType": "ProcessingError"
        }))
        raise Exception("Simulated error for monitoring lab")

    duration = (time.time() - start) * 1000

    # Emit custom metric
    cloudwatch.put_metric_data(
        Namespace='Lab06/Application',
        MetricData=[
            {
                'MetricName': 'ProcessingTime',
                'Value': duration,
                'Unit': 'Milliseconds',
                'Dimensions': [{'Name': 'FunctionName', 'Value': context.function_name}]
            },
            {
                'MetricName': 'OrdersProcessed',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Environment', 'Value': 'lab'}]
            }
        ]
    )

    logger.info(json.dumps({
        "level": "INFO",
        "requestId": request_id,
        "message": "Request processed successfully",
        "duration": round(duration, 2),
        "orderId": event.get("orderId", "unknown")
    }))

    return {"statusCode": 200, "body": json.dumps({"processed": True, "duration": duration})}
EOF

zip /tmp/lambda_lab06.zip /tmp/lambda_lab06.py

ROLE_ARN=$(aws iam get-role --role-name lab06-lambda-role --query 'Role.Arn' --output tsv)

aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler lambda_lab06.handler \
  --zip-file fileb:///tmp/lambda_lab06.zip \
  --timeout 30 \
  --memory-size 256 \
  --region $REGION

aws lambda wait function-active --function-name $FUNCTION_NAME --region $REGION
echo "Lambda function created: $FUNCTION_NAME"
```

---

## Step 2: Create SNS Topic for Alerts

```bash
TOPIC_ARN=$(aws sns create-topic \
  --name lab06-alerts \
  --region $REGION \
  --query 'TopicArn' --output tsv)

# Subscribe your email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint "your-email@example.com" \
  --region $REGION

echo "SNS Topic: $TOPIC_ARN"
echo "Check your email to confirm subscription"
```

---

## Step 3: Create CloudWatch Alarms

```bash
FUNCTION_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"

# Alarm 1: Lambda errors > 2 in 5 minutes
aws cloudwatch put-metric-alarm \
  --alarm-name "lab06-lambda-errors" \
  --alarm-description "Lambda function errors exceeded threshold" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 2 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions $TOPIC_ARN \
  --ok-actions $TOPIC_ARN \
  --region $REGION

# Alarm 2: Lambda duration P99 > 3 seconds
aws cloudwatch put-metric-alarm \
  --alarm-name "lab06-lambda-duration" \
  --alarm-description "Lambda P99 duration above 3 seconds" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --extended-statistic p99 \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 3000 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions $TOPIC_ARN \
  --region $REGION

# Alarm 3: Lambda throttles > 0
aws cloudwatch put-metric-alarm \
  --alarm-name "lab06-lambda-throttles" \
  --alarm-description "Lambda function is being throttled" \
  --metric-name Throttles \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions $TOPIC_ARN \
  --region $REGION

# Alarm 4: Custom metric — processing time anomaly
aws cloudwatch put-metric-alarm \
  --alarm-name "lab06-processing-time" \
  --alarm-description "Processing time above 400ms" \
  --metric-name ProcessingTime \
  --namespace Lab06/Application \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --extended-statistic p95 \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 400 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions $TOPIC_ARN \
  --region $REGION

echo "Alarms created"
```

---

## Step 4: Generate Traffic and Trigger Alarms

```bash
# Generate 50 invocations
echo "Generating Lambda invocations..."
for i in $(seq 1 50); do
  aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload "{\"orderId\": \"order-$i\"}" \
    --cli-binary-format raw-in-base64-out \
    /tmp/response.json \
    --region $REGION > /dev/null 2>&1 &
done
wait

echo "50 invocations complete. Check CloudWatch in 5 minutes for alarms."

# View recent logs
aws logs tail /aws/lambda/$FUNCTION_NAME \
  --since 5m \
  --region $REGION
```

---

## Step 5: CloudWatch Logs Insights Queries

```bash
# Get Log Group ARN
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Start a query
QUERY_ID=$(aws logs start-query \
  --log-group-name $LOG_GROUP \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /INFO/
    | parse @message "\"duration\": *," as duration
    | stats
        count() as invocations,
        avg(duration) as avgMs,
        pct(duration, 95) as p95Ms,
        pct(duration, 99) as p99Ms
    | limit 1
  ' \
  --region $REGION \
  --query 'queryId' --output tsv)

echo "Query ID: $QUERY_ID"
sleep 5

# Get results
aws logs get-query-results \
  --query-id $QUERY_ID \
  --region $REGION \
  --query 'results'

# Error analysis query
aws logs start-query \
  --log-group-name $LOG_GROUP \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count() as errorCount by bin(5m)
    | sort @timestamp asc
  ' \
  --region $REGION
```

---

## Step 6: Create Dashboard

```bash
aws cloudwatch put-dashboard \
  --dashboard-name "lab06-monitoring" \
  --dashboard-body "{
    \"widgets\": [
      {
        \"type\": \"metric\",
        \"x\": 0, \"y\": 0, \"width\": 12, \"height\": 6,
        \"properties\": {
          \"title\": \"Lambda Invocations & Errors\",
          \"metrics\": [
            [\"AWS/Lambda\", \"Invocations\", \"FunctionName\", \"$FUNCTION_NAME\", {\"stat\": \"Sum\", \"period\": 300}],
            [\"AWS/Lambda\", \"Errors\", \"FunctionName\", \"$FUNCTION_NAME\", {\"stat\": \"Sum\", \"period\": 300, \"color\": \"#d62728\"}]
          ],
          \"view\": \"timeSeries\"
        }
      },
      {
        \"type\": \"metric\",
        \"x\": 12, \"y\": 0, \"width\": 12, \"height\": 6,
        \"properties\": {
          \"title\": \"Lambda Duration (P50/P95/P99)\",
          \"metrics\": [
            [\"AWS/Lambda\", \"Duration\", \"FunctionName\", \"$FUNCTION_NAME\", {\"stat\": \"p50\", \"period\": 300, \"label\": \"P50\"}],
            [\"...\", {\"stat\": \"p95\", \"period\": 300, \"label\": \"P95\", \"color\": \"#ff7f0e\"}],
            [\"...\", {\"stat\": \"p99\", \"period\": 300, \"label\": \"P99\", \"color\": \"#d62728\"}]
          ]
        }
      },
      {
        \"type\": \"metric\",
        \"x\": 0, \"y\": 6, \"width\": 12, \"height\": 6,
        \"properties\": {
          \"title\": \"Custom: Processing Time\",
          \"metrics\": [
            [\"Lab06/Application\", \"ProcessingTime\", \"FunctionName\", \"$FUNCTION_NAME\", {\"stat\": \"p95\", \"period\": 300}]
          ]
        }
      },
      {
        \"type\": \"alarm\",
        \"x\": 12, \"y\": 6, \"width\": 12, \"height\": 6,
        \"properties\": {
          \"title\": \"Active Alarms\",
          \"alarms\": [
            \"arn:aws:cloudwatch:$REGION:$ACCOUNT_ID:alarm:lab06-lambda-errors\",
            \"arn:aws:cloudwatch:$REGION:$ACCOUNT_ID:alarm:lab06-lambda-duration\",
            \"arn:aws:cloudwatch:$REGION:$ACCOUNT_ID:alarm:lab06-lambda-throttles\"
          ]
        }
      }
    ]
  }" \
  --region $REGION

echo "Dashboard created: lab06-monitoring"
echo "View at: https://console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=lab06-monitoring"
```

---

## Step 7: Cleanup

```bash
# Delete alarms
for ALARM in lab06-lambda-errors lab06-lambda-duration lab06-lambda-throttles lab06-processing-time; do
  aws cloudwatch delete-alarms --alarm-names $ALARM --region $REGION
done

# Delete dashboard
aws cloudwatch delete-dashboards --dashboard-names lab06-monitoring --region $REGION

# Delete Lambda
aws lambda delete-function --function-name $FUNCTION_NAME --region $REGION

# Delete SNS topic
aws sns delete-topic --topic-arn $TOPIC_ARN --region $REGION

# Delete IAM role
aws iam detach-role-policy \
  --role-name lab06-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lab06-lambda-role

# Clean up temp files
rm -f /tmp/lambda_lab06.py /tmp/lambda_lab06.zip /tmp/response.json

echo "Cleanup complete"
```

---

## What You Learned

✅ Create Lambda function with structured JSON logging
✅ Emit custom CloudWatch metrics from Lambda code
✅ Create metric alarms with SNS notifications
✅ Use extended statistics (P95, P99) in alarms
✅ Query logs with CloudWatch Logs Insights
✅ Build a CloudWatch dashboard with multiple widgets
✅ Use alarm widgets to show alarm status
