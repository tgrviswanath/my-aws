# Architecture — Project 7.1 CloudWatch Monitoring System

## Monitoring Stack

```
ECS Tasks / ALB
    │ Emit metrics automatically (AWS/ECS, AWS/ApplicationELB namespaces)
    ▼
CloudWatch Metrics
    ├── AWS/ECS: CPUUtilization, MemoryUtilization, RunningTaskCount
    ├── AWS/ApplicationELB: RequestCount, TargetResponseTime, HTTPCode_ELB_5XX
    └── Custom: publish via PutMetricData API
    │
    ├── Alarms (threshold-based)
    │   ├── ecs-cpu-high (> 80% for 10 min) → SNS → Email
    │   ├── ecs-memory-high (> 85%) → SNS → Email
    │   ├── alb-5xx-errors (> 10/min) → SNS → Email
    │   ├── alb-latency-high (p99 > 2s) → SNS → Email
    │   └── [composite] CPU AND latency → SNS → Email
    │
    ├── Dashboard: handson-overview
    │   ├── ECS CPU & Memory chart
    │   ├── ALB requests & latency chart
    │   ├── HTTP status codes chart
    │   └── Alarm status widget
    │
    └── Log Insights (saved queries)
        ├── error-rate-last-hour
        └── slow-requests
```

## Alarm Evaluation

```
period = 300s (5-minute average)
evaluation_periods = 2
→ Alarm fires after threshold exceeded for 10 consecutive minutes
→ Reduces false positives from brief spikes

treat_missing_data = "notBreaching"
→ If no data (service down), don't alarm on missing metrics
→ Use "breaching" for task count alarms (missing = problem)
```
