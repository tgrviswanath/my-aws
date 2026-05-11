# Project 7.2 — Centralized Logging Platform

## What This Does
Aggregates logs from all ECS containers into a centralized platform using CloudWatch Logs → OpenSearch (Elasticsearch) + Kibana for search and visualization.

## Architecture
```
ECS Tasks → CloudWatch Logs
              → Subscription Filter
                → Kinesis Data Firehose
                  → OpenSearch (Elasticsearch)
                    → Kibana dashboards
```

## Components
| Component | Role |
|-----------|------|
| CloudWatch Logs | Collect container logs |
| Subscription Filter | Stream logs to Firehose |
| Kinesis Firehose | Buffer and deliver to OpenSearch |
| OpenSearch | Index and search logs |
| Kibana | Visualize and query logs |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"
terraform output kibana_url
```

## Lessons Learned
- OpenSearch is the AWS fork of Elasticsearch — same API, AWS-managed
- Firehose buffers logs (5 MB or 60s) before delivering — not real-time
- For real-time: use CloudWatch Logs → Lambda → OpenSearch directly
- Index lifecycle management: auto-delete old indices to control storage costs
- Use index patterns in Kibana: `ecs-logs-*` matches all daily indices
- Fine-grained access control: restrict Kibana access by IAM role or Cognito
