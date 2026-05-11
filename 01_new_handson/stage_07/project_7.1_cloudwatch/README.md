# Project 7.1 — CloudWatch Monitoring System

## What This Does
Sets up a comprehensive CloudWatch monitoring system: custom metrics, alarms, dashboards, and log insights queries for the ECS application from Stage 5.

## Components Built
| Component | Purpose |
|-----------|---------|
| Custom metrics | App-level metrics (request count, latency, errors) |
| Alarms | Alert when thresholds are breached |
| Dashboard | Single-pane view of system health |
| Log Insights | Query logs with SQL-like syntax |
| Composite alarms | Combine multiple alarms into one |
| Anomaly detection | ML-based baseline + alert on deviation |

## Alarms Created
| Alarm | Threshold | Action |
|-------|-----------|--------|
| High CPU | > 80% for 5 min | SNS → email |
| High memory | > 85% for 5 min | SNS → email |
| 5xx errors | > 10/min | SNS → email |
| ALB latency | > 2s p99 | SNS → email |
| ECS task count | < desired | SNS → email |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"
terraform output dashboard_url
```

## Lessons Learned
- CloudWatch metrics have 1-minute resolution by default — use high-resolution (1s) for critical metrics
- Alarm states: OK, ALARM, INSUFFICIENT_DATA — always handle INSUFFICIENT_DATA
- Log Insights queries are powerful but cost per GB scanned — use time ranges
- Composite alarms reduce alert noise — only page when multiple signals fire together
- Metric math: combine metrics (e.g. error rate = errors / total requests × 100)
