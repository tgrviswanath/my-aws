# AWS Developer & DevOps Interview Preparation

## Developer Associate Topics

### Serverless & Lambda

**Q1: How do you optimize Lambda performance?**
```
1. Memory: More memory = more CPU. Profile with Lambda Power Tuning.
2. Package size: Smaller = faster cold start. Use layers for dependencies.
3. Init code: Move SDK clients, DB connections outside handler.
4. Provisioned concurrency: Pre-warm for latency-sensitive functions.
5. ARM/Graviton2: 20% cheaper, often faster.
6. Runtime: Python/Node.js cold start faster than Java.
7. Lambda SnapStart: For Java — snapshot initialized state.
8. Connection reuse: Reuse HTTP connections (keep-alive).
```

**Q2: How do you handle Lambda timeouts?**
```
Prevention:
- Set timeout to 3x your expected execution time
- Use async patterns for long operations
- Break into smaller functions with Step Functions

Detection:
- CloudWatch Logs: "Task timed out after X seconds"
- CloudWatch Metric: Duration approaching timeout

Handling:
- Async invocations: retry automatically (2 times)
- SQS trigger: message returns to queue after visibility timeout
- Step Functions: configure timeout + catch block
```

---

### DynamoDB Development

**Q3: How do you implement pagination in DynamoDB?**
```python
def get_orders_paginated(customer_id: str, page_size: int = 20, last_key: dict = None):
    kwargs = {
        'KeyConditionExpression': Key('customerId').eq(customer_id),
        'Limit': page_size,
        'ScanIndexForward': False  # Newest first
    }
    
    if last_key:
        kwargs['ExclusiveStartKey'] = last_key
    
    response = table.query(**kwargs)
    
    return {
        'items': response['Items'],
        'nextKey': response.get('LastEvaluatedKey'),  # None if last page
        'count': response['Count']
    }
```

**Q4: How do you handle DynamoDB conditional writes?**
```python
# Optimistic locking with version number
def update_order_status(order_id: str, customer_id: str, 
                        new_status: str, expected_version: int):
    try:
        table.update_item(
            Key={'customerId': customer_id, 'orderId': order_id},
            UpdateExpression='SET #s = :status, version = :new_version',
            ConditionExpression='version = :expected_version AND attribute_exists(orderId)',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': new_status,
                ':new_version': expected_version + 1,
                ':expected_version': expected_version
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise OptimisticLockException("Item was modified by another process")
        raise
```

---

### API Gateway

**Q5: What is the difference between REST API and HTTP API in API Gateway?**

| Feature | REST API | HTTP API |
|---------|---------|---------|
| Cost | Higher | ~70% cheaper |
| Latency | Higher | Lower |
| Features | Full (usage plans, caching, WAF) | Basic |
| Auth | Cognito, Lambda, IAM | JWT, Lambda, IAM |
| WebSocket | ❌ | ❌ (use WebSocket API) |
| VPC Link | ✅ | ✅ |
| Use case | Complex APIs needing all features | Simple APIs, microservices |

**Choose HTTP API** unless you need: API keys/usage plans, request/response transformation, caching, or AWS WAF integration.

---

### SQS/SNS Development

**Q6: How do you implement a dead letter queue pattern?**
```python
# Producer: send to main queue
sqs.send_message(
    QueueUrl=MAIN_QUEUE_URL,
    MessageBody=json.dumps(order),
    MessageAttributes={
        'retryCount': {'DataType': 'Number', 'StringValue': '0'}
    }
)

# Consumer: process with error handling
def process_message(record):
    body = json.loads(record['body'])
    retry_count = int(record.get('messageAttributes', {})
                      .get('retryCount', {}).get('stringValue', '0'))
    
    try:
        process_order(body)
        # Success: message auto-deleted after Lambda returns
    except RetryableError as e:
        # Raise exception: message returns to queue
        # After maxReceiveCount (3), goes to DLQ
        raise
    except NonRetryableError as e:
        # Log and don't raise: message deleted, won't retry
        logger.error(f"Non-retryable error: {e}")
        send_to_error_tracking(body, str(e))

# DLQ processor: alert and investigate
def process_dlq(record):
    body = json.loads(record['body'])
    logger.error(f"Message in DLQ: {body}")
    send_alert(f"Order {body['orderId']} failed processing")
```

---

## DevOps Engineer Topics

### CI/CD

**Q7: How do you implement zero-downtime deployments for ECS?**
```
Blue/Green with CodeDeploy:
1. CodeDeploy creates new task set (green)
2. Registers green tasks with test listener (port 8080)
3. Runs BeforeAllowTraffic hook (smoke tests)
4. Shifts traffic: 10% → 50% → 100% (configurable)
5. Runs AfterAllowTraffic hook (validation)
6. Terminates blue task set after stabilization period

Rollback triggers:
- CloudWatch alarm breach during deployment
- Hook function returns failure
- Manual rollback via console/CLI

Key settings:
- Deployment config: ECSCanary10Percent5Minutes
- Stabilization time: 5-10 minutes
- Alarm: error rate > 1%, latency p99 > 2s
```

**Q8: How do you manage environment-specific configurations in a CI/CD pipeline?**
```
Strategy:
1. SSM Parameter Store: /myapp/{env}/database_host
2. Secrets Manager: /myapp/{env}/database_password
3. Environment variables in task definition (non-sensitive)
4. Feature flags in DynamoDB or AppConfig

Pipeline:
- Same artifact (Docker image) deployed to all environments
- Environment injected at runtime via SSM/Secrets Manager
- Never bake environment config into the image

CodeBuild:
- Use different IAM roles per environment
- Role has access only to that environment's parameters
```

---

### CloudFormation Advanced

**Q9: How do you handle CloudFormation stack updates that require resource replacement?**
```
Problem: Some changes (e.g., RDS engine version, EC2 key pair) 
require resource replacement → data loss risk

Solutions:
1. Change sets: Review before applying
   aws cloudformation create-change-set ...
   # Check for "Replacement: True" in change set

2. DeletionPolicy: Snapshot
   Type: AWS::RDS::DBInstance
   DeletionPolicy: Snapshot  # Creates snapshot before deletion

3. Retain policy for critical resources
   DeletionPolicy: Retain

4. Blue/green stack update:
   - Create new stack with new config
   - Migrate data
   - Switch DNS
   - Delete old stack

5. Custom resources for complex migrations
```

**Q10: What is a CloudFormation Custom Resource?**
```python
# Lambda-backed custom resource
import cfnresponse
import boto3

def handler(event, context):
    try:
        request_type = event['RequestType']
        
        if request_type == 'Create':
            # Provision resource not supported by CloudFormation
            result = create_resource(event['ResourceProperties'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS, 
                           {'ResourceId': result['id']},
                           physicalResourceId=result['id'])
        
        elif request_type == 'Update':
            update_resource(event['PhysicalResourceId'], 
                          event['ResourceProperties'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {},
                           physicalResourceId=event['PhysicalResourceId'])
        
        elif request_type == 'Delete':
            delete_resource(event['PhysicalResourceId'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {},
                           physicalResourceId=event['PhysicalResourceId'])
    
    except Exception as e:
        cfnresponse.send(event, context, cfnresponse.FAILED, 
                        {'Error': str(e)},
                        physicalResourceId=event.get('PhysicalResourceId', 'error'))
```

---

### Monitoring & Debugging

**Q11: How do you debug a performance issue in production?**
```
Systematic approach:
1. Define the problem: which endpoint, what latency, when started
2. CloudWatch Dashboard: CPU, memory, DB connections, error rate
3. X-Ray Service Map: identify slow service
4. X-Ray Traces: find slow individual requests
5. CloudWatch Logs Insights: query for slow requests
   fields @timestamp, duration, path
   | filter duration > 2000
   | stats avg(duration) by path
   | sort avg(duration) desc
6. RDS Performance Insights: slow queries, wait events
7. ElastiCache metrics: cache hit ratio, evictions

Common findings:
- N+1 query problem → batch queries
- Missing DB index → add index
- Cache miss → warm cache, increase TTL
- Memory pressure → increase instance size
- Connection pool exhausted → RDS Proxy
```

**Q12: How do you set up alerting for a microservices application?**
```
Metrics to alert on:
Service level:
- Error rate > 1% (5xx responses)
- P99 latency > 2 seconds
- Availability < 99.9%

Infrastructure:
- EC2 CPU > 80% for 5 min
- RDS CPU > 80%, connections > 80% max
- ElastiCache evictions > 0
- SQS queue depth > 1000 (processing lag)
- Lambda errors > 1%, throttles > 0

Business:
- Orders per minute drops > 50% from baseline
- Payment failures > 0.1%

Alert routing:
- Critical (P1): PagerDuty → on-call engineer
- Warning (P2): Slack #alerts channel
- Info (P3): Email digest

Composite alarms to reduce noise:
- Alert only if BOTH error rate AND latency are high
```

---

## Troubleshooting Scenarios

**Q13: Lambda function works locally but fails in AWS. Debug steps:**
```
1. Check CloudWatch Logs for error message
2. Verify IAM role has required permissions
   - Missing: s3:GetObject, dynamodb:PutItem, etc.
3. Check VPC configuration
   - Lambda in VPC needs NAT Gateway for internet
   - Lambda needs VPC endpoints for AWS services
4. Check environment variables
   - Missing or wrong values
5. Check timeout
   - Lambda timeout < downstream service timeout
6. Check memory
   - OOM errors in logs
7. Check deployment package
   - Missing dependencies
   - Wrong architecture (x86 vs arm64)
8. Check resource limits
   - Concurrency throttling
   - Account-level limits
```

**Q14: ECS task keeps restarting. Debug steps:**
```
1. ECS Console → Service → Events tab
   - "Task failed ELB health checks"
   - "Essential container exited"
2. CloudWatch Logs → /ecs/task-name
   - Application error on startup
   - Missing environment variable
   - DB connection failure
3. Check task definition
   - Correct image tag
   - Sufficient CPU/memory
   - Correct environment variables
4. Check health check
   - Path correct (/health)
   - Port correct
   - Grace period sufficient
5. Check IAM task role
   - Missing permissions for Secrets Manager, S3, etc.
6. Check security groups
   - Task can reach DB, cache, downstream services
```

---

## Quick-Fire Questions

| Question | Answer |
|---------|--------|
| Max Lambda timeout | 15 minutes |
| Max SQS message size | 256KB |
| Max SQS retention | 14 days |
| DynamoDB max item size | 400KB |
| S3 max object size | 5TB |
| Max EC2 EBS volumes | 28 (varies by instance) |
| CloudFormation max resources | 500 per stack |
| Lambda max deployment package | 250MB unzipped |
| API Gateway max timeout | 29 seconds |
| Max Lambda layers | 5 per function |
| ECS max containers per task | No hard limit (practical: 10-20) |
| RDS max read replicas | 5 (RDS), 15 (Aurora) |
