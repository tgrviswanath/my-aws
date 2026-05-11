# Cost Estimate — Project 8.2 WAF Application Protection

| Resource | Monthly Cost |
|----------|-------------|
| WAF Web ACL | $5.00 |
| WAF rules (5 rules) | $5.00 ($1 each) |
| Managed rule groups (3) | $3.00 ($1 each) |
| WAF requests (1M) | $0.60 |
| CloudWatch Logs (WAF) | ~$0.50 |
| **Total** | **~$14/month** |

## Notes
- WAF is a fixed cost regardless of traffic — worth it for production
- Managed rule groups: $1/month each — AWS maintains them automatically
- For learning: deploy briefly, test, then destroy to save ~$14/month
