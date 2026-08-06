# Cost Estimate — Project 0.1: AWS Local Dev Environment Setup

> **Total Estimated Cost: $0.00**  
> **AWS Free Tier Eligible: Yes (100%)**

---

## Service Cost Breakdown

| Service | Resource Created | Quantity | Unit Cost | Monthly Cost |
|---------|-----------------|----------|-----------|--------------|
| AWS IAM | IAM User | 1 user | Free | $0.00 |
| AWS IAM | IAM Policy attachment | 1 | Free | $0.00 |
| AWS IAM | Access Key | 1 key | Free | $0.00 |
| AWS STS | `get-caller-identity` calls | ~5 calls | Free | $0.00 |
| AWS CLI | Software download | 1 install | Free | $0.00 |
| **Total** | | | | **$0.00** |

---

## Free Tier Details

### IAM — Always Free
- IAM users, groups, roles, and policies are **always free** with no limits
- Access keys are always free
- AWS does not charge for IAM API calls
- Free Tier: Unlimited (IAM has no cost tier — it is simply always free)

### AWS STS — Always Free
- `sts:GetCallerIdentity` is free
- All STS API calls are free regardless of volume
- Free Tier: Unlimited

### AWS CLI — Free Software
- The AWS CLI v2 is open-source and free to download/use
- No license fee
- Source: https://github.com/aws/aws-cli

### Python, Git, VS Code — Free Software
- Python: Free (PSF License)
- Git: Free (GPL)
- VS Code: Free (MIT License)

---

## What Could Cost Money (But Doesn't in This Project)

| If You Had Done This | Potential Cost |
|---------------------|---------------|
| Created an EC2 instance | $0.0116/hour (t2.micro, outside free tier) |
| Stored files in S3 | $0.023/GB/month (after 5 GB free tier) |
| Used AWS Secrets Manager | $0.40/secret/month |
| Created CloudTrail trail | $2.00/100k events (after first trail free) |

> This project deliberately avoids all billable resources. Only IAM and STS are used.

---

## Cleanup

No cleanup is required for zero cost — IAM resources have no ongoing charge.

However, for security best practices, clean up when done:

### Recommended Cleanup Actions
1. **Deactivate the access key** when not actively learning:
   - IAM Console → Users → `cli-learning-user` → Security credentials → Deactivate
   - Cost impact: $0 (deactivating doesn't change cost)

2. **Delete the access key** when you want full cleanup:
   - IAM Console → Users → `cli-learning-user` → Security credentials → Delete
   - Cost impact: $0

3. **Delete the IAM user** if completely done with the project:
   - IAM Console → Users → `cli-learning-user` → Delete
   - Cost impact: $0

4. **Remove local credentials**:
   ```powershell
   # Clear the credentials file
   Remove-Item $env:USERPROFILE\.aws\credentials
   ```

### Cleanup Cost Impact
All cleanup actions cost $0. The only reason to clean up is security hygiene, not cost.

---

## Monthly Running Cost Summary

```
IAM User:              $0.00/month
Access Key:            $0.00/month
STS API calls:         $0.00/month
─────────────────────────────────
Total:                 $0.00/month
Annual projection:     $0.00/year
```

**This is a zero-cost foundational project.**

---

*End of cost_estimate.md — Project 0.1*
