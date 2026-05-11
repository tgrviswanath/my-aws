# Cost Estimate — Project 3.1 Terraform Basics

| Resource | Monthly Cost |
|----------|-------------|
| S3 buckets (< 5 GB) | $0 (free tier) |
| EC2 t3.micro (data sources demo) | $0 (free tier) |
| SSM Parameter (SecureString) | $0.05 |
| **Total** | **~$0.05/month** |

## Notes
- Always run `terraform destroy` after each exercise to avoid accumulating costs
- The EC2 instance in `04_data_sources` should be destroyed immediately after the demo
- S3 buckets are essentially free at learning volumes
