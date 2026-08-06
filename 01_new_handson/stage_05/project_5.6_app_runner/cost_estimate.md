# Project 5.6 — Cost Estimate: AWS App Runner

## Free Tier

| Resource | Free Tier |
|----------|-----------|
| App Runner compute (active) | **No free tier** |
| App Runner compute (paused) | **$0** when scaled to 0 or paused |
| CloudWatch logs | 5 GB/month free |

---

## Pricing Breakdown (us-east-1)

### App Runner Compute

| Metric | Rate |
|--------|------|
| vCPU (active processing) | $0.064 per vCPU-hour |
| Memory (provisioned) | $0.007 per GB-hour |

**Important:** App Runner charges for provisioned instances, not just active request processing. Even an idle instance with `minSize: 1` incurs memory charges.

**Configuration for this project:** 0.25 vCPU, 0.5 GB, min 1 instance

| Resource | Calculation | Monthly Cost |
|----------|------------|-------------|
| vCPU (provisioned, 1 instance) | 0.25 × $0.064 × 24h × 30 days | $11.52 |
| Memory (provisioned, 1 instance) | 0.5 × $0.007 × 24h × 30 days | $2.52 |
| **Minimum monthly (1 instance, 24/7)** | | **~$14.04/month** |

### Comparison: App Runner vs ECS Fargate

| Service | vCPU rate | Memory rate | 0.25vCPU 0.5GB 24/7 | Includes |
|---------|-----------|-------------|---------------------|---------|
| App Runner | $0.064/hr | $0.007/GB-hr | ~$14/month | HTTPS, ALB, scaling |
| ECS Fargate | $0.04048/hr | $0.004445/GB-hr | ~$12/month | Compute only |
| ECS + ALB | — | — | ~$28/month | Add $16/month for ALB |

App Runner is slightly more expensive per compute unit but includes HTTPS and load balancing at no extra charge.

### Paused Service

If App Runner service is paused (0 active instances):
- Memory and CPU charges stop
- You pay only for the provisioned configuration (a small fixed cost)
- Approximate cost when fully idle (0 instances): **~$0.007/GB-hour × 0 GB = $0**

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| 1 instance min, 0.25 vCPU / 0.5GB, 24/7 running | **~$14/month** |
| Dev use (8h/day, 5 days/week) | **~$4/month** |
| Paused / scaled to 0 | **~$0/month** |
| Peak: 10 instances for 1 hour | 10 × (0.25 × $0.064 + 0.5 × $0.007) = ~$0.20 one-time |

---

## Cleanup

```bash
# Delete service immediately stops all billing
aws apprunner delete-service \
  --service-arn $(aws apprunner list-services \
    --query "ServiceSummaryList[?ServiceName=='flask-app-runner'].ServiceArn" \
    --output text --region us-east-1) \
  --region us-east-1
```

After deletion: **$0.00/month**

---

## Cost Tips

- Set `minSize: 0` instead of `minSize: 1` if you can tolerate cold start latency on the first request — this eliminates the idle instance charge
- For a development service used only during work hours, pause it at night using a scheduled EventBridge rule calling `aws apprunner pause-service`
- App Runner is most cost-effective for services that receive consistent traffic — the included load balancer and HTTPS make it competitive with ECS+ALB for simple apps
- Use `minSize: 1` for production (avoids cold starts); `minSize: 0` for dev/staging to save money
