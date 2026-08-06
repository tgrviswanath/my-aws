# Cost Estimate — Project 0.3: Git Workflow

> **Total Estimated Cost: $0.00**  
> **AWS Free Tier Eligible: Yes (100%)**

---

## Service Cost Breakdown

| Service | Resource Used | Quantity | Unit Cost | Monthly Cost |
|---------|--------------|----------|-----------|--------------|
| GitHub | Public/Private repositories | Up to 500 MB | Free | $0.00 |
| GitHub | Actions CI/CD minutes | 2,000 min/month | Free | $0.00 |
| AWS CodeCommit | Repository (optional) | 1 repo | Free | $0.00 |
| AWS CodeCommit | Git requests (optional) | ~50 requests | Free | $0.00 |
| AWS IAM | Git credentials | 1 set | Free | $0.00 |
| **Total** | | | | **$0.00** |

---

## Free Tier Details

### GitHub Free Plan — Always Free
- **Public repositories:** Unlimited
- **Private repositories:** Unlimited (since 2019)
- **Collaborators:** Unlimited on public repos; up to 3 on private repos (free plan)
- **GitHub Actions:** 2,000 minutes/month free
- **Storage:** 500 MB per repository (soft limit)
- **GitHub Packages:** 500 MB storage, 1 GB transfer free
- Source: https://github.com/pricing

### AWS CodeCommit Free Tier
- **Free tier:** 5 active users per month
- **Storage:** 50 GB per month
- **Git requests:** 10,000 per month
- **Active user definition:** Any user who pushes to or pulls from a repository
- **After free tier:**
  - $1.00 per additional active user/month
  - $0.06 per GB/month storage (above 50 GB)
  - $0.001 per 1,000 Git requests (above 10,000)
- For 1 solo learner: **$0.00/month** (well within free tier)

### AWS IAM — Always Free
- Git credentials for CodeCommit are IAM-managed and free

---

## GitHub vs CodeCommit — Cost Comparison for Learning

| Scenario | GitHub Cost | CodeCommit Cost |
|----------|-------------|-----------------|
| Solo learner, 1 repo | $0 | $0 |
| Solo learner, 10 repos | $0 | $0 |
| 5-person team, private repos | $0 (free plan) | $0 (free tier) |
| 6-person team | $0 (free plan allows 3 collab on private; unlimited on public) | ~$1/month for 6th user |
| Open source project | $0 | $0 (but no discoverability) |

For stage_00 learning: **both are $0.**

---

## What Could Cost Money Later (Not in This Project)

| Future Scenario | Service | Potential Cost |
|----------------|---------|---------------|
| GitHub Teams plan | GitHub | $4/user/month |
| GitHub Enterprise | GitHub | $21/user/month |
| Large LFS storage | GitHub | $5/50 GB/month |
| Many CodeCommit users | CodeCommit | $1/user/month (above 5) |
| CodeCommit large storage | CodeCommit | $0.06/GB/month (above 50 GB) |

---

## Cleanup

### GitHub Cleanup (Optional)
No ongoing cost — free repositories have no monthly charge.

To delete the repository (if desired):
1. GitHub → repository → Settings → Danger Zone → Delete this repository

### CodeCommit Cleanup

```bash
# Delete CodeCommit repository (if created)
aws codecommit delete-repository --repository-name aws-learning-private

# Verify deletion
aws codecommit list-repositories
```

Or via console: CodeCommit → repository → Settings → Delete repository

**Cost of not cleaning up:** $0 (within free tier for solo learner)

---

## Monthly Running Cost Summary

```
GitHub repositories:        $0.00/month
GitHub Actions:             $0.00/month
AWS CodeCommit (1 user):    $0.00/month
AWS IAM credentials:        $0.00/month
Git software (local):       $0.00/month
─────────────────────────────────────────
Total:                      $0.00/month
Annual projection:          $0.00/year
```

**This is a zero-cost foundational project.**

---

*End of cost_estimate.md — Project 0.3*
