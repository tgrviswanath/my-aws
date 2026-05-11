# Cost Estimate — Project 7.2 Centralized Logging Platform

| Resource | Monthly Cost |
|----------|-------------|
| OpenSearch t3.small.search (1 node) | ~$25 |
| OpenSearch EBS 10 GB gp3 | ~$1 |
| Kinesis Firehose (< 1 GB) | ~$0.03 |
| S3 backup storage | ~$0.02 |
| **Total** | **~$26/month** |

## ⚠️ Destroy After Learning
OpenSearch has no free tier. Destroy when done:
```bash
terraform destroy
```
For learning, use CloudWatch Log Insights instead (much cheaper).
