# Cost Estimate — Project 4.6 Step Functions Workflow

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Step Functions Standard | 1,000 executions × 6 transitions | $0.15 |
| Lambda (5 functions) | 1,000 × 5 invocations | $0 (free tier) |
| SNS notifications | 1,000 | $0 (free tier) |
| **Total** | | **~$0.15/month** |

## Notes
- Step Functions free tier: 4,000 state transitions/month
- 1,000 executions × 6 states = 6,000 transitions → ~$0.05 over free tier
- Use Express Workflows for high-volume short workflows — much cheaper
