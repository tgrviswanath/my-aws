# Project 5.1 — Cost Estimate: Single Docker App & ECR

## Free Tier

AWS ECR offers a free tier for new accounts:

| Resource | Free Tier Allowance | Notes |
|----------|-------------------|-------|
| ECR Storage | 500 MB/month | Per account, not per repo |
| ECR Data Transfer (in) | Free | Pushing images |
| ECR Data Transfer (out) | 1 GB/month free | Then standard rates |

A typical Python Flask slim image is ~120-150MB. You get ~3-4 pushes of unique layer data before hitting the 500MB free tier.

---

## Pricing Breakdown

### ECR Storage

| Usage | Rate | Monthly Cost |
|-------|------|-------------|
| First 500 MB | $0.00 | Free Tier |
| Additional storage | $0.10/GB/month | ~$0.01-0.02 for a 150MB image beyond free tier |

### ECR Data Transfer

| Transfer Type | Rate |
|--------------|------|
| Data IN (push) | Free |
| Data OUT to EC2 (same region) | Free |
| Data OUT to internet | $0.09/GB (first 10 TB) |

### Estimated Monthly Cost for This Project

| Component | Estimated Cost |
|-----------|---------------|
| ECR repo (1 image, ~150MB) | $0.00 (within free tier) |
| Image push (one-time) | $0.00 |
| Pull from same region | $0.00 |
| Total | **$0.00** (within free tier) |

If you push many versions and exceed 500MB:
- 10 versions × 150MB = 1.5GB → $0.10 extra/month

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| 1-2 image versions stored | **$0.00** |
| 5 image versions (~750MB) | **~$0.03/month** |
| CI/CD with 20+ images per month | **~$0.15/month** |

ECR is effectively free at learning/development scale.

---

## Cleanup

To avoid any charges after this project:

```bash
# Delete the ECR repository and all images
aws ecr delete-repository \
  --repository-name flask-app \
  --region us-east-1 \
  --force

# Remove local Docker images
docker rmi flask-app:1.0.0 flask-app:latest 2>/dev/null || true
docker image prune -f
```

After deletion: **$0.00/month** ongoing cost.

---

## Cost Tips

- Lifecycle policies prevent image accumulation — set them up (covered in Step 7 of GUIDE.md)
- ECR data transfer out to the internet costs $0.09/GB — if you pull images frequently from outside AWS, this adds up
- Pulling from within the same AWS region (e.g., ECS in same region) is free
- Use `IMMUTABLE` tags to avoid accidentally storing duplicate data under the same tag name
