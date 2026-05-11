# Cost Estimate — Project 9.6 dbt Transformation Pipeline

| Resource | Monthly Cost |
|----------|-------------|
| dbt Core (open source) | $0 |
| Athena queries (dbt runs, ~1 GB scanned) | ~$0.005 |
| S3 staging (dbt results) | ~$0.01 |
| **Total** | **~$0.02/month** |

## Notes
- dbt Core is completely free and open source
- dbt Cloud (managed): $50/month per developer seat — skip for learning
- Athena costs are minimal since dbt models are typically small SQL queries
