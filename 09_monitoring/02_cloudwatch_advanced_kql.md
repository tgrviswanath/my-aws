# CloudWatch Advanced — Logs Insights, Dashboards & Anomaly Detection

## CloudWatch Logs Insights — Advanced Queries

```
CloudWatch Logs Insights uses a purpose-built query language.
Key commands: fields, filter, stats, sort, limit, parse, pattern
```

### Performance Analysis

```
# P50/P95/P99 latency by API endpoint
fields @timestamp, path, duration, statusCode
| filter duration > 0
| stats
    count() as requests,
    avg(duration) as avgMs,
    pct(duration, 50) as p50Ms,
    pct(duration, 95) as p95Ms,
    pct(duration, 99) as p99Ms,
    count_distinct(requestId) as uniqueRequests
  by path
| sort p95Ms desc
| limit 20

# Error rate over time (5-minute buckets)
fields @timestamp, statusCode
| filter statusCode >= 400
| stats
    count() as errors,
    count_distinct(requestId) as uniqueErrors
  by bin(5m)
| sort @timestamp asc

# Lambda cold start analysis
fields @timestamp, @type, @duration, @billedDuration, @initDuration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| stats
    count() as invocations,
    count(@initDuration) as coldStarts,
    avg(@duration) as avgDuration,
    avg(@initDuration) as avgColdStart,
    pct(@duration, 99) as p99Duration,
    avg(@maxMemoryUsed) as avgMemoryUsed
| sort coldStarts desc

# Find slow DynamoDB operations
fields @timestamp, @message
| filter @message like /DynamoDB/
| parse @message "duration=* ms" as duration
| filter duration > 100
| stats count() as slowOps, avg(duration) as avgMs by bin(5m)
| sort @timestamp desc
```

### Security Analysis

```
# Failed API calls by user
fields @timestamp, userIdentity.arn, eventName, errorCode, errorMessage
| filter errorCode like /AccessDenied/ or errorCode like /UnauthorizedAccess/
| stats count() as deniedCalls by userIdentity.arn, eventName
| sort deniedCalls desc
| limit 20

# Root account usage (should be zero)
fields @timestamp, userIdentity.type, eventName, sourceIPAddress
| filter userIdentity.type = "Root"
| sort @timestamp desc

# Security group changes
fields @timestamp, userIdentity.arn, eventName, requestParameters
| filter eventName in ["AuthorizeSecurityGroupIngress", "RevokeSecurityGroupIngress",
                       "CreateSecurityGroup", "DeleteSecurityGroup"]
| sort @timestamp desc

# S3 public access changes
fields @timestamp, userIdentity.arn, eventName, requestParameters.bucketName
| filter eventName in ["PutBucketAcl", "PutBucketPolicy", "DeleteBucketPolicy",
                       "PutPublicAccessBlock"]
| sort @timestamp desc

# Detect impossible travel (multiple regions in short time)
fields @timestamp, userIdentity.arn, awsRegion, sourceIPAddress
| filter userIdentity.type = "IAMUser"
| stats
    count_distinct(awsRegion) as regions,
    count_distinct(sourceIPAddress) as ips,
    earliest(@timestamp) as firstSeen,
    latest(@timestamp) as lastSeen
  by userIdentity.arn
| filter regions > 3
| sort regions desc
```

### Cost Analysis

```
# Lambda cost estimation
fields @timestamp, @billedDuration, @memorySize
| filter @type = "REPORT"
| stats
    sum(@billedDuration) as totalBilledMs,
    count() as invocations,
    sum(@billedDuration * @memorySize / 1024 / 1000) as gbSeconds
  by bin(1d)
| sort @timestamp desc

# Data transfer analysis
fields @timestamp, bytes, destinationAddress
| filter bytes > 1000000
| stats sum(bytes) as totalBytes by destinationAddress
| sort totalBytes desc
```

---

## CloudWatch Metric Math

```bash
# Create alarm using metric math (error rate %)
aws cloudwatch put-metric-alarm \
  --alarm-name "api-error-rate" \
  --alarm-description "API error rate > 1%" \
  --metrics '[
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "HTTPCode_Target_5XX_Count",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc123"}]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "requests",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "RequestCount",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc123"}]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "errorRate",
      "Expression": "errors / requests * 100",
      "Label": "Error Rate %",
      "ReturnData": true
    }
  ]' \
  --comparison-operator GreaterThanThreshold \
  --threshold 1 \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789:prod-alerts
```

---

## CloudWatch Anomaly Detection

```bash
# Create anomaly detection band for a metric
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/my-alb/abc123 \
  --stat Sum \
  --configuration '{
    "ExcludedTimeRanges": [
      {
        "StartTime": "2024-01-01T00:00:00Z",
        "EndTime": "2024-01-02T00:00:00Z"
      }
    ],
    "MetricTimezone": "America/New_York"
  }'

# Create alarm based on anomaly detection
aws cloudwatch put-metric-alarm \
  --alarm-name "request-count-anomaly" \
  --alarm-description "Request count outside normal band" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "RequestCount",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc123"}]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": true
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)",
      "Label": "RequestCount (expected)",
      "ReturnData": true
    }
  ]' \
  --comparison-operator GreaterThanUpperThreshold \
  --threshold-metric-id ad1 \
  --evaluation-periods 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789:prod-alerts
```

---

## CloudWatch Dashboards

```bash
# Create comprehensive dashboard
aws cloudwatch put-dashboard \
  --dashboard-name production-overview \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "title": "ALB Request Count & Error Rate",
          "metrics": [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/my-alb/abc123",
             {"stat": "Sum", "period": 300, "label": "Requests"}],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/my-alb/abc123",
             {"stat": "Sum", "period": 300, "color": "#d62728", "label": "5xx Errors"}]
          ],
          "view": "timeSeries",
          "period": 300
        }
      },
      {
        "type": "metric",
        "x": 12, "y": 0, "width": 12, "height": 6,
        "properties": {
          "title": "ALB Latency (P50/P95/P99)",
          "metrics": [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/my-alb/abc123",
             {"stat": "p50", "period": 300, "label": "P50"}],
            ["...", {"stat": "p95", "period": 300, "label": "P95", "color": "#ff7f0e"}],
            ["...", {"stat": "p99", "period": 300, "label": "P99", "color": "#d62728"}]
          ],
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "x": 0, "y": 6, "width": 8, "height": 6,
        "properties": {
          "title": "EC2 ASG CPU Utilization",
          "metrics": [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "prod-asg",
             {"stat": "Average", "period": 300}]
          ]
        }
      },
      {
        "type": "metric",
        "x": 8, "y": 6, "width": 8, "height": 6,
        "properties": {
          "title": "RDS CPU & Connections",
          "metrics": [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", "prod-aurora",
             {"stat": "Average", "period": 300, "label": "CPU %"}],
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", "prod-aurora",
             {"stat": "Average", "period": 300, "yAxis": "right", "label": "Connections"}]
          ]
        }
      },
      {
        "type": "alarm",
        "x": 16, "y": 6, "width": 8, "height": 6,
        "properties": {
          "title": "Active Alarms",
          "alarms": [
            "arn:aws:cloudwatch:us-east-1:123456789:alarm:high-cpu-prod",
            "arn:aws:cloudwatch:us-east-1:123456789:alarm:api-error-rate",
            "arn:aws:cloudwatch:us-east-1:123456789:alarm:rds-cpu-high"
          ]
        }
      },
      {
        "type": "log",
        "x": 0, "y": 12, "width": 24, "height": 6,
        "properties": {
          "title": "Recent Application Errors",
          "query": "SOURCE '\''/aws/lambda/prod-api'\'' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20",
          "region": "us-east-1",
          "view": "table"
        }
      }
    ]
  }'
```

---

## Composite Alarms (Reduce Alert Noise)

```bash
# Only alert if BOTH CPU is high AND error rate is high
aws cloudwatch put-composite-alarm \
  --alarm-name "prod-critical-composite" \
  --alarm-description "Critical: high CPU AND high error rate simultaneously" \
  --alarm-rule "ALARM(high-cpu-prod) AND ALARM(api-error-rate)" \
  --alarm-actions arn:aws:sns:us-east-1:123456789:pagerduty-critical \
  --ok-actions arn:aws:sns:us-east-1:123456789:pagerduty-critical

# Alert if ANY of these are in alarm
aws cloudwatch put-composite-alarm \
  --alarm-name "prod-any-critical" \
  --alarm-rule "ALARM(rds-cpu-high) OR ALARM(redis-memory-high) OR ALARM(api-error-rate)"
```

---

## CloudWatch Synthetics (Canary Monitoring)

```bash
# Create synthetic canary (end-to-end monitoring)
aws synthetics create-canary \
  --name prod-api-canary \
  --code Handler=pageLoadBlueprint.handler,S3Bucket=my-canary-bucket,S3Key=canary.zip \
  --artifact-s3-location s3://my-canary-artifacts/prod-api-canary \
  --execution-role-arn arn:aws:iam::123456789:role/CloudWatchSyntheticsRole \
  --schedule Expression="rate(5 minutes)" \
  --run-config TimeoutInSeconds=60,MemoryInMB=960 \
  --runtime-version syn-nodejs-puppeteer-6.2 \
  --start-canary-after-creation

# Canary script (Node.js)
# const synthetics = require('Synthetics');
# const log = require('SyntheticsLogger');
# const syntheticsConfiguration = synthetics.getConfiguration();
#
# const apiCanaryBlueprint = async function () {
#   const URL = "https://api.myapp.com/health";
#   const response = await synthetics.executeHttpStep('Verify API health', URL, {
#     method: 'GET',
#     headers: {'Content-Type': 'application/json'}
#   });
#   if (response.statusCode !== 200) {
#     throw new Error(`API health check failed: ${response.statusCode}`);
#   }
# };
# exports.handler = async () => { return await apiCanaryBlueprint(); };
```

---

## Interview Q&A

### Q1: What is the difference between CloudWatch Metrics and CloudWatch Logs?
**Metrics**: Numerical time-series data (CPU %, request count, latency). Stored for 15 months. Used for alarms and dashboards. Low cost, high performance for trending.
**Logs**: Text/structured log data from applications and services. Queryable with Logs Insights. More expensive to store. Use for debugging, security analysis, detailed investigation. Best practice: emit structured JSON logs, use metric filters to create metrics from log patterns.

### Q2: How do you set up effective alerting without alert fatigue?
1. Alert on symptoms, not causes (high error rate, not high CPU alone)
2. Use composite alarms — only alert when multiple conditions are true
3. Set appropriate thresholds — too sensitive = noise, too loose = misses issues
4. Use anomaly detection for dynamic thresholds
5. Route by severity: critical → PagerDuty, warning → Slack, info → email digest
6. Set evaluation periods (2-3 data points) to avoid transient spikes
7. Use `treat_missing_data = notBreaching` for sparse metrics
8. Regular alarm review — remove stale alarms

### Q3: What is CloudWatch Logs Insights and when would you use it?
Logs Insights is an interactive query service for CloudWatch Logs. Use it to: analyze log data with a purpose-built query language, find errors and patterns, calculate statistics (P99 latency, error rates), create visualizations. Much faster than downloading and grepping logs. Use for: incident investigation, performance analysis, security auditing, cost analysis. Queries are charged per GB scanned — use time ranges and log group filters to reduce cost.

### Q4: How do you monitor a serverless application?
1. Lambda metrics: Errors, Duration, Throttles, ConcurrentExecutions, IteratorAge (SQS/Kinesis)
2. Lambda Insights: Enhanced monitoring (memory, CPU, init duration, network)
3. X-Ray: Distributed tracing across Lambda → DynamoDB → SQS
4. Structured logging: JSON logs with requestId, userId, duration
5. Custom metrics: business metrics (orders/min, payment failures)
6. CloudWatch Synthetics: end-to-end API health checks
7. DLQ monitoring: alert on messages in dead letter queues
8. API Gateway metrics: 4xx/5xx rates, latency, integration errors
