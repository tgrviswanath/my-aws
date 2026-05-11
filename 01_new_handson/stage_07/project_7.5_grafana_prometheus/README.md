# Project 7.5 — Grafana + Prometheus Monitoring

## What This Does
Deploys the modern observability stack: Prometheus scrapes metrics from ECS/EKS, Grafana visualizes them with rich dashboards. This is the industry-standard stack used by most engineering teams.

## Stack
| Tool | Role |
|------|------|
| Prometheus | Time-series metrics database + scraper |
| Grafana | Visualization and alerting |
| AWS Managed Grafana | Fully managed Grafana (no server to run) |
| CloudWatch data source | Connect Grafana to CloudWatch metrics |
| Prometheus data source | Connect Grafana to Prometheus |

## Architecture
```
ECS Tasks (expose /metrics endpoint)
  → Prometheus scrapes every 15s
    → Stores time-series data
      → Grafana queries Prometheus
        → Dashboards + Alerts
```

## Dashboards Built
- ECS service overview (CPU, memory, task count)
- API performance (request rate, latency, error rate)
- Infrastructure overview (EC2, RDS, ALB)
- Business metrics (orders/min, revenue/hour)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output grafana_url
```

## Lessons Learned
- AWS Managed Grafana: no server to manage, integrates with IAM/SSO
- Prometheus remote_write: send metrics to AWS Managed Prometheus (AMP)
- PromQL: Prometheus query language — more powerful than CloudWatch metrics math
- Grafana alerts: route to PagerDuty, Slack, email — more flexible than CloudWatch alarms
- USE method: Utilization, Saturation, Errors — framework for infrastructure metrics
- RED method: Rate, Errors, Duration — framework for service metrics
