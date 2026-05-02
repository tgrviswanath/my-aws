# AWS Lambda — Serverless Deep Dive

## What is Lambda?
Lambda runs code without provisioning or managing servers. You pay only for compute time consumed — no charge when code is not running.

```
Event Source → Lambda Function → Output/Side Effects
(S3, API GW,    (your code,       (DynamoDB write,
 SQS, SNS...)    max 15 min)       SNS publish...)
```

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| Function | Your code + configuration |
| Runtime | Language environment (Python 3.12, Node.js 20, Java 21...) |
| Handler | Entry point function |
| Event | JSON input triggering the function |
| Context | Runtime info (request ID, remaining time, memory) |
| Execution environment | Isolated container running your function |
| Cold start | First invocation — container initialization |
| Warm start | Reuse of existing container |

---

## Invocation Models

### 1. Synchronous (Request/Response)
Caller waits for response. Errors returned to caller.
- API Gateway, ALB, Lambda Function URLs, SDK direct invoke

### 2. Asynchronous (Event)
Lambda queues the event, returns 202 immediately. Retries on failure (2 times).
- S3 events, SNS, EventBridge, CloudWatch Events

### 3. Stream/Poll-based
Lambda polls the source and processes batches.
- SQS, Kinesis, DynamoDB Streams, Kafka

---

## Function Configuration

```bash
# Create function
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --role arn:aws:iam::123456789:role/lambda-role \
  --handler app.handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables='{DB_HOST=mydb.cluster.amazonaws.com,ENV=prod}' \
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-12345678

# Update function code
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip

# Invoke function
aws lambda invoke \
  --function-name my-function \
  --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# View logs
aws logs tail /aws/lambda/my-function --follow
```

---

## Python Handler Example

```python
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: dict - trigger event data
        context: LambdaContext - runtime information
    """
    logger.info(f"Event: {json.dumps(event)}")
    logger.info(f"Remaining time: {context.get_remaining_time_in_millis()}ms")
    
    try:
        # Process event
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')
        
        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'userId is required'})
            }
        
        # DynamoDB operation
        response = table.get_item(Key={'userId': user_id})
        item = response.get('Item')
        
        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'User not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(item)
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

---

## Memory & Performance

- Memory: 128MB to 10,240MB (10GB)
- **CPU scales proportionally with memory** — 1,769MB = 1 vCPU
- Timeout: 1 second to 15 minutes
- Ephemeral storage (/tmp): 512MB to 10GB

```
Memory  | vCPU  | Use case
128MB   | 0.07  | Simple transforms, lightweight tasks
512MB   | 0.28  | API handlers, moderate processing
1769MB  | 1.0   | CPU-intensive tasks
3538MB  | 2.0   | Parallel processing
10240MB | 6.0   | ML inference, large data processing
```

**Tip**: For CPU-bound tasks, increase memory even if you don't need RAM — you get more CPU.

---

## Cold Starts

Cold start = time to initialize execution environment + download code + run init code.

```
Cold start breakdown:
├── Container init:     ~100-500ms (AWS managed)
├── Runtime init:       ~100-500ms (language startup)
├── Code init:          your init code outside handler
└── Handler execution:  your actual code
```

### Reducing Cold Starts

```python
# BAD: Initialize inside handler (runs every invocation)
def handler(event, context):
    db = boto3.resource('dynamodb')  # reconnects every time
    ...

# GOOD: Initialize outside handler (runs once per container)
import boto3
db = boto3.resource('dynamodb')      # reused across invocations
table = db.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    ...
```

### Provisioned Concurrency
Pre-warms execution environments — eliminates cold starts.

```bash
# Create alias
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version 5

# Set provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

**Cost**: ~3x more expensive than on-demand. Use for latency-sensitive APIs.

---

## Concurrency

```
Reserved Concurrency:   Guarantees capacity, limits max concurrency
Provisioned Concurrency: Pre-warmed, eliminates cold starts
Account limit:          1000 concurrent executions (default, can increase)
```

```bash
# Set reserved concurrency (also acts as throttle limit)
aws lambda put-function-concurrency \
  --function-name my-function \
  --reserved-concurrent-executions 100

# Remove reserved concurrency (uses account pool)
aws lambda delete-function-concurrency \
  --function-name my-function
```

---

## Lambda Layers

Share code/libraries across functions without bundling them.

```bash
# Create layer
zip -r layer.zip python/
aws lambda publish-layer-version \
  --layer-name my-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12

# Attach layer to function
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789:layer:my-dependencies:1
```

---

## Event Source Mappings (SQS, Kinesis, DynamoDB Streams)

```bash
# SQS trigger
aws lambda create-event-source-mapping \
  --function-name my-function \
  --event-source-arn arn:aws:sqs:us-east-1:123456789:my-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --function-response-types ReportBatchItemFailures

# Kinesis trigger
aws lambda create-event-source-mapping \
  --function-name my-function \
  --event-source-arn arn:aws:kinesis:us-east-1:123456789:stream/my-stream \
  --starting-position LATEST \
  --batch-size 100 \
  --bisect-batch-on-function-error true
```

---

## Lambda with API Gateway

```yaml
# SAM template
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Runtime: python3.12
    Timeout: 30
    MemorySize: 512
    Environment:
      Variables:
        TABLE_NAME: !Ref UsersTable

Resources:
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      CodeUri: src/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable
      Events:
        GetUser:
          Type: Api
          Properties:
            Path: /users/{userId}
            Method: GET
        CreateUser:
          Type: Api
          Properties:
            Path: /users
            Method: POST

  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: users
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: userId
          AttributeType: S
      KeySchema:
        - AttributeName: userId
          KeyType: HASH
```

---

## Security Best Practices

1. **Least privilege IAM role** — only permissions the function needs
2. **Environment variables** — use KMS encryption for secrets
3. **Secrets Manager** — for database passwords, API keys
4. **VPC** — for accessing private resources (RDS, ElastiCache)
5. **Resource-based policies** — control who can invoke the function
6. **Code signing** — verify function code integrity

```python
# Retrieve secret from Secrets Manager (cache it!)
import boto3
import json

secrets_client = boto3.client('secretsmanager')
_secret_cache = {}

def get_secret(secret_name):
    if secret_name not in _secret_cache:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        _secret_cache[secret_name] = json.loads(response['SecretString'])
    return _secret_cache[secret_name]
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|---------|
| Timeout on cold start | Increase timeout, use provisioned concurrency |
| DB connection exhaustion | Use RDS Proxy, connection pooling |
| Large deployment package | Use layers, Lambda container images |
| Storing state in /tmp across invocations | Don't rely on it — use S3/DynamoDB |
| Recursive invocation loop | Set reserved concurrency limit |
| Missing VPC internet access | Add NAT Gateway for outbound internet |

---

## Interview Q&A

### Q1: What is a Lambda cold start and how do you mitigate it?
Cold start = time to initialize a new execution environment (container + runtime + your init code). Mitigation: (1) Keep deployment package small, (2) Initialize SDK clients outside handler, (3) Use Provisioned Concurrency for latency-sensitive functions, (4) Choose faster runtimes (Python/Node.js vs Java), (5) Use Lambda SnapStart for Java.

### Q2: How does Lambda concurrency work?
Each concurrent invocation runs in its own execution environment. Account default limit is 1000 concurrent executions. Reserved concurrency guarantees capacity for a function and limits its max. Provisioned concurrency pre-warms environments. If concurrency limit is hit, Lambda throttles (returns 429).

### Q3: What is the difference between synchronous and asynchronous Lambda invocation?
**Synchronous**: Caller waits for response. Errors propagate to caller. Used by API Gateway, ALB. No automatic retry.
**Asynchronous**: Lambda queues event, returns 202 immediately. Retries twice on failure. Dead letter queue (DLQ) or Lambda destinations capture failures. Used by S3, SNS, EventBridge.

### Q4: How do you handle errors in Lambda?
1. Try/catch in code, return structured error responses
2. Dead Letter Queue (DLQ) for async invocations
3. Lambda Destinations — route success/failure to SQS/SNS/EventBridge/Lambda
4. For SQS: use `ReportBatchItemFailures` to partially succeed batches
5. For Kinesis: use `BisectBatchOnFunctionError` to isolate bad records
6. CloudWatch Alarms on `Errors` and `Throttles` metrics

### Q5: When would you NOT use Lambda?
- Long-running tasks > 15 minutes (use ECS Fargate or Step Functions)
- Workloads needing persistent connections (use EC2 or ECS)
- High-frequency, predictable load (EC2 Reserved may be cheaper)
- Large binary dependencies > 250MB unzipped (use container image Lambda)
- Workloads needing GPU (use EC2 GPU instances)
