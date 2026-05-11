# Cost Estimate — Project 10.2 Disaster Recovery Architecture

| Resource | Monthly Cost |
|----------|-------------|
| RDS primary (db.t3.micro) | $0 (free tier) |
| RDS read replica in DR region | ~$13 |
| S3 cross-region replication | ~$0.02 per GB replicated |
| ECS in DR region (1 task, standby) | ~$4 |
| **Total** | **~$17/month** |

## Notes
- DR always costs money — you're paying for standby capacity
- Warm standby is a good balance of cost vs RTO
- For learning: deploy briefly, test failover, then destroy DR resources
- Production: keep DR running permanently — the cost of downtime exceeds DR cost
