# Level 3 — Advanced Hands-On Scenarios

> **Goal**: Think like a production engineer.  
> **Prerequisites**: Completed Levels 1 & 2.

---

## Scenario 13 — Auto Scaling Web Application

**Skills**: ALB, Auto Scaling, Launch Templates  
**Time**: 45 minutes

### Architecture
```
Internet → ALB (port 80/443)
              ↓
         Target Group
              ↓
    Auto Scaling Group (min=2, max=10)
    ├── EC2 in AZ-a
    ├── EC2 in AZ-b
    └── EC2 in AZ-c (scales out when CPU > 60%)
```

### Step-by-Step

```bash
REGION="us-east-1"
VPC_ID="vpc-xxxxxxxx"       # From Scenario 6
PUBLIC_SUBNET_A="subnet-aaa"
PUBLIC_SUBNET_B="subnet-bbb"
SG_WEB="sg-xxxxxxxx"

# Step 1: Create Launch Template
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name "webapp-lt" \
  --version-description "v1" \
  --launch-template-data "{
    \"ImageId\": \"$(aws ec2 describe-images \
      --owners amazon \
      --filters 'Name=name,Values=al2023-ami-*-x86_64' 'Name=state,Values=available' \
      --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text)\",
    \"InstanceType\": \"t3.micro\",
    \"SecurityGroupIds\": [\"${SG_WEB}\"],
    \"UserData\": \"$(base64 -w0 << 'SCRIPT'
#!/bin/bash
yum install -y nginx
systemctl start nginx
systemctl enable nginx
INSTANCE_ID=\$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=\$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
echo \"<h1>Hello from \$INSTANCE_ID in \$AZ</h1>\" > /usr/share/nginx/html/index.html
SCRIPT
)\"
  }" \
  --query 'LaunchTemplate.LaunchTemplateId' --output text)

echo "Launch Template: $LT_ID"

# Step 2: Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name "webapp-alb" \
  --subnets $PUBLIC_SUBNET_A $PUBLIC_SUBNET_B \
  --security-groups $SG_WEB \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name "webapp-tg" \
  --protocol HTTP --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)

echo "ALB DNS: $ALB_DNS"

# Step 3: Create Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "webapp-asg" \
  --launch-template LaunchTemplateId=$LT_ID,Version='$Latest' \
  --min-size 2 --max-size 10 --desired-capacity 2 \
  --vpc-zone-identifier "${PUBLIC_SUBNET_A},${PUBLIC_SUBNET_B}" \
  --target-group-arns $TG_ARN \
  --health-check-type ELB \
  --health-check-grace-period 300

# Step 4: Target tracking scaling policy (maintain 60% CPU)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name "webapp-asg" \
  --policy-name "cpu-tracking" \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

echo ""
echo "✅ Auto Scaling setup complete!"
echo "Website: http://$ALB_DNS"
echo "Refresh multiple times — you'll see different instance IDs!"
```

### Test Auto Scaling

```bash
# Simulate load to trigger scale-out
# SSH into one instance and run:
# stress --cpu 4 --timeout 300

# Watch scaling activity
watch -n 10 "aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name webapp-asg \
  --max-items 5 \
  --query 'Activities[*].{Status:StatusCode,Cause:Cause}' \
  --output table"

# Watch instance count
watch -n 5 "aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names webapp-asg \
  --query 'AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Running:Instances[?LifecycleState==\`InService\`]|length(@)}'"
```

### What You Learned
- ✅ Launch templates for consistent instance config
- ✅ ALB distributing traffic across instances
- ✅ Target tracking auto scaling
- ✅ Health checks and grace periods

---

## Scenario 14 — Serverless REST API

**Skills**: Lambda, API Gateway, DynamoDB  
**Time**: 45 minutes

### Architecture
```
Client → API Gateway → Lambda → DynamoDB
  GET /users          list_users()
  POST /users         create_user()
  GET /users/{id}     get_user()
  DELETE /users/{id}  delete_user()
```

### Step-by-Step

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Step 1: Create DynamoDB table
aws dynamodb create-table \
  --table-name "users" \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION

# Step 2: Create Lambda execution role
aws iam create-role \
  --role-name "lambda-api-role" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'

aws iam attach-role-policy \
  --role-name "lambda-api-role" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

aws iam attach-role-policy \
  --role-name "lambda-api-role" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"

ROLE_ARN=$(aws iam get-role --role-name lambda-api-role --query 'Role.Arn' --output text)
sleep 10  # Wait for role propagation
```

```python
# lambda_function.py
import boto3
import json
import uuid
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')

def handler(event, context):
    method = event['httpMethod']
    path   = event['path']
    body   = json.loads(event.get('body') or '{}')
    params = event.get('pathParameters') or {}

    try:
        if method == 'GET' and path == '/users':
            result = table.scan()
            return ok(result['Items'])

        elif method == 'POST' and path == '/users':
            user = {'id': str(uuid.uuid4()), **body}
            table.put_item(Item=user)
            return created(user)

        elif method == 'GET' and '/users/' in path:
            result = table.get_item(Key={'id': params['id']})
            item = result.get('Item')
            return ok(item) if item else not_found()

        elif method == 'DELETE' and '/users/' in path:
            table.delete_item(Key={'id': params['id']})
            return {'statusCode': 204, 'body': ''}

        return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def ok(data):
    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(data, default=str)}

def created(data):
    return {'statusCode': 201, 'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(data, default=str)}

def not_found():
    return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
```

```bash
# Package and deploy Lambda
zip function.zip lambda_function.py

LAMBDA_ARN=$(aws lambda create-function \
  --function-name "users-api" \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler lambda_function.handler \
  --zip-file fileb://function.zip \
  --architectures arm64 \
  --query 'FunctionArn' --output text)

# Create API Gateway
API_ID=$(aws apigateway create-rest-api \
  --name "users-api" \
  --query 'id' --output text)

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[0].id' --output text)

# Create /users resource
USERS_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part "users" \
  --query 'id' --output text)

# Add GET method to /users
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $USERS_ID \
  --http-method GET \
  --authorization-type NONE

# Connect to Lambda
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $USERS_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name "users-api" \
  --statement-id "apigateway-invoke" \
  --action "lambda:InvokeFunction" \
  --principal "apigateway.amazonaws.com" \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*"

# Deploy API
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
echo "API URL: $API_URL"

# Test
curl -X POST $API_URL/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

curl $API_URL/users
```

### What You Learned
- ✅ Serverless architecture (no servers to manage)
- ✅ Lambda + API Gateway integration
- ✅ DynamoDB as serverless database
- ✅ IAM roles for Lambda permissions

---

## Scenario 15 — Monitoring & Logging System

**Skills**: CloudWatch, Alarms, Log Insights  
**Time**: 30 minutes

```bash
# Step 1: Create SNS topic for alerts
TOPIC_ARN=$(aws sns create-topic --name "ops-alerts" --query 'TopicArn' --output text)

# Subscribe your email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint "your-email@example.com"

echo "Check your email to confirm SNS subscription!"

# Step 2: Create CloudWatch alarms
# EC2 CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu" \
  --alarm-description "CPU > 80% for 5 minutes" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=webapp-asg \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions $TOPIC_ARN \
  --ok-actions $TOPIC_ARN

# ALB 5xx error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "high-error-rate" \
  --alarm-description "5xx errors > 10 in 5 minutes" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --dimensions Name=LoadBalancer,Value=$(aws elbv2 describe-load-balancers \
    --names webapp-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text | \
    sed 's|arn:aws:elasticloadbalancing:[^:]*:[^:]*:loadbalancer/||') \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions $TOPIC_ARN

# Step 3: Custom metric from application
aws cloudwatch put-metric-data \
  --namespace "MyApp/Business" \
  --metric-data '[
    {"MetricName": "OrdersProcessed", "Value": 150, "Unit": "Count"},
    {"MetricName": "Revenue", "Value": 7500.00, "Unit": "None"}
  ]'

# Step 4: CloudWatch Logs Insights query
LOG_GROUP="/aws/lambda/users-api"

aws logs create-log-group --log-group-name $LOG_GROUP 2>/dev/null || true

# Query: find errors in last hour
QUERY_ID=$(aws logs start-query \
  --log-group-name $LOG_GROUP \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count(*) as errorCount by bin(5m)
    | sort @timestamp desc
  ' \
  --query 'queryId' --output text)

sleep 5
aws logs get-query-results --query-id $QUERY_ID

echo "✅ Monitoring setup complete!"
```

### What You Learned
- ✅ CloudWatch alarms with SNS notifications
- ✅ Custom business metrics
- ✅ Log Insights for querying logs
- ✅ Monitoring infrastructure + application

---

## Scenario 16 — Event-Driven File Processing

**Skills**: S3 events, Lambda, Python  
**Time**: 30 minutes

### Architecture
```
User uploads CSV to S3
        ↓
S3 Event Notification
        ↓
Lambda triggered automatically
        ↓
Process CSV (validate, transform)
        ↓
Store results in DynamoDB
        ↓
Send notification via SNS
```

```python
# csv_processor.py
import boto3
import csv
import io
import json
import os

s3        = boto3.client('s3')
dynamodb  = boto3.resource('dynamodb')
sns       = boto3.client('sns')
table     = dynamodb.Table(os.environ['TABLE_NAME'])
TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key    = record['s3']['object']['key']

        print(f"Processing: s3://{bucket}/{key}")

        # Download CSV
        response = s3.get_object(Bucket=bucket, Key=key)
        content  = response['Body'].read().decode('utf-8')

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))
        rows   = list(reader)
        valid  = 0
        errors = []

        # Process each row
        with table.batch_writer() as batch:
            for i, row in enumerate(rows):
                try:
                    # Validate
                    if not row.get('name') or not row.get('email'):
                        errors.append(f"Row {i+1}: missing name or email")
                        continue

                    # Store in DynamoDB
                    batch.put_item(Item={
                        'id':    f"{key}_{i}",
                        'name':  row['name'].strip(),
                        'email': row['email'].strip().lower(),
                        'source_file': key,
                    })
                    valid += 1
                except Exception as e:
                    errors.append(f"Row {i+1}: {str(e)}")

        # Send summary notification
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"CSV Processing Complete: {key}",
            Message=json.dumps({
                'file': key,
                'total_rows': len(rows),
                'valid_rows': valid,
                'errors': errors[:10]  # First 10 errors
            }, indent=2)
        )

        print(f"✅ Processed {valid}/{len(rows)} rows from {key}")
    return {'statusCode': 200}
```

```bash
# Deploy and configure
zip csv_processor.zip csv_processor.py

aws lambda create-function \
  --function-name "csv-processor" \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler csv_processor.handler \
  --zip-file fileb://csv_processor.zip \
  --environment Variables="{TABLE_NAME=users,SNS_TOPIC_ARN=${TOPIC_ARN}}"

# Grant S3 permission to invoke Lambda
aws lambda add-permission \
  --function-name "csv-processor" \
  --statement-id "s3-trigger" \
  --action "lambda:InvokeFunction" \
  --principal "s3.amazonaws.com" \
  --source-arn "arn:aws:s3:::my-uploads-bucket"

# Configure S3 event notification
aws s3api put-bucket-notification-configuration \
  --bucket "my-uploads-bucket" \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789:function:csv-processor",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {"FilterRules": [{"Name": "suffix", "Value": ".csv"}]}
      }
    }]
  }'

# Test: upload a CSV
cat > test_users.csv << 'EOF'
name,email,age
Alice,alice@example.com,30
Bob,bob@example.com,25
,invalid@example.com,20
EOF

aws s3 cp test_users.csv s3://my-uploads-bucket/uploads/test_users.csv

# Watch Lambda logs
aws logs tail /aws/lambda/csv-processor --follow
```

### What You Learned
- ✅ Event-driven architecture
- ✅ S3 event notifications
- ✅ Lambda triggered by S3 uploads
- ✅ Batch DynamoDB writes
- ✅ SNS notifications from Lambda

---

## Summary — Advanced Level Complete ✅

| Scenario | Services | Key Concept |
|---------|---------|------------|
| 13 | ALB, ASG | High availability, auto scaling |
| 14 | Lambda, API GW, DynamoDB | Serverless architecture |
| 15 | CloudWatch, SNS | Monitoring and alerting |
| 16 | S3, Lambda, DynamoDB | Event-driven processing |

**Next**: Move to `20_scenarios_data_engineering.md` → Data lake, ETL, Kinesis, Spark on EMR.
