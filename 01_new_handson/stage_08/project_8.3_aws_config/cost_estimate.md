# Cost Estimate — Project 8.3 AWS Config Compliance Automation

| Resource | Monthly Cost |
|----------|-------------|
| Config rules (5 rules) | $2.50 ($0.001 per evaluation × ~500 evaluations each) |
| Config configuration items | ~$0.50 (first 100K free) |
| S3 storage (config snapshots) | ~$0.10 |
| EventBridge rules | $0 (first 1M events free) |
| SNS notifications | $0 (free tier) |
| **Total** | **~$3/month** |

## Notes
- AWS Config free tier: 100K configuration item recordings/month
- Config rules: $0.001 per evaluation — very cheap
- Keep Config running permanently — it's your compliance audit trail
