# Cost Estimate — Project 5.3 Push Containers to ECR

| Resource | Monthly Cost |
|----------|-------------|
| ECR storage (first 500 MB free) | $0 |
| ECR data transfer (within region) | $0 |
| ECR image scanning | $0 (basic scanning free) |
| **Total** | **$0** |

## Notes
- ECR free tier: 500 MB/month storage — permanent
- A typical Docker image is 100–300 MB — well within free tier for learning
- Lifecycle policies prevent storage from growing unbounded
- Data transfer to ECS/EKS in the same region is free
