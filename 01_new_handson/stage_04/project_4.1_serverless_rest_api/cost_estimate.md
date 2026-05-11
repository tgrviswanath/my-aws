# Cost Estimate — Project 4.1 Serverless REST API

## Assumptions: 100,000 requests/month

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Lambda invocations | 100K requests | $0 (free tier: 1M) |
| Lambda compute | 100K × 100ms × 128MB | $0 (free tier: 400K GB-s) |
| API Gateway HTTP API | 100K requests | $0.10 |
| DynamoDB reads | 100K | $0 (free tier: 25 RCU) |
| DynamoDB writes | 10K | $0 (free tier: 25 WCU) |
| DynamoDB storage | < 1 GB | $0 (free tier: 25 GB) |
| CloudWatch Logs | < 1 GB | $0 (free tier: 5 GB) |
| **Total** | | **~$0.10/month** |

## Notes
- Serverless is essentially free at learning/small-scale volumes
- Lambda free tier: 1M requests + 400K GB-seconds per month — permanent (not just 12 months)
- DynamoDB free tier: 25 GB + 25 WCU + 25 RCU — permanent
- This API could handle millions of requests before costing more than $5/month
