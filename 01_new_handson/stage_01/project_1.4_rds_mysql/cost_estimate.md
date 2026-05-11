# Cost Estimate — Project 1.4 RDS MySQL Deployment

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| RDS db.t3.micro | 750 hrs/month | $0 (free tier) |
| RDS storage 20 GB gp2 | 20 GB | $0 (free tier: 20 GB) |
| RDS automated backups | 20 GB | $0 (free tier: equal to DB size) |
| Data transfer | Minimal | $0 |
| **Total** | | **$0** |

## Notes
- db.t3.micro is free tier eligible for 750 hours/month
- **Stop the RDS instance when not using it** — free tier hours are consumed even when idle
- Multi-AZ doubles the cost — skip it for learning (use it in production)
- After free tier expires: db.t3.micro ≈ $13/month
