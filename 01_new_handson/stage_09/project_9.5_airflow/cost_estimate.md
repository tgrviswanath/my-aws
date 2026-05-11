# Cost Estimate — Project 9.5 Airflow Data Orchestration

## Local Docker (Learning)
| Resource | Cost |
|----------|------|
| Local Docker Compose | $0 |

## Amazon MWAA (Production)
| Resource | Monthly Cost |
|----------|-------------|
| MWAA environment (mw1.small) | ~$315 |
| MWAA worker (1 worker) | ~$0.49/hr = ~$355 |
| **Total MWAA** | **~$670/month** |

## ⚠️ MWAA is Very Expensive
- Use local Airflow (Docker) for all development and learning
- Only deploy MWAA for production team use
- Alternative: self-hosted Airflow on ECS (~$30/month)
