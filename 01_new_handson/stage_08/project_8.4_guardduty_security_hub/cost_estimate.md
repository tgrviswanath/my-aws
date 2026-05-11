# Cost Estimate — Project 8.4 GuardDuty + Security Hub

| Resource | Monthly Cost |
|----------|-------------|
| GuardDuty (first 30 days free trial) | $0 (trial) |
| GuardDuty after trial (~1M events) | ~$4 |
| Security Hub | $0.0010 per finding check × ~1000 | ~$1 |
| EventBridge rules | $0 (free tier) |
| SNS notifications | $0 (free tier) |
| **Total (after trial)** | **~$5/month** |

## Notes
- GuardDuty: 30-day free trial — enable it, learn it, then decide
- Security Hub: $0.0010 per security check per resource per month
- Both are worth keeping enabled in production — cheap insurance
- Disable GuardDuty if not needed to avoid ongoing charges
