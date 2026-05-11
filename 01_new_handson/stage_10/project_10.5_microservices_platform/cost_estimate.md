# Cost Estimate — Project 10.5 Production-grade Microservices Platform

## Full Platform Monthly Cost

| Component | Service | Monthly Cost |
|-----------|---------|-------------|
| Compute | ECS Fargate (4 tasks) | ~$50 |
| Compute | EKS cluster + nodes | ~$148 |
| Database | RDS MySQL (2 instances) | ~$26 |
| Cache | ElastiCache Redis | ~$12 |
| Networking | NAT Gateway | ~$32 |
| Networking | ALB (2) | ~$32 |
| API | API Gateway | ~$3 |
| Streaming | Kinesis (1 shard) | ~$11 |
| Data | Glue ETL (daily) | ~$3 |
| Data | Redshift Serverless | ~$86 |
| Security | WAF | ~$14 |
| Security | GuardDuty | ~$5 |
| Observability | CloudWatch | ~$10 |
| Observability | Grafana (managed) | ~$9 |
| Storage | S3 (all buckets) | ~$5 |
| **Total** | | **~$446/month** |

## Learning Strategy
- Never run the full platform simultaneously during learning
- Build and test each component individually
- Destroy after each session
- Estimated learning cost: $50-100 total if you destroy resources promptly

## Production Reality
- This platform at real scale would cost $500-2000/month
- Savings Plans + Reserved Instances reduce compute by 30-60%
- Spot instances for non-critical workloads: 60-90% savings
- Right-sizing after 1 month of data: 20-40% savings
