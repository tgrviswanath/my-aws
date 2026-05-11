# Cost Estimate — Project 4.2 API Authentication & Authorization

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Cognito User Pool | Up to 50,000 MAU | $0 (free tier) |
| Cognito auth flows | 1,000 logins | $0 (free tier) |
| Lambda (auth + protected) | 10K requests | $0 (free tier) |
| API Gateway HTTP API | 10K requests | $0.01 |
| **Total** | | **~$0.01/month** |

## Notes
- Cognito free tier: 50,000 Monthly Active Users — permanent
- After 50K MAU: $0.0055 per MAU
- JWT Authorizer validation is free — no Lambda invocation cost for auth
