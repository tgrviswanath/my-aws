# Cost Estimate — Project 1.2 Linux Web Server on EC2

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| EC2 t3.micro | 750 hrs/month | $0 (free tier) |
| EBS gp3 8 GB | 30 GB free tier | $0 |
| Data transfer out | < 1 GB | $0 (free tier: 100 GB) |
| Public IPv4 address | 1 address | $3.60 (750 hrs free for EC2 default) |
| **Total** | | **~$0–$3.60/month** |

## Notes
- t3.micro is free tier eligible for 750 hours/month (enough for 1 instance running 24/7)
- **Stop the instance when not using it** — free tier hours are shared across all t2/t3.micro instances
- AWS now charges $0.005/hr for public IPv4 addresses (even in free tier) — stop instance when done
- Terminate (not just stop) when completely finished to avoid EBS charges after free tier
