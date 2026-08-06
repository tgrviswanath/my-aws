# Project 5.3 — Cost Estimate: Amazon ECR

## Free Tier

| Resource | Free Tier Allowance | Notes |
|----------|-------------------|-------|
| ECR Private storage | 500 MB/month | Per account across all private repos |
| ECR Data transfer IN | Free | Always free (pushing images) |
| ECR Data transfer OUT (internet) | 1 GB/month free | First 1 GB per month |

---

## Pricing Breakdown

### Storage

| Usage | Rate |
|-------|------|
| First 500 MB/month | Free (Free Tier) |
| Additional storage | $0.10 per GB/month |

For this project: pushing ~7 versions of a Python slim image (~150MB each), deduplicated layers mean actual storage is much less than 7×150MB. ECR stores unique layers only.

Estimated unique data: ~200MB (layers shared between versions)
Expected storage cost: **$0.00** (within 500MB free tier)

### Data Transfer

| Transfer | Rate |
|----------|------|
| IN (pushing to ECR) | Free |
| OUT to EC2 in same region | Free |
| OUT to EC2 in different region | $0.01/GB |
| OUT to internet | $0.09/GB first 10TB |

### Image Scanning

| Tier | Cost |
|------|------|
| ECR Basic Scanning | Free (included) |
| Amazon Inspector Enhanced Scanning | $0.09 per image push |

For this project with ~7 pushes using Enhanced Scanning: ~$0.63 one-time.
For Basic Scanning: **$0.00**

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| 7 image versions, Basic Scanning, same-region pulls | **$0.00** |
| 7 image versions, Enhanced Scanning | **~$0.63 one-time** |
| 50 image versions (~1GB unique data) | **~$0.05/month** after free tier |
| CI/CD: 100 pushes/month with Enhanced Scanning | **~$9/month** scanning only |

---

## Cleanup

```bash
# Delete all images and repository
aws ecr delete-repository \
  --repository-name my-app \
  --region us-east-1 \
  --force

# Verify deletion
aws ecr describe-repositories --repository-names my-app --region us-east-1 2>&1 | \
  grep -i "RepositoryNotFoundException" && echo "Deleted successfully"
```

After deletion: **$0.00/month** ongoing cost.

---

## Cost Tips

- Lifecycle policies are your best cost control for ECR — without them, old image layers accumulate
- ECR stores layers, not full images — 10 versions of similar images share base layers
- Enhanced scanning is worth enabling for production workloads despite the cost ($0.09/push) — it catches language-level vulnerabilities that Basic scanning misses
- Data transfer from ECR to ECS in the same region is always free — you won't pay for ECS pulling images from ECR in same region
- Public ECR repositories have a separate generous free tier: 500GB/month free egress to internet when authenticated, unlimited egress to AWS services
