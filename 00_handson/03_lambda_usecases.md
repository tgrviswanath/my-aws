# Lambda — Real-World Use Cases

## Use Case 1: Image Thumbnail Generator

**Business Problem**: When users upload photos, automatically create 3 thumbnail sizes (small/medium/large) without running a server 24/7.

```python
# handler.py
import boto3
import io
import os
from PIL import Image

s3 = boto3.client('s3')
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']

SIZES = {
    'small':  (150, 150),
    'medium': (400, 400),
    'large':  (800, 800),
}

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key    = record['s3']['object']['key']

        # Download original
        response = s3.get_object(Bucket=bucket, Key=key)
        image    = Image.open(io.BytesIO(response['Body'].read()))
        fmt      = image.format or 'JPEG'

        for size_name, dimensions in SIZES.items():
            # Create thumbnail (preserves aspect ratio)
            thumb = image.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)

            # Upload to output bucket
            buffer = io.BytesIO()
            thumb.save(buffer, format=fmt, optimize=True, quality=85)
            buffer.seek(0)

            output_key = f"thumbnails/{size_name}/{key.split('/')[-1]}"
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=buffer.getvalue(),
                ContentType=response['ContentType'],
            )
            print(f"Created {size_name} thumbnail: {output_key}")

    return {'statusCode': 200}
```

```bash
# Deploy
pip install Pillow -t package/
cp handler.py package/
cd package && zip -r ../function.zip . && cd ..

aws lambda create-function \
  --function-name "image-thumbnail-generator" \
  --runtime python3.12 \
  --role arn:aws:iam::123456789:role/lambda-s3-role \
  --handler handler.handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 1024 \
  --architectures arm64 \
  --environment Variables='{"OUTPUT_BUCKET":"thumbnails-bucket"}'

# Test with a real image
aws s3 cp photo.jpg s3://raw-uploads/photos/photo.jpg
aws logs tail /aws/lambda/image-thumbnail-generator --follow
```

**What you learn**: S3 trigger, PIL image processing, arm64 for cost savings, memory sizing for image workloads.

---

## Use Case 2: Scheduled Report Generator (Cron Job)

**Business Problem**: Every Monday at 8 AM, generate a weekly sales report from DynamoDB and email it to the team.

```python
# weekly_report.py
import boto3
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses      = boto3.client('ses')
table    = dynamodb.Table(os.environ['ORDERS_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def handler(event, context):
    # Calculate last week's date range
    today     = datetime.utcnow().date()
    week_ago  = today - timedelta(days=7)

    # Query DynamoDB for last week's orders
    response = table.scan(
        FilterExpression='#date BETWEEN :start AND :end AND #status = :status',
        ExpressionAttributeNames={'#date': 'date', '#status': 'status'},
        ExpressionAttributeValues={
            ':start': str(week_ago),
            ':end':   str(today),
            ':status': 'completed'
        }
    )
    orders = response['Items']

    # Calculate metrics
    total_revenue = sum(float(o['amount']) for o in orders)
    order_count   = len(orders)
    avg_order     = total_revenue / order_count if order_count else 0

    # Build HTML report
    html = f"""
    <h2>Weekly Sales Report — {week_ago} to {today}</h2>
    <table border="1">
      <tr><td><b>Total Orders</b></td><td>{order_count:,}</td></tr>
      <tr><td><b>Total Revenue</b></td><td>${total_revenue:,.2f}</td></tr>
      <tr><td><b>Avg Order Value</b></td><td>${avg_order:.2f}</td></tr>
    </table>
    """

    # Send via SES
    ses.send_email(
        Source='reports@mycompany.com',
        Destination={'ToAddresses': ['team@mycompany.com']},
        Message={
            'Subject': {'Data': f'Weekly Sales Report — {today}'},
            'Body': {'Html': {'Data': html}}
        }
    )
    print(f"Report sent: {order_count} orders, ${total_revenue:.2f} revenue")
    return {'orders': order_count, 'revenue': total_revenue}
```

```bash
# Create EventBridge rule (every Monday 8 AM UTC)
aws events put-rule \
  --name "weekly-sales-report" \
  --schedule-expression "cron(0 8 ? * MON *)" \
  --state ENABLED \
  --description "Trigger weekly sales report every Monday 8 AM"

# Add Lambda as target
aws events put-targets \
  --rule "weekly-sales-report" \
  --targets '[{
    "Id": "WeeklyReportLambda",
    "Arn": "arn:aws:lambda:us-east-1:123456789:function:weekly-report"
  }]'

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name "weekly-report" \
  --statement-id "eventbridge-trigger" \
  --action "lambda:InvokeFunction" \
  --principal "events.amazonaws.com" \
  --source-arn "arn:aws:events:us-east-1:123456789:rule/weekly-sales-report"

# Test immediately
aws lambda invoke \
  --function-name "weekly-report" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json
```

**What you learn**: EventBridge cron expressions, SES email, DynamoDB scan with filters, scheduled serverless jobs.

---

## Use Case 3: API Backend with DynamoDB

**Business Problem**: Build a serverless REST API for a todo app — no servers to manage, scales to zero when unused.

```python
# api_handler.py
import boto3
import json
import uuid
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    method = event['httpMethod']
    path   = event['path']
    body   = json.loads(event.get('body') or '{}')
    params = event.get('pathParameters') or {}

    try:
        if method == 'GET' and path == '/todos':
            return list_todos(event)
        elif method == 'POST' and path == '/todos':
            return create_todo(body)
        elif method == 'GET' and '/todos/' in path:
            return get_todo(params['id'])
        elif method == 'PUT' and '/todos/' in path:
            return update_todo(params['id'], body)
        elif method == 'DELETE' and '/todos/' in path:
            return delete_todo(params['id'])
        else:
            return response(404, {'error': 'Not found'})
    except Exception as e:
        print(f"Error: {e}")
        return response(500, {'error': 'Internal server error'})

def list_todos(event):
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'anonymous')
    result  = table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    return response(200, {'todos': result['Items']})

def create_todo(body):
    todo = {
        'id':        str(uuid.uuid4()),
        'userId':    body.get('userId', 'anonymous'),
        'title':     body['title'],
        'completed': False,
        'createdAt': datetime.utcnow().isoformat()
    }
    table.put_item(Item=todo)
    return response(201, todo)

def get_todo(todo_id):
    result = table.get_item(Key={'id': todo_id})
    item   = result.get('Item')
    return response(200, item) if item else response(404, {'error': 'Not found'})

def update_todo(todo_id, body):
    result = table.update_item(
        Key={'id': todo_id},
        UpdateExpression='SET completed = :c, updatedAt = :u',
        ExpressionAttributeValues={
            ':c': body.get('completed', False),
            ':u': datetime.utcnow().isoformat()
        },
        ReturnValues='ALL_NEW'
    )
    return response(200, result['Attributes'])

def delete_todo(todo_id):
    table.delete_item(Key={'id': todo_id})
    return response(204, {})

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, default=str)
    }
```

```bash
# Deploy with SAM
cat > template.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  TodoApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowOrigin: "'*'"
        AllowHeaders: "'Content-Type,Authorization'"

  TodoFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: api_handler.handler
      Runtime: python3.12
      Architectures: [arm64]
      Environment:
        Variables:
          TABLE_NAME: !Ref TodoTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref TodoTable
      Events:
        Api:
          Type: Api
          Properties:
            RestApiId: !Ref TodoApi
            Path: /todos/{proxy+}
            Method: ANY

  TodoTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH
EOF

sam build && sam deploy --guided
```

**What you learn**: Lambda proxy integration, SAM templates, DynamoDB CRUD, CORS headers.

---

## Use Case 4: SQS Consumer (Async Order Processing)

**Business Problem**: Process orders asynchronously. If processing fails, retry 3 times then send to dead letter queue for investigation.

```python
# order_processor.py
import boto3
import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
ses      = boto3.client('ses')
table    = dynamodb.Table(os.environ['ORDERS_TABLE'])

def handler(event, context):
    failed_items = []

    for record in event['Records']:
        message_id = record['messageId']
        body       = json.loads(record['body'])
        order_id   = body['orderId']

        try:
            logger.info(f"Processing order: {order_id}")

            # 1. Validate order exists
            order = table.get_item(Key={'orderId': order_id}).get('Item')
            if not order:
                raise ValueError(f"Order {order_id} not found")

            # 2. Process payment (simulated)
            process_payment(order)

            # 3. Update order status
            table.update_item(
                Key={'orderId': order_id},
                UpdateExpression='SET #s = :status',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': 'CONFIRMED'}
            )

            # 4. Send confirmation email
            ses.send_email(
                Source='orders@mycompany.com',
                Destination={'ToAddresses': [order['email']]},
                Message={
                    'Subject': {'Data': f'Order {order_id} Confirmed!'},
                    'Body': {'Text': {'Data': f'Your order {order_id} has been confirmed.'}}
                }
            )
            logger.info(f"Order {order_id} processed successfully")

        except Exception as e:
            logger.error(f"Failed to process {order_id}: {e}")
            # Report partial batch failure — only this message retries
            failed_items.append({'itemIdentifier': message_id})

    # Return failed items — they go back to queue for retry
    return {'batchItemFailures': failed_items}

def process_payment(order):
    # Simulate payment processing
    if float(order.get('amount', 0)) <= 0:
        raise ValueError("Invalid amount")
    # In real code: call Stripe/PayPal API
```

```bash
# Create DLQ first
DLQ_ARN=$(aws sqs create-queue \
  --queue-name "orders-dlq" \
  --attributes MessageRetentionPeriod=1209600 \
  --query 'QueueUrl' --output text | \
  xargs -I{} aws sqs get-queue-attributes \
    --queue-url {} \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

# Create main queue with DLQ
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "orders-queue" \
  --attributes '{
    "VisibilityTimeout": "360",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":\"3\"}"
  }' \
  --query 'QueueUrl' --output text)

# Connect Lambda to SQS
aws lambda create-event-source-mapping \
  --function-name "order-processor" \
  --event-source-arn $(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text) \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --function-response-types ReportBatchItemFailures

# Monitor DLQ for failed orders
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name orders-dlq --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages
```

**What you learn**: SQS batch processing, partial batch failures, DLQ pattern, retry logic.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Initializing SDK clients inside handler | Cold start penalty on every call | Move to module level (outside handler) |
| Not setting timeout | Lambda runs until 15 min max, costs money | Set timeout = 3× expected duration |
| Ignoring cold starts for latency-sensitive APIs | Slow first response | Use Provisioned Concurrency |
| Using Python UDFs instead of built-ins | 10–100× slower | Use boto3 native operations |
| Not using arm64 | 20% higher cost | Switch to `--architectures arm64` |
| Storing state in `/tmp` across invocations | Unreliable (container may be recycled) | Use DynamoDB/S3/ElastiCache for state |
