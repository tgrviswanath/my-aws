# CloudWatch — Real-World Use Cases

## Use Case 1: Custom Business Metrics Dashboard

**Business Problem**: Track business KPIs (orders/min, revenue/hr, error rate) alongside infrastructure metrics in one dashboard.

```python
# Emit custom metrics from your application
import boto3
import time
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def record_order_metrics(order_count: int, revenue: float, failed_count: int):
    """Emit business metrics to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='MyApp/Business',
        MetricData=[
            {
                'MetricName': 'OrdersProcessed',
                'Value': order_count,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'production'},
                    {'Name': 'Region', 'Value': 'us-east-1'}
                ]
            },
            {
                'MetricName': 'Revenue',
                'Value': revenue,
                'Unit': 'None',
                'Dimensions': [{'Name': 'Environment', 'Value': 'production'}]
            },
            {
                'MetricName': 'FailedOrders',
                'Value': failed_count,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Environment', 'Value': 'production'}]
            },
            {
                'MetricName': 'OrderSuccessRate',
                'Value': (order_count - failed_count) / max(order_count, 1) * 100,
                'Unit': 'Percent',
                'Dimensions': [{'Name': 'Environment', 'Value': 'production'}]
            }
        ]
    )

# Call from your Lambda/EC2 every minute
record_order_metrics(order_count=150, revenue=7500.00, failed_count=3)
```

```bash
# Create dashboard with business + infra metrics
aws cloudwatch put-dashboard \
  --dashboard-name "production-overview" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 8, "height": 6,
        "properties": {
          "title": "Orders Per Minute",
          "metrics": [["MyApp/Business", "OrdersProcessed", "Environment", "production",
                       {"stat": "Sum", "period": 60, "label": "Orders/min"}]],
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "x": 8, "y": 0, "width": 8, "height": 6,
        "properties": {
          "title": "Revenue Per Hour",
          "metrics": [["MyApp/Business", "Revenue", "Environment", "production",
                       {"stat": "Sum", "period": 3600}]]
        }
      },
      {
        "type": "metric",
        "x": 16, "y": 0, "width": 8, "height": 6,
        "properties": {
          "title": "Order Success Rate %",
          "metrics": [["MyApp/Business", "OrderSuccessRate", "Environment", "production",
                       {"stat": "Average", "period": 300}]],
          "yAxis": {"left": {"min": 0, "max": 100}}
        }
      },
      {
        "type": "alarm",
        "x": 0, "y": 6, "width": 24, "height": 4,
        "properties": {
          "title": "Active Alarms",
          "alarms": [
            "arn:aws:cloudwatch:us-east-1:123456789:alarm:high-error-rate",
            "arn:aws:cloudwatch:us-east-1:123456789:alarm:low-order-rate"
          ]
        }
      }
    ]
  }'
```

**What you learn**: Custom metrics, namespaces, dimensions, dashboard creation.

---

## Use Case 2: Intelligent Alerting (Reduce Alert Fatigue)

**Business Problem**: Too many false-positive alerts. Need smart alerting that only pages on-call when multiple signals are bad simultaneously.

```bash
# 1. Individual metric alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "high-error-rate" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/abc123 \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching

aws cloudwatch put-metric-alarm \
  --alarm-name "high-latency" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/abc123 \
  --extended-statistic p99 \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 2.0 \
  --comparison-operator GreaterThanThreshold

aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=prod-asg \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# 2. Composite alarm: only page if BOTH errors AND latency are high
# (reduces false positives from transient spikes)
aws cloudwatch put-composite-alarm \
  --alarm-name "production-critical" \
  --alarm-description "Page on-call: high errors AND high latency" \
  --alarm-rule "ALARM(high-error-rate) AND ALARM(high-latency)" \
  --alarm-actions arn:aws:sns:us-east-1:123456789:pagerduty-critical \
  --ok-actions arn:aws:sns:us-east-1:123456789:pagerduty-critical

# 3. Anomaly detection alarm (dynamic threshold based on historical patterns)
aws cloudwatch put-metric-alarm \
  --alarm-name "order-count-anomaly" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "MyApp/Business",
          "MetricName": "OrdersProcessed",
          "Dimensions": [{"Name": "Environment", "Value": "production"}]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": true
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)",
      "Label": "Expected range",
      "ReturnData": true
    }
  ]' \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --threshold-metric-id ad1 \
  --evaluation-periods 3 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789:ops-alerts
```

**What you learn**: Composite alarms, anomaly detection, p99 latency alarms, alert fatigue reduction.

---

## Use Case 3: Log Insights for Incident Investigation

```bash
# Scenario: Production incident — users reporting 500 errors since 14:30

# 1. Find error rate over time
aws logs start-query \
  --log-group-name "/aws/lambda/order-api" \
  --start-time $(date -d '2 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message, level, requestId
    | filter level = "ERROR"
    | stats count(*) as errorCount by bin(5m)
    | sort @timestamp asc
  '

# 2. Find the most common error messages
aws logs start-query \
  --log-group-name "/aws/lambda/order-api" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @message
    | filter level = "ERROR"
    | parse @message "Error: *" as errorMsg
    | stats count(*) as count by errorMsg
    | sort count desc
    | limit 10
  '

# 3. Find slow requests (P99 latency)
aws logs start-query \
  --log-group-name "/aws/lambda/order-api" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed
    | filter @type = "REPORT"
    | stats
        count() as invocations,
        avg(@duration) as avgMs,
        pct(@duration, 99) as p99Ms,
        max(@duration) as maxMs
    | sort p99Ms desc
  '

# 4. Correlate with specific request ID
REQUEST_ID="abc-123-def"
aws logs start-query \
  --log-group-name "/aws/lambda/order-api" \
  --start-time $(date -d '2 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string "
    fields @timestamp, @message
    | filter requestId = '${REQUEST_ID}'
    | sort @timestamp asc
  "

# 5. Get query results
QUERY_ID="<query-id-from-above>"
aws logs get-query-results --query-id $QUERY_ID
```

**What you learn**: Logs Insights queries, incident investigation workflow, P99 latency analysis.

---

## Use Case 4: CloudWatch Agent for EC2 Memory & Disk

```bash
# Default EC2 metrics don't include memory or disk — need CloudWatch Agent

# 1. Install CloudWatch Agent
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-ConfigureAWSPackage" \
  --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}'

# 2. Create agent config
cat > /tmp/cloudwatch-agent-config.json << 'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent", "mem_available"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent", "disk_free"],
        "resources": ["/", "/data"],
        "metrics_collection_interval": 60
      },
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "totalcpu": true
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/application.log",
            "log_group_name": "/myapp/production",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S"
          }
        ]
      }
    }
  }
}
EOF

# 3. Push config to SSM Parameter Store
aws ssm put-parameter \
  --name "/cloudwatch-agent/config/prod" \
  --type String \
  --value file:///tmp/cloudwatch-agent-config.json \
  --overwrite

# 4. Start agent with config
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AmazonCloudWatch-ManageAgent" \
  --parameters '{
    "action": ["configure"],
    "optionalConfigurationSource": ["ssm"],
    "optionalConfigurationLocation": ["/cloudwatch-agent/config/prod"],
    "optionalRestart": ["yes"]
  }'

# 5. Alert on high memory
aws cloudwatch put-metric-alarm \
  --alarm-name "high-memory-usage" \
  --metric-name mem_used_percent \
  --namespace CWAgent \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:ops-alerts
```

**What you learn**: CloudWatch Agent, custom metrics (memory/disk), SSM for agent management.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Alerting on every metric spike | Alert fatigue, ignored alerts | Use composite alarms + evaluation periods |
| No custom business metrics | Can't see business impact | Emit custom metrics from application code |
| Short log retention | Can't investigate old incidents | Set retention to 90+ days for production |
| Not using anomaly detection | Static thresholds miss seasonal patterns | Use anomaly detection for variable metrics |
| Alerting without runbooks | On-call doesn't know what to do | Link runbook URL in alarm description |
| Missing memory/disk metrics | Can't detect OOM or disk full | Install CloudWatch Agent |
