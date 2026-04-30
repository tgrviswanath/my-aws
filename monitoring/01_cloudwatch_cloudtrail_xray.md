# CloudWatch, CloudTrail & X-Ray — Monitoring & Observability

## The Three Pillars of Observability

```
Metrics  → CloudWatch Metrics (what is happening)
Logs     → CloudWatch Logs (what happened in detail)
Traces   → X-Ray (how requests flow through services)
Audit    → CloudTrail (who did what to AWS resources)
```

---

## CloudWatch Metrics

### Key Concepts

```
Namespace: AWS/EC2, AWS/RDS, custom/MyApp
Metric: CPUUtilization, DatabaseConnections
Dimension: InstanceId=i-123, DBInstanceIdentifier=prod-db
Resolution: Standard (1 min), High (1 sec)
Retention: 3hr (1sec), 15days (1min), 63days (5min), 15months (1hr)
```

### Custom Metrics

```bash
# Put custom metric
aws cloudwatch put-metric-data \
  --namespace "MyApp/Business" \
  --metric-data '[
    {
      "MetricName": "OrdersProcessed",
      "Value": 42,
      "Unit": "Count",
      "Dimensions": [
        {"Name": "Environment", "Value": "production"},
        {"Name": "Region", "Value": "us-east-1"}
      ]
    },
    {
      "MetricName": "OrderProcessingTime",
      "Value": 250,
      "Unit": "Milliseconds"
    }
  ]'

# Python SDK
import boto3
cloudwatch = boto3.client('cloudwatch')

def record_metric(name: str, value: float, unit: str = 'Count'):
    cloudwatch.put_metric_data(
        Namespace='MyApp/Business',
        MetricData=[{
            'MetricName': name,
            'Value': value,
            'Unit': unit,
            'Dimensions': [
                {'Name': 'Environment', 'Value': 'production'}
            ]
        }]
    )
```

### CloudWatch Alarms

```bash
# CPU alarm with SNS notification
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-prod \
  --alarm-description "CPU > 80% for 5 minutes" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=prod-asg \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:prod-alerts \
  --ok-actions arn:aws:sns:us-east-1:123456789:prod-alerts \
  --treat-missing-data notBreaching

# Composite alarm (multiple conditions)
aws cloudwatch put-composite-alarm \
  --alarm-name prod-critical \
  --alarm-description "Critical: high CPU AND high error rate" \
  --alarm-rule "ALARM(high-cpu-prod) AND ALARM(high-error-rate)" \
  --alarm-actions arn:aws:sns:us-east-1:123456789:pagerduty-critical
```

### CloudWatch Dashboards

```bash
aws cloudwatch put-dashboard \
  --dashboard-name production-overview \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "title": "EC2 CPU Utilization",
          "metrics": [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "prod-asg",
             {"stat": "Average", "period": 300}]
          ],
          "period": 300,
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "properties": {
          "title": "ALB Request Count & Errors",
          "metrics": [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/my-alb/abc123"],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/my-alb/abc123",
             {"color": "#d62728"}]
          ]
        }
      }
    ]
  }'
```

---

## CloudWatch Logs

### Log Groups and Streams

```bash
# Create log group with retention
aws logs create-log-group \
  --log-group-name /myapp/production

aws logs put-retention-policy \
  --log-group-name /myapp/production \
  --retention-in-days 90

# Encrypt log group
aws logs associate-kms-key \
  --log-group-name /myapp/production \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/abc-123

# Query logs with CloudWatch Logs Insights
aws logs start-query \
  --log-group-name /myapp/production \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message, level, requestId
    | filter level = "ERROR"
    | stats count(*) as errorCount by bin(5m)
    | sort @timestamp desc
    | limit 100
  '
```

### CloudWatch Logs Insights Queries

```
# Find slow API calls
fields @timestamp, path, duration
| filter duration > 1000
| stats avg(duration) as avgDuration, count() as count by path
| sort avgDuration desc
| limit 20

# Error rate by endpoint
fields @timestamp, path, statusCode
| filter statusCode >= 400
| stats count() as errors by path, statusCode
| sort errors desc

# Lambda cold starts
fields @timestamp, @type, @duration, @billedDuration, @initDuration
| filter @type = "REPORT"
| stats count() as invocations, 
        avg(@duration) as avgDuration,
        count(@initDuration) as coldStarts,
        avg(@initDuration) as avgColdStart
| sort coldStarts desc

# P99 latency
fields @timestamp, duration
| stats pct(duration, 99) as p99, pct(duration, 95) as p95, avg(duration) as avg
```

### Metric Filters (Logs → Metrics)

```bash
# Create metric filter for error count
aws logs put-metric-filter \
  --log-group-name /myapp/production \
  --filter-name error-count \
  --filter-pattern '[timestamp, requestId, level="ERROR", ...]' \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=MyApp,metricValue=1,unit=Count

# JSON log filter
aws logs put-metric-filter \
  --log-group-name /myapp/production \
  --filter-name http-5xx \
  --filter-pattern '{ $.statusCode >= 500 }' \
  --metric-transformations \
    metricName=HTTP5xxCount,metricNamespace=MyApp,metricValue=1
```

### CloudWatch Agent (EC2)

```json
// /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent"],
        "resources": ["/", "/data"],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/myapp/app.log",
            "log_group_name": "/myapp/production",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S"
          }
        ]
      }
    }
  }
}
```

---

## AWS CloudTrail

CloudTrail records all API calls made in your AWS account — who did what, when, from where.

```bash
# Create trail (multi-region, all events)
aws cloudtrail create-trail \
  --name prod-audit-trail \
  --s3-bucket-name my-cloudtrail-logs \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/abc-123 \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789:log-group:CloudTrail \
  --cloud-watch-logs-role-arn arn:aws:iam::123456789:role/CloudTrailRole

aws cloudtrail start-logging --name prod-audit-trail

# Enable data events (S3 object-level, Lambda invocations)
aws cloudtrail put-event-selectors \
  --trail-name prod-audit-trail \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::sensitive-bucket/"]
        },
        {
          "Type": "AWS::Lambda::Function",
          "Values": ["arn:aws:lambda"]
        }
      ]
    }
  ]'

# Query CloudTrail events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T00:00:00Z

# Find who deleted an S3 object
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=my-bucket \
  --start-time 2024-01-15T00:00:00Z
```

### CloudTrail Insights (Anomaly Detection)

```bash
aws cloudtrail put-insight-selectors \
  --trail-name prod-audit-trail \
  --insight-selectors '[
    {"InsightType": "ApiCallRateInsight"},
    {"InsightType": "ApiErrorRateInsight"}
  ]'
```

---

## AWS X-Ray — Distributed Tracing

X-Ray traces requests as they travel through your distributed application.

```
Request → API Gateway → Lambda → DynamoDB
                     ↘ SQS → Lambda → RDS

X-Ray shows: latency at each hop, errors, throttles, service map
```

### Instrument Lambda

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch all supported libraries (boto3, requests, etc.)
patch_all()

@xray_recorder.capture('process_order')
def process_order(order_id: str):
    # Add custom annotations (indexed, searchable)
    xray_recorder.current_subsegment().put_annotation('orderId', order_id)
    
    # Add metadata (not indexed)
    xray_recorder.current_subsegment().put_metadata('orderDetails', {
        'items': 3,
        'total': 99.99
    })
    
    with xray_recorder.in_subsegment('validate_inventory'):
        # This creates a child subsegment
        check_inventory(order_id)
    
    return True

def handler(event, context):
    order_id = event['orderId']
    
    # X-Ray automatically traces Lambda invocations
    # when active tracing is enabled on the function
    result = process_order(order_id)
    return {'statusCode': 200, 'body': 'OK'}
```

### X-Ray Groups and Sampling

```bash
# Create sampling rule (trace 5% of requests, always trace errors)
aws xray create-sampling-rule \
  --sampling-rule '{
    "RuleName": "production-sampling",
    "Priority": 1,
    "FixedRate": 0.05,
    "ReservoirSize": 5,
    "ServiceName": "my-api",
    "ServiceType": "AWS::ApiGateway::Stage",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "ResourceARN": "*",
    "Version": 1
  }'

# Create X-Ray group for filtering
aws xray create-group \
  --group-name errors-only \
  --filter-expression 'fault = true OR error = true'
```

---

## Structured Logging Best Practices

```python
import json
import logging
import time
import uuid

class StructuredLogger:
    def __init__(self, service_name: str):
        self.logger = logging.getLogger(service_name)
        self.service = service_name
    
    def _log(self, level: str, message: str, **kwargs):
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'level': level,
            'service': self.service,
            'message': message,
            **kwargs
        }
        getattr(self.logger, level.lower())(json.dumps(log_entry))
    
    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('ERROR', message, **kwargs)

logger = StructuredLogger('order-service')

def handler(event, context):
    request_id = context.aws_request_id
    
    logger.info('Processing order',
        requestId=request_id,
        orderId=event.get('orderId'),
        userId=event.get('userId')
    )
    
    try:
        result = process(event)
        logger.info('Order processed successfully',
            requestId=request_id,
            duration=result['duration']
        )
        return result
    except Exception as e:
        logger.error('Order processing failed',
            requestId=request_id,
            error=str(e),
            errorType=type(e).__name__
        )
        raise
```

---

## Interview Q&A

### Q1: What is the difference between CloudWatch and CloudTrail?
**CloudWatch**: Operational monitoring — metrics, logs, alarms, dashboards. Answers "Is my application healthy? What's the performance?" Monitors AWS resources and applications.
**CloudTrail**: Audit and compliance — records all AWS API calls (who, what, when, from where). Answers "Who deleted that S3 bucket? Who changed this security group?" Governance and security auditing.

### Q2: How do you debug a Lambda function in production?
1. CloudWatch Logs: Check `/aws/lambda/function-name` for errors and stack traces
2. CloudWatch Logs Insights: Query for errors, slow invocations, cold starts
3. X-Ray: Trace request flow, identify slow downstream calls
4. Lambda Insights: Enhanced monitoring (memory, CPU, init duration)
5. CloudWatch Metrics: Errors, Duration, Throttles, ConcurrentExecutions
6. Dead Letter Queue: Check for failed async invocations

### Q3: What is CloudWatch Logs Insights and when would you use it?
Logs Insights is an interactive query service for CloudWatch Logs. Use it to: analyze log data with SQL-like queries, find errors and patterns, calculate statistics (P99 latency, error rates), create visualizations. Much faster than downloading and grepping logs. Use for: incident investigation, performance analysis, security auditing.

### Q4: How do you set up alerting for a production application?
1. CloudWatch Alarms on key metrics: CPU, memory, error rate, latency, queue depth
2. Composite alarms to reduce alert noise
3. SNS topics for routing: critical → PagerDuty, warning → Slack
4. CloudWatch Anomaly Detection for dynamic thresholds
5. Metric filters on logs for application-level errors
6. Health Dashboard for AWS service health
7. Synthetic monitoring (CloudWatch Synthetics) for end-to-end checks

### Q5: What is distributed tracing and why is it important for microservices?
In microservices, a single user request may touch 10+ services. When something is slow or fails, you need to know which service is the culprit. X-Ray assigns a trace ID to each request and propagates it through all services. You can see the full request path, latency at each hop, errors, and service dependencies. Without tracing, debugging microservices is like finding a needle in a haystack.
