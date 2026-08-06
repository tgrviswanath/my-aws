# Project 5.4 — Cost Estimate: ECS Fargate

## Free Tier

ECS itself has no charge — you pay for the underlying Fargate compute and other AWS services used.

| Resource | Free Tier |
|----------|-----------|
| ECS (control plane) | Free |
| Fargate compute | **No free tier** |
| ALB | **No free tier** ($16.20/month minimum) |
| CloudWatch logs | 5 GB ingestion/month free |

---

## Pricing Breakdown

### Fargate Compute (us-east-1 pricing)

| Resource | Rate |
|----------|------|
| vCPU | $0.04048 per vCPU-hour |
| Memory | $0.004445 per GB-hour |

Task configuration: 0.25 vCPU, 0.5 GB memory, desired count 2

**Cost per task per hour:**
- vCPU: 0.25 × $0.04048 = $0.01012
- Memory: 0.5 × $0.004445 = $0.002223
- Per task: $0.012343/hour

**Cost for 2 tasks (desired count = 2):**
- Per hour: 2 × $0.012343 = $0.024686
- Per day: $0.59
- Per month (24/7): ~$17.85

### Application Load Balancer

| Cost Element | Rate |
|-------------|------|
| ALB hourly | $0.008/hour = $5.76/month |
| LCU (Load Balancer Capacity Units) | $0.008 per LCU-hour |
| Minimum monthly (low traffic) | ~$16.20/month |

### ECR Storage (from project 5.1)

~$0.00 (within free tier for small images)

### CloudWatch Logs

| Usage | Rate |
|-------|------|
| Log ingestion (first 5GB) | Free |
| Additional ingestion | $0.50/GB |
| Log storage (first 5GB) | Free |

---

## Total

| Component | Monthly Cost |
|-----------|-------------|
| Fargate (2 tasks, 0.25 vCPU / 0.5GB, 24/7) | ~$17.85 |
| ALB (minimum) | ~$16.20 |
| CloudWatch Logs (low volume) | $0.00 |
| ECR storage | $0.00 |
| **Total** | **~$34/month** |

For a development/learning environment running only during business hours (8h/day, 5 days/week):
- Fargate: ~$5.10/month
- ALB: ~$16.20/month (fixed cost regardless of hours)
- **Total dev cost: ~$21/month**

---

## Cleanup

Run cleanup immediately after learning to avoid ongoing charges:

```bash
# Scale down to 0 first (stops Fargate billing instantly)
aws ecs update-service \
  --cluster my-fargate-cluster \
  --service my-fargate-service \
  --desired-count 0 \
  --region us-east-1

# Then delete all resources (see GUIDE.md Step 10)
```

After cleanup: **$0.00/month**

---

## Cost Tips

- ALB is the biggest fixed cost — if building multiple learning projects, share one ALB using path-based routing rules
- Fargate Spot can reduce compute costs by up to 70% (use `FARGATE_SPOT` capacity provider) — trade-off: tasks can be interrupted
- For dev environments, scale down to 0 at night using EventBridge rules targeting `ecs:UpdateService`
- Consider using a single smaller t3.micro EC2 instance (free tier eligible) for learning instead of Fargate if cost is a concern
- CloudWatch Log retention: always set to 7-30 days, not `Never expire` — unbounded log accumulation can add surprising costs over time
