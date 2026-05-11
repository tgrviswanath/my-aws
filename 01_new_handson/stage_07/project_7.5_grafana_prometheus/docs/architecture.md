# Architecture — Project 7.5 Grafana + Prometheus Monitoring

## Observability Stack

```
ECS Flask App
  │ /metrics endpoint (Prometheus format)
  ▼
Prometheus Sidecar (in ECS task)
  │ scrape every 15s
  │ remote_write (SigV4 auth)
  ▼
AWS Managed Prometheus (AMP)
  │ stores time-series data
  │ PromQL query API
  ▼
AWS Managed Grafana
  ├── Prometheus data source → custom app metrics
  ├── CloudWatch data source → AWS service metrics
  └── X-Ray data source → distributed traces
        │
        ▼
  Dashboards + Alerts → SNS → Email/Slack/PagerDuty
```

## Key PromQL Queries

```promql
# Request rate (requests per second)
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
/ rate(http_requests_total[5m]) * 100

# P99 latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# CPU utilization (from CloudWatch)
avg(aws_ecs_cpuutilization_average{service_name="handson-flask-api"})
```

## RED Method (Service Metrics)

| Metric | PromQL | Alert Threshold |
|--------|--------|----------------|
| Rate | `rate(http_requests_total[5m])` | < 0 (service down) |
| Errors | `rate(http_requests_total{status=~"5.."}[5m])` | > 1% |
| Duration | `histogram_quantile(0.99, ...)` | > 2s |
