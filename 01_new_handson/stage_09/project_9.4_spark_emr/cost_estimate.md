# Cost Estimate — Project 9.4 Spark Processing on EMR

## EMR Serverless (Recommended)
| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| vCPU-hours (2 vCPU × 10 min/run × 10 runs) | 3.3 vCPU-hours | ~$0.17 |
| Memory-hours (4 GB × 10 min × 10 runs) | 6.7 GB-hours | ~$0.02 |
| **Total** | | **~$0.19/month** |

## EMR on EC2 (if used)
| Resource | Monthly Cost |
|----------|-------------|
| m5.xlarge master (1 node) | ~$140 |
| m5.xlarge workers (2 nodes) | ~$280 |
| **Total** | **~$420/month** |

## Notes
- EMR Serverless is dramatically cheaper for learning — no idle cluster cost
- EMR on EC2: only use if you need persistent cluster or custom config
- Spot instances reduce EMR on EC2 cost by 60-90%
