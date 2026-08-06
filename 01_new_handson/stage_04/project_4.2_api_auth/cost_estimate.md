# Cost Estimate — Project 4.2: API Authentication with Cognito + JWT

> **Total Estimated Cost: ~$0.00** | Free Tier Eligible: Yes

---

## Free Tier

| Service | Free Tier | Monthly Limit |
|---------|-----------|---------------|
| Amazon Cognito | 50,000 MAU free | Forever |
| AWS Lambda | 1M requests/month | Forever |
| Amazon API Gateway (HTTP) | 1M calls/month | 12 months |
| AWS IAM | Always free | Unlimited |
| Amazon CloudWatch Logs | 5 GB storage/month | 12 months |

---

## Cost Breakdown (Beyond Free Tier)

| Service | Resource | Unit Price | Lab Usage | Cost |
|---------|----------|-----------|-----------|------|
| Cognito | Users (MAU) | $0.0055/MAU after 50K | ~5 test users | $0.00 |
| Lambda | Invocations | $0.20/1M requests | <1,000 | $0.00 |
| API Gateway | HTTP API calls | $1.00/1M calls | <500 | $0.00 |
| **Total** | | | | **$0.00** |

---

## Cleanup

```bash
# Delete Cognito User Pool
aws cognito-idp delete-user-pool --user-pool-id <pool-id>

# Delete API Gateway
aws apigatewayv2 delete-api --api-id <api-id>

# Delete Lambda functions
aws lambda delete-function --function-name auth-handler
aws lambda delete-function --function-name protected-handler

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /aws/lambda/auth-handler
```
