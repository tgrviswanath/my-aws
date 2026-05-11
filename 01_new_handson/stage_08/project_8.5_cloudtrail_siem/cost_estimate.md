# Cost Estimate — Project 8.5 CloudTrail + SIEM Integration

| Resource | Monthly Cost |
|----------|-------------|
| CloudTrail (first trail, management events) | $0 |
| CloudTrail Insights | ~$0.35 (per 100K events analyzed) |
| S3 storage (logs, < 1 GB) | ~$0.02 |
| S3 → Glacier after 90 days | ~$0.004/GB |
| CloudWatch Logs (90-day retention) | ~$0.50 |
| EventBridge rules | $0 (free tier) |
| SNS notifications | $0 (free tier) |
| **Total** | **~$1/month** |

## Notes
- First CloudTrail trail management events are FREE — always enable it
- Data events (S3 object access, Lambda) cost $0.10/100K — enable selectively
- CloudTrail Insights: optional but useful for detecting unusual activity
- Keep CloudTrail running permanently — it's your security audit trail
