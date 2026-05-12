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

## Code

### `code/log_shipper.py` — Ship application logs to CloudWatch Logs

```bash
pip install boto3

# Send a single log message
python code/log_shipper.py \
  --log-group /app/myservice \
  --message "Application started successfully"

# Tail a log file and ship new lines to CloudWatch
python code/log_shipper.py \
  --log-group /app/myservice \
  --file /var/log/myapp.log

# Use a specific log stream name
python code/log_shipper.py \
  --log-group /app/myservice \
  --message "test" \
  --stream my-instance-id
```

What it does:
- Creates the log group and log stream if they don't exist
- Handles CloudWatch sequence tokens correctly (required for ordered log delivery)
- Tails a file and ships new lines in real-time when `--file` is used
- Prints the CloudWatch Logs console URL for the stream
