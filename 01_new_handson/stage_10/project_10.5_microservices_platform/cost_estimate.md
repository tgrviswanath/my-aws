# Cost Estimate — Project 10.5: Full Microservices Platform

## Platform Component Pricing

### ECS Fargate
| Resource | Price | Notes |
|----------|-------|-------|
| vCPU per hour | $0.04048 | Per vCPU allocated |
| Memory per GB per hour | $0.004445 | Per GB allocated |
| Fargate Spot vCPU | $0.01213 | 70% savings, interruptible |
| Fargate Spot GB/hr | $0.00133 | 70% savings |

### API Gateway
| Resource | Price | Notes |
|----------|-------|-------|
| REST API calls | $3.50/million | First 333M/month |
| REST API calls | $2.80/million | > 333M/month |
| Data transfer out | $0.09/GB | Standard AWS rates |

### SQS
| Resource | Price | Notes |
|----------|-------|-------|
| Standard queue | $0.40/million requests | First 1M/month free |
| FIFO queue | $0.50/million requests | First 1M/month free |

### ElastiCache Redis
| Instance | On-Demand | Notes |
|----------|----------|-------|
| cache.t3.micro | $0.017/hour | ~$12.41/month |
| cache.t3.small | $0.034/hour | ~$24.82/month |
| cache.r6g.large | $0.166/hour | ~$121.18/month |

### Application Load Balancer
| Resource | Price |
|----------|-------|
| Per ALB-hour | $0.008 |
| Per LCU-hour | $0.008 |

---

## Free Tier

- **SQS**: First 1 million requests/month free (per account)
- **ECS Fargate**: No free tier
- **ElastiCache t3.micro**: 750 hours/month free (12 months)
- **API Gateway**: First 1 million REST API calls/month free (12 months)

---

## Scenario Estimates

### Minimal Platform (Dev/Testing, 2 tasks per service)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| 3 services × 2 tasks × 0.5 vCPU × 730hr | 6 tasks | $88.65 |
| 3 services × 2 tasks × 1 GB × 730hr | 6 GB-tasks | $38.93 |
| 3 ALBs (minimal traffic) | 3 × $16.20 | $48.60 |
| ElastiCache t3.micro × 1 | 1 | $12.41 |
| SQS requests (100K) | 100K | $0.00 (free) |
| API Gateway (100K calls) | 100K | $0.00 (free) |
| RDS per service (db.t3.micro × 3) | 3 | $74.46 |
| CloudWatch Logs (5 GB) | 5 GB | $2.50 |
| **Total** | | **~$265/month** |

### Production Platform (4 tasks per service, auto-scaled)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| 3 services × 4 tasks avg × 1 vCPU × 730hr | 12 tasks | $354.61 |
| 3 services × 4 tasks × 2 GB × 730hr | 24 GB-tasks | $311.44 |
| 3 ALBs (moderate traffic, 10M requests) | 3 | $125 |
| ElastiCache t3.small × 1 (with replica) | 2 | $49.64 |
| SQS requests (10M) | 10M | $4.00 |
| API Gateway (10M REST calls) | 10M | $35.00 |
| RDS db.t3.small × 3 (Multi-AZ) | 3 | $224.58 |
| CloudWatch + Container Insights (20 GB) | 20 GB | $10.00 |
| NAT Gateway × 2 (private subnets) | 2 | $65.70 |
| **Total** | | **~$1,180/month** |

### High Traffic (Fargate Spot mix, 20 tasks per service)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| 50% On-Demand Fargate (base capacity) | 30 tasks × 1vCPU | $886.52 |
| 50% Fargate Spot (burst) | 30 tasks × 1vCPU | $265.96 |
| ALBs (high traffic, 100M requests) | 3 × $200 | $600 |
| ElastiCache r6g.large (HA) | 1 primary + 1 replica | $242.36 |
| API Gateway (100M calls) | 100M | $350 |
| RDS db.r6g.large × 3 (Multi-AZ) | 3 × $313 | $939 |
| **Total** | | **~$3,280/month** |

---

## Cost per Service Breakdown (Production)

| Service | Monthly Cost |
|---------|-------------|
| user-service (ECS + RDS) | ~$195 |
| order-service (ECS + RDS + Redis) | ~$244 |
| analytics-service (ECS + S3) | ~$160 |
| API Gateway (shared) | ~$35 |
| SQS (shared) | ~$4 |
| Networking (NAT, ALBs) | ~$190 |
| Monitoring (CloudWatch) | ~$10 |
| **Total** | **~$838/month** |

---

## Cost Optimization for Microservices

### 1. Use Fargate Spot for Non-Critical Services
```bash
# Analytics service: 100% Fargate Spot (can tolerate interruption)
# 70% savings
aws ecs update-service \
  --cluster myapp-microservices \
  --service analytics-service \
  --capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=1,base=0
```

### 2. Share Database for Lower Traffic Services
- Instead of 3 separate RDS instances: use 1 RDS with separate schemas
- Saves ~$150/month at db.t3.small tier

### 3. Reduce Task Sizes
```yaml
# Review actual memory usage — often over-allocated
# Analytics service with 256MB is often enough for light processing
cpu: 256  # 0.25 vCPU = $0.01012/hr
memory: 512  # 0.5 GB = $0.00222/hr
# vs 0.5 vCPU + 1 GB = $0.02468/hr
# Savings: ~60% per task
```

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Dev/Testing (minimal) | ~$265 | ~$3,180 |
| Production (moderate) | ~$1,180 | ~$14,160 |
| High Traffic | ~$3,280 | ~$39,360 |

**Comparison:** Running this on a single large EC2 instance would cost ~$100-200/month but lacks HA, autoscaling, and observability.

---

## Cleanup

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Scale down and delete ECS services (stops Fargate billing)
for SERVICE in user-service order-service analytics-service; do
  aws ecs update-service \
    --cluster myapp-microservices \
    --service $SERVICE \
    --desired-count 0 \
    --region $REGION
  
  aws ecs delete-service \
    --cluster myapp-microservices \
    --service $SERVICE \
    --force \
    --region $REGION
  
  echo "Deleted service: $SERVICE"
done

# 2. Delete ECS cluster
aws ecs delete-cluster \
  --cluster myapp-microservices \
  --region $REGION

# 3. Delete API Gateway
API_ID=$(aws apigateway get-rest-apis \
  --query 'items[?name==`myapp-api`].id' --output text)
aws apigateway delete-rest-api --rest-api-id $API_ID

# 4. Delete SQS queues
ORDER_QUEUE_URL=$(aws sqs get-queue-url --queue-name order-events \
  --query QueueUrl --output text)
DLQ_URL=$(aws sqs get-queue-url --queue-name order-events-dlq \
  --query QueueUrl --output text)
aws sqs delete-queue --queue-url $ORDER_QUEUE_URL
aws sqs delete-queue --queue-url $DLQ_URL

# 5. Delete ElastiCache (takes ~5 minutes)
aws elasticache delete-cache-cluster --cache-cluster-id myapp-redis

# 6. Delete CloudWatch log groups
for SERVICE in user-service order-service analytics-service; do
  aws logs delete-log-group --log-group-name "/ecs/myapp/${SERVICE}"
done

# 7. Delete ECR repositories
for SERVICE in user-service order-service analytics-service; do
  aws ecr delete-repository \
    --repository-name "myapp/${SERVICE}" \
    --force
done

echo "Microservices platform cleanup complete"
echo "Largest immediate savings: ECS Fargate tasks stop billing within 5 minutes of service deletion"
```

**Key cost note:** Fargate billing stops immediately when tasks stop. The cluster itself has no cost — only running tasks incur charges.
