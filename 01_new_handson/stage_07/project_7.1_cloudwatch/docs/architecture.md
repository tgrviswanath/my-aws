# Architecture — Project 7.1 CloudWatch Monitoring System

## Monitoring Stack

```
ECS Tasks / ALB
    │
    │ Emit metrics automatically
    ▼
┌──────────────────────────────────────────────────────────────┐
│                    CloudWatch                                 │
│                                                               │
│  Metrics Namespaces:                                          │
│  ├── AWS/ECS          (CPU, Memory, TaskCount)               │
│  ├── AWS/ApplicationELB (RequestCount, Latency, 5xx)         │
│  └── Custom/App       (business metrics you publish)         │
│                                                               │
│  Alarms:                                                      │
│  ├── ecs-cpu-high     → SNS → Email                          │
│  ├── ecs-memory-high  → SNS → Email                          │
│  ├── alb-5xx-errors   → SNS → Email                          │
│  ├── alb-latency-high → SNS → Email                          │
│  └── [composite]      → SNS → Email (CPU AND latency)        │
│                                                               │
│  Dashboard: handson-overview                                  │
│  ├── ECS CPU & Memory chart                                   │
│  ├── ALB requests & latency chart                            │
│  ├── HTTP status codes chart                                  │
│  └── Alarm status widget                                      │
│                                                               │
│  Log Insights:                                                │
│  ├── error-rate-last-hour query                              │
│  └── slow-requests query                                     │
└──────────────────────────────────────────────────────────────┘
    │
    │ Alarm → SNS Topic → Email subscription
    ▼
📧 your@email.com
```

## Alarm Evaluation

```
Metric data points collected every 60s (period=60)
Alarm evaluates every evaluation_periods × period

Example: ecs-cpu-high
  period=300 (5 min average)
  evaluation_periods=2
  → Alarm fires after CPU > 80% for 10 consecutive minutes
  → Reduces false positives from brief spikes
```
