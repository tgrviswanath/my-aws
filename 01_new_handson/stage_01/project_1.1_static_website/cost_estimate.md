# Cost Estimate — Project 1.1 Static Website Hosting

## Assumptions
- Small personal/portfolio site
- ~10,000 visitors/month
- ~50 MB total website size
- CloudFront PriceClass_100 (US/Canada/Europe)

## Monthly Cost Breakdown

| Service | Usage | Cost |
|---------|-------|------|
| S3 Storage | 50 MB | $0.00 (free tier: 5 GB) |
| S3 GET requests | ~10,000 | $0.00 (free tier: 20K) |
| S3 PUT requests | ~100 deploys | $0.00 (free tier: 2K) |
| CloudFront data transfer | ~500 MB | $0.00 (free tier: 1 TB) |
| CloudFront requests | ~10,000 | $0.00 (free tier: 10M) |
| ACM certificate | 1 cert | $0.00 (always free) |
| Route53 hosted zone | 1 zone | $0.50 |
| Route53 queries | ~10,000 | $0.00 (free tier: 1M) |
| **Total** | | **~$0.50/month** |

## Notes
- Almost entirely within AWS Free Tier for a learning project
- Route53 hosted zone ($0.50/month) is the only real cost
- If you already have a domain registered elsewhere, you can skip Route53 and use the CloudFront domain directly (free)
- Cost scales very cheaply even with more traffic due to CloudFront caching

---

## Cleanup

`ash
# Delete all resources created in this project
# (Run after completing the lab to avoid unexpected charges)

# Delete Lambda functions
aws lambda list-functions --query 'Functions[*].FunctionName' --output text | \
  xargs -r -n1 aws lambda delete-function --function-name

# Delete S3 buckets (empty first)
aws s3 ls | awk '{print }' | grep "handson" | \
  xargs -r -I{} aws s3 rb s3://{} --force

# Delete CloudFormation stacks (if used)
aws cloudformation delete-stack --stack-name <stack-name>

# Verify cleanup - check for running resources
aws ec2 describe-instances --filters Name=instance-state-name,Values=running --output table
aws rds describe-db-instances --query 'DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}' --output table
`

**Cost after cleanup:** .00/month
