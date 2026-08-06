# Cost Estimate — Project 4.3: URL Shortener (API Gateway + Lambda + DynamoDB TTL)

> **Total Estimated Cost: $0.00** | Free Tier Eligible: Yes (100%)

---

## Free Tier

| Service | Free Allowance | Duration |
|---------|---------------|---------|
| AWS Lambda | 1,000,000 requests/month | Always free |
| Lambda compute | 400,000 GB-seconds/month | Always free |
| Amazon API Gateway (HTTP) | 1,000,000 calls/month | 12 months |
| Amazon DynamoDB | 25 GB storage + 25 RCU/WCU | Always free |
| Amazon CloudWatch Logs | 5 GB ingestion/month | 12 months |

All services in this project fall within AWS Free Tier for typical lab usage.

---

## Cost Breakdown

| Service | Resource | Unit Price | Lab Usage | Monthly Cost |
|---------|----------|-----------|-----------|-------------|
| Lambda | Invocations | $0.20/1M | ~500 | $0.00 |
| Lambda | Compute (128MB, 200ms avg) | $0.0000166667/GB-s | ~100 GB-s | $0.00 |
| API Gateway | HTTP API calls | $1.00/1M | ~500 | $0.00 |
| DynamoDB | Storage | $0.25/GB | <1 MB | $0.00 |
| DynamoDB | Read/Write | $0.25/WCU | <10 WCU | $0.00 |
| **Total** | | | | **$0.00** |

---

## Total

**Estimated cost: $0.00** for lab-scale usage.

| Scenario | Cost |
|---------|------|
| Lab session (2-4 hours) | $0.00 |
| Monthly (idle) | $0.00 |
| Monthly (heavy traffic — millions of redirects) | $0.20–$1.00 |

---

## Cleanup

```bash
# Delete Lambda function
aws lambda delete-function --function-name url-shortener-handler

# Delete API Gateway
aws apigatewayv2 delete-api --api-id $(aws apigatewayv2 get-apis --query 'Items[?Name==`url-shortener`].ApiId' --output text)

# Delete DynamoDB table
aws dynamodb delete-table --table-name url-shortener-table

# Delete CloudWatch log group
aws logs delete-log-group --log-group-name /aws/lambda/url-shortener-handler

# Verify cleanup
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `url`)].FunctionName' --output table
aws dynamodb list-tables --output table
```
