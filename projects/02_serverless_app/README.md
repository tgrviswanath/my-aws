# Project 02: Serverless Application (Lambda + API Gateway + DynamoDB)

## Architecture

```
Client
  ↓
CloudFront (CDN)
  ↓
API Gateway (HTTP API)
  ↓
Lambda Functions
  ↓
DynamoDB (data store)
  ↓
SQS (async processing)
  ↓
Lambda (background workers)
  ↓
SNS (notifications)
```

## Use Case: Order Management API

A fully serverless REST API for managing orders with async processing.

## API Endpoints

| Method | Path | Lambda | Description |
|--------|------|--------|-------------|
| POST | /orders | create-order | Create new order |
| GET | /orders/{id} | get-order | Get order by ID |
| GET | /orders | list-orders | List user's orders |
| PUT | /orders/{id}/status | update-status | Update order status |
| DELETE | /orders/{id} | cancel-order | Cancel order |

## Project Structure

```
02_serverless_app/
├── functions/
│   ├── create_order/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── get_order/
│   │   └── handler.py
│   ├── list_orders/
│   │   └── handler.py
│   └── process_order/
│       └── handler.py
└── infrastructure/
    ├── template.yaml (SAM)
    └── samconfig.toml
```

## SAM Template

```yaml
# infrastructure/template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Serverless Order Management API

Globals:
  Function:
    Runtime: python3.12
    Timeout: 30
    MemorySize: 512
    Architectures: [arm64]
    Tracing: Active
    Environment:
      Variables:
        ORDERS_TABLE: !Ref OrdersTable
        ORDER_QUEUE_URL: !Ref OrderQueue
        POWERTOOLS_SERVICE_NAME: order-api
        LOG_LEVEL: INFO
    Layers:
      - !Ref CommonLayer

Parameters:
  Environment:
    Type: String
    Default: production

Resources:
  # ── Lambda Functions ────────────────────────────────────────────────────────
  CreateOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "${Environment}-create-order"
      Handler: handler.handler
      CodeUri: ../functions/create_order/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
        - SQSSendMessagePolicy:
            QueueName: !GetAtt OrderQueue.QueueName
      Events:
        CreateOrder:
          Type: HttpApi
          Properties:
            ApiId: !Ref OrderApi
            Path: /orders
            Method: POST
            Auth:
              Authorizer: CognitoAuthorizer

  GetOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "${Environment}-get-order"
      Handler: handler.handler
      CodeUri: ../functions/get_order/
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref OrdersTable
      Events:
        GetOrder:
          Type: HttpApi
          Properties:
            ApiId: !Ref OrderApi
            Path: /orders/{orderId}
            Method: GET

  ProcessOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "${Environment}-process-order"
      Handler: handler.handler
      CodeUri: ../functions/process_order/
      Timeout: 300
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
        - SNSPublishMessagePolicy:
            TopicName: !GetAtt NotificationTopic.TopicName
      Events:
        OrderQueue:
          Type: SQS
          Properties:
            Queue: !GetAtt OrderQueue.Arn
            BatchSize: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures

  # ── API Gateway ─────────────────────────────────────────────────────────────
  OrderApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      CorsConfiguration:
        AllowOrigins:
          - "https://myapp.com"
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
        AllowHeaders:
          - Content-Type
          - Authorization
      Auth:
        Authorizers:
          CognitoAuthorizer:
            IdentitySource: $request.header.Authorization
            JwtConfiguration:
              issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}"
              audience:
                - !Ref UserPoolClient
        DefaultAuthorizer: CognitoAuthorizer

  # ── DynamoDB ─────────────────────────────────────────────────────────────────
  OrdersTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Retain
    Properties:
      TableName: !Sub "${Environment}-orders"
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: customerId
          AttributeType: S
        - AttributeName: orderId
          AttributeType: S
        - AttributeName: status
          AttributeType: S
        - AttributeName: createdAt
          AttributeType: S
      KeySchema:
        - AttributeName: customerId
          KeyType: HASH
        - AttributeName: orderId
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: status-createdAt-index
          KeySchema:
            - AttributeName: status
              KeyType: HASH
            - AttributeName: createdAt
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
        SSEType: KMS

  # ── SQS ──────────────────────────────────────────────────────────────────────
  OrderQueueDLQ:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub "${Environment}-order-processing-dlq"
      MessageRetentionPeriod: 1209600  # 14 days

  OrderQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub "${Environment}-order-processing"
      VisibilityTimeout: 360  # 6x Lambda timeout
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt OrderQueueDLQ.Arn
        maxReceiveCount: 3

  # ── SNS ──────────────────────────────────────────────────────────────────────
  NotificationTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub "${Environment}-order-notifications"

  # ── Cognito ──────────────────────────────────────────────────────────────────
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: !Sub "${Environment}-users"
      AutoVerifiedAttributes: [email]
      PasswordPolicy:
        MinimumLength: 12
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: true

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      UserPoolId: !Ref UserPool
      GenerateSecret: false
      ExplicitAuthFlows:
        - ALLOW_USER_SRP_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH

  # ── Lambda Layer ─────────────────────────────────────────────────────────────
  CommonLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: !Sub "${Environment}-common"
      ContentUri: ../layers/common/
      CompatibleRuntimes: [python3.12]
      CompatibleArchitectures: [arm64]
    Metadata:
      BuildMethod: python3.12

Outputs:
  ApiUrl:
    Value: !Sub "https://${OrderApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
  OrdersTableName:
    Value: !Ref OrdersTable
  UserPoolId:
    Value: !Ref UserPool
```

## Lambda Handler Example

```python
# functions/create_order/handler.py
import json
import uuid
import time
import boto3
import os
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

table = dynamodb.Table(os.environ['ORDERS_TABLE'])
queue_url = os.environ['ORDER_QUEUE_URL']

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: dict, context: LambdaContext) -> dict:
    try:
        # Extract user from JWT claims
        claims = event['requestContext']['authorizer']['jwt']['claims']
        customer_id = claims['sub']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        if not body.get('items'):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'items is required'})
            }
        
        # Create order
        order_id = str(uuid.uuid4())
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        order = {
            'customerId': customer_id,
            'orderId': order_id,
            'status': 'PENDING',
            'items': body['items'],
            'total': sum(item['price'] * item['quantity'] for item in body['items']),
            'createdAt': timestamp,
            'updatedAt': timestamp,
            'version': 1
        }
        
        # Save to DynamoDB
        table.put_item(
            Item=order,
            ConditionExpression='attribute_not_exists(orderId)'
        )
        
        # Queue for async processing
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({'orderId': order_id, 'customerId': customer_id}),
            MessageGroupId=customer_id  # FIFO: group by customer
        )
        
        # Record metric
        metrics.add_metric(name='OrdersCreated', unit=MetricUnit.Count, value=1)
        
        logger.info('Order created', extra={'orderId': order_id})
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'orderId': order_id, 'status': 'PENDING'})
        }
        
    except Exception as e:
        logger.exception('Failed to create order')
        metrics.add_metric(name='OrderCreationErrors', unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

## Deployment

```bash
# Install SAM CLI
pip install aws-sam-cli

# Build
sam build --use-container

# Deploy (first time)
sam deploy --guided

# Deploy (subsequent)
sam deploy

# Test locally
sam local start-api
curl -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"items": [{"productId": "prod-1", "quantity": 2, "price": 29.99}]}'

# View logs
sam logs -n CreateOrderFunction --tail
```

## Cost Estimate (1M requests/month)

| Service | Cost |
|---------|------|
| Lambda (1M req, 512MB, 100ms avg) | ~$2 |
| API Gateway HTTP API | ~$1 |
| DynamoDB On-Demand | ~$5 |
| SQS | ~$0.40 |
| CloudWatch Logs | ~$2 |
| **Total** | **~$10/month** |
