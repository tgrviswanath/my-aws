# Project 5.5 — Cost Estimate: Blue-Green Deployment

## Free Tier

| Resource | Free Tier |
|----------|-----------|
| CodeDeploy (ECS deployments) | Free |
| ECS (control plane) | Free |
| CloudWatch alarms | 10 alarms free |
| S3 (appspec storage) | 5GB free |

---

## Pricing Breakdown

### CodeDeploy

ECS blue-green deployments via CodeDeploy are **free**. You only pay for the underlying infrastructure.

| Resource | Rate |
|----------|------|
| CodeDeploy for ECS | $0.00 |

### Fargate Compute During Deployment

During a blue-green deployment, both blue (old) and green (new) task sets run simultaneously:

**Base cost (2 blue tasks running):**
- 2 × (0.25 vCPU × $0.04048 + 0.5GB × $0.004445) = $0.025/hour

**During deployment (4 tasks: 2 blue + 2 green):**
- 4 × (0.25 vCPU × $0.04048 + 0.5GB × $0.004445) = $0.049/hour
- Deployment typically takes 5-15 minutes
- Extra cost per deployment: ~$0.004-0.012 (less than 1 cent)

### ALB (from project 5.4)

| Cost | Amount |
|------|--------|
| Hourly | $0.008/hour |
| Monthly | ~$5.76 base |
| LCU (traffic-based) | Variable, typically $5-15/month for low traffic |
| **ALB total** | **~$16-20/month** |

### S3 (appspec.json)

| Usage | Cost |
|-------|------|
| Storage (tiny file) | < $0.01/month |
| PUT request | < $0.01 |

### CloudWatch Alarm

| Usage | Cost |
|-------|------|
| 1 alarm (first 10 free) | $0.00 |

---

## Total

| Component | Monthly Cost |
|-----------|-------------|
| Fargate (2 tasks, 24/7, post-deployment) | ~$17.85 |
| ALB (minimum) | ~$16.20 |
| CodeDeploy | $0.00 |
| CloudWatch alarm | $0.00 |
| S3 appspec | < $0.01 |
| Extra Fargate during deployments (10 deploys/month × 10min) | ~$0.08 |
| **Total** | **~$34/month** |

---

## Cleanup

```bash
# Scale ECS service to 0 (immediate billing stop)
aws ecs update-service \
  --cluster my-fargate-cluster \
  --service my-fargate-service \
  --desired-count 0 \
  --region us-east-1

# Delete CodeDeploy resources (no cost, but clean up anyway)
aws deploy delete-deployment-group \
  --application-name my-fargate-app \
  --deployment-group-name my-fargate-dg \
  --region us-east-1

aws deploy delete-application \
  --application-name my-fargate-app \
  --region us-east-1

# Delete CloudWatch alarm
aws cloudwatch delete-alarms \
  --alarm-names fargate-app-5xx-alarm \
  --region us-east-1

# Delete S3 bucket
aws s3 rb s3://$(aws sts get-caller-identity --query Account --output text)-codedeploy-artifacts --force
```

After cleanup: **$0.00/month**

---

## Cost Tips

- Blue-green deployments briefly double your Fargate costs — but only for 5-15 minutes per deploy
- Terminate blue tasks quickly (`terminationWaitTimeInMinutes: 5`) to minimize overlap cost
- CodeDeploy for ECS is free — this is a significant advantage over third-party deployment tools
- The ALB is the dominant fixed cost; share it across multiple services using path-based routing if running multiple projects
- Use `FARGATE_SPOT` for the green (new) tasks during deployment to reduce cost by up to 70% during the brief overlap
