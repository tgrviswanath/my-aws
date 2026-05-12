# Architecture — Project 7.5 Grafana + Prometheus Monitoring

## Observability Stack

```
ECS Flask App
    │ /metrics endpoint (Prometheus format)
    │ Exposes: http_requests_total, http_request_duration_seconds
    ▼
Prometheus Sidecar (in ECS task)
    │ Scrapes /metrics every 15s
    │ remote_write with SigV4 auth
    ▼
AWS Managed Prometheus (AMP)
    │ Stores time-series data
    │ PromQL query API
    ▼
AWS Managed Grafana
    ├── Data source: Prometheus (AMP) → custom app metrics
    ├── Data source: CloudWatch → AWS service metrics
    └── Data source: X-Ray → distributed traces
          │
          ▼
    Dashboards + Alerts → SNS → Email/Slack
```

## RED Method Dashboards

```
Rate (requests per second):
  rate(http_requests_total[5m])

Errors (error rate %):
  rate(http_requests_total{status=~"5.."}[5m])
  / rate(http_requests_total[5m]) * 100

Duration (p99 latency):
  histogram_quantile(0.99,
    rate(http_request_duration_seconds_bucket[5m])
  )
```

## Grafana Alert Example

```
Alert: High Error Rate
Query: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
Condition: IS ABOVE 0.01 (1% error rate)
Evaluation: every 1m for 5m
Notification: SNS → email
```
