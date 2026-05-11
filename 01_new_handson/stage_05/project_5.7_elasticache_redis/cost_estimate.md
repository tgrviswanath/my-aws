# Cost Estimate — Project 5.7 Redis Caching with ElastiCache

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| ElastiCache cache.t3.micro | 730 hrs | ~$12.40 |
| Data transfer (within VPC) | Minimal | $0 |
| Backup storage | < 1 GB | $0 |
| **Total** | | **~$12.40/month** |

## Notes
- cache.t3.micro is NOT free tier eligible — ElastiCache has no free tier
- Stop/delete the cluster when not using it
- For learning: use a local Redis container (from Project 5.2) instead of ElastiCache
- Production: use cache.r7g.large for better performance/cost ratio
- Multi-AZ (2 nodes): doubles the cost but provides automatic failover
