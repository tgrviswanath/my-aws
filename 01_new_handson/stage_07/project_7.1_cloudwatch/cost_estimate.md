# Cost Estimate — Project 7.1 CloudWatch Monitoring System

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| CloudWatch alarms (5) | 5 alarms | $0.50 |
| Composite alarm (1) | 1 alarm | $0.50 |
| CloudWatch dashboard (1) | 1 dashboard | $3.00 |
| Log Insights queries | ~100 queries | ~$0.05 |
| SNS notifications | ~100 emails | $0 (free tier) |
| **Total** | | **~$4.05/month** |

## Notes
- First 10 alarms are $0.10 each — very cheap
- Dashboard: $3/month per dashboard — worth it for visibility
- Log Insights: $0.005 per GB scanned — use time ranges to limit cost
