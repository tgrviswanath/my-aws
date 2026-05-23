# Stage 7 — Monitoring & Observability

> Master production-grade observability on AWS: CloudWatch, centralized logging, distributed tracing, log analytics, and the Grafana + Prometheus stack.

---

## Projects

| # | Project | Key Services | Difficulty |
|---|---------|-------------|-----------|
| 7.1 | CloudWatch Monitoring System | CloudWatch Alarms, Dashboards, Log Insights, SNS | ⭐⭐ |
| 7.2 | Centralized Logging Platform | CloudWatch Logs, Kinesis Firehose, OpenSearch, Kibana | ⭐⭐⭐ |
| 7.3 | AWS X-Ray Distributed Tracing | X-Ray, ECS sidecar, Service Map, Trace Analytics | ⭐⭐⭐ |
| 7.4 | Athena Log Analytics | Athena, Glue, CloudTrail, ALB Logs, S3 | ⭐⭐⭐ |
| 7.5 | Grafana + Prometheus Monitoring | AMP, AMG, Prometheus, PromQL, Grafana Dashboards | ⭐⭐⭐⭐ |

---

## Folder Structure

```
stage_07/
├── project_7.1_cloudwatch/
│   ├── code/cloudwatch_setup.py     # Create alarms, dashboards, log groups
│   ├── docs/architecture.md
│   ├── terraform/main.tf
│   ├── cost_estimate.md
│   ├── README.md
│   ├── steps.md
│   └── verify.md                   ✅ Verification & validation
├── project_7.2_centralized_logging/
│   ├── code/log_shipper.py          # Ship logs to CloudWatch
│   ├── docs/architecture.md
│   ├── terraform/main.tf
│   ├── cost_estimate.md
│   ├── README.md
│   ├── steps.md
│   └── verify.md                   ✅ Verification & validation
├── project_7.3_xray_tracing/
│   ├── src/app_with_tracing.py      # Flask app with X-Ray SDK
│   ├── docs/architecture.md
│   ├── terraform/main.tf
│   ├── cost_estimate.md
│   ├── README.md
│   ├── steps.md
│   └── verify.md                   ✅ Verification & validation
├── project_7.4_athena_log_analytics/
│   ├── queries/cloudtrail_queries.sql
│   ├── queries/alb_queries.sql
│   ├── docs/architecture.md
│   ├── terraform/main.tf
│   ├── cost_estimate.md
│   ├── README.md
│   ├── steps.md
│   └── verify.md                   ✅ Verification & validation
└── project_7.5_grafana_prometheus/
    ├── code/metrics_exporter.py     # Flask app with /metrics endpoint
    ├── docs/architecture.md
    ├── terraform/main.tf
    ├── cost_estimate.md
    ├── README.md
    ├── steps.md
    └── verify.md                   ✅ Verification & validation
```

---

## Quick Start

```bash
# Deploy any project
cd project_7.1_cloudwatch/terraform
terraform init && terraform apply

# Run verification after deploy
cat verify.md   # follow the checklist

# Run code helpers
pip install boto3
python code/cloudwatch_setup.py --ec2-id i-0abc123 --sns-arn arn:aws:sns:...
```

---

## Observability Concepts Covered

| Concept | Project | Key Takeaway |
|---------|---------|-------------|
| Metrics + Alarms | 7.1 | CloudWatch alarms: OK / ALARM / INSUFFICIENT_DATA |
| Composite alarms | 7.1 | Reduce noise — only alert when multiple signals fire |
| Log aggregation | 7.2 | CloudWatch → Firehose → OpenSearch pipeline |
| Distributed tracing | 7.3 | X-Ray segments, subsegments, annotations, service map |
| Log analytics at scale | 7.4 | Athena SQL on S3 logs — pay per query, use partitions |
| Prometheus + Grafana | 7.5 | RED method: Rate, Errors, Duration |

---

## 7. Verification & Validation

Every project in Stage 7 has a `verify.md` file covering:

- **AWS Console verification** — what to check and expected state for each resource
- **AWS CLI verification commands** — exact commands with expected outputs
- **Terraform state verification** — `terraform state list`, `terraform state show`, `terraform output`, `terraform plan`
- **Logs / monitoring checks** — confirm metrics are flowing, logs are indexed, traces appear
- **Expected successful outputs** — exact JSON / text output to compare against
- **Health check procedures** — end-to-end tests (alarm trigger, log flow, trace generation)
- **Verification checklist** — checkbox list to tick off before marking project complete

### Quick Verification Reference

| Project | Key CLI Check | Expected Result |
|---------|--------------|-----------------|
| 7.1 CloudWatch | `aws cloudwatch describe-alarms --alarm-name-prefix handson-` | All alarms listed, state OK |
| 7.2 Logging | `curl -u admin:pass https://ENDPOINT/ecs-logs-*/_count` | count > 0 |
| 7.3 X-Ray | `aws xray get-trace-summaries --start-time ... --end-time ...` | Traces listed with durations |
| 7.4 Athena | `aws athena get-query-execution --query-execution-id $ID` | State = SUCCEEDED |
| 7.5 Grafana | `curl $ALB_URL/metrics \| grep http_requests_total` | Counter values > 0 |

---

## Key Lessons

- **CloudWatch alarms**: always handle `INSUFFICIENT_DATA` state — it fires before metrics arrive
- **Firehose buffering**: 60s or 5MB before delivery — not real-time; use Lambda for real-time
- **X-Ray sampling**: 5% default — increase for low-traffic services, decrease for high-traffic
- **Athena cost**: $5/TB scanned — always use partition pruning (`WHERE year=... AND month=...`)
- **Grafana vs CloudWatch**: Grafana is more flexible for multi-source dashboards; CloudWatch is simpler for AWS-only
- **PromQL vs CloudWatch Metrics Math**: PromQL is more powerful for complex queries (histograms, rates)

---

## Certification Alignment

| Cert | Relevant Projects |
|------|------------------|
| AWS SysOps Administrator Associate | 7.1, 7.2, 7.3 |
| AWS Solutions Architect Associate | 7.1, 7.4 |
| AWS DevOps Engineer Professional | 7.1, 7.2, 7.3, 7.5 |
