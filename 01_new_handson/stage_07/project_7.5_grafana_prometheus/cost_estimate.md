# Cost Estimate — Project 7.5 Grafana + Prometheus Monitoring

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| AWS Managed Prometheus | < 10M samples | $0 (free tier: 10M) |
| AWS Managed Grafana | 1 active editor | $9 |
| **Total** | | **~$9/month** |

## Notes
- AMP free tier: 10M active series + 10B samples ingested — generous for learning
- Managed Grafana: $9/month per active editor user
- Alternative: run Grafana + Prometheus locally in Docker (free) for learning
- Destroy after learning: `terraform destroy`
