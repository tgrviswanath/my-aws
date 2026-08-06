# Cost Estimate — Project 4.4: Event-Driven Image Processing (S3 + Lambda + DynamoDB)

> **Total Estimated Cost: $0.00** | Free Tier Eligible: Yes (100%)

---

## Free Tier

| Service | Free Allowance | Duration |
|---------|---------------|---------|
| Amazon S3 | 5 GB storage, 20K GET, 2K PUT | 12 months |
| AWS Lambda | 1,000,000 requests/month | Always free |
| Lambda compute | 400,000 GB-seconds/month | Always free |
| Amazon DynamoDB | 25 GB storage + 25 RCU/WCU | Always free |
| Amazon CloudWatch Logs | 5 GB ingestion/month | 12 months |

---

## Cost Breakdown

| Service | Resource | Unit Price | Lab Usage | Monthly Cost |
|---------|----------|-----------|-----------|-------------|
| S3 | Storage (original + resized images) | $0.023/GB | ~50 MB | $0.00 |
| S3 | PUT requests | $0.005/1K | ~50 | $0.00 |
| Lambda | Invocations (1 per image upload) | $0.20/1M | ~50 | $0.00 |
| Lambda | Compute (512MB, 2s avg for Pillow) | $0.0000166667/GB-s | ~50 GB-s | $0.00 |
| DynamoDB | Storage (image metadata) | $0.25/GB | <1 MB | $0.00 |
| **Total** | | | | **$0.00** |

---

## Total

**Estimated cost: $0.00** for lab-scale usage.

| Scenario | Cost |
|---------|------|
| Lab (50 test images uploaded) | $0.00 |
| Monthly (1,000 images, all free tier) | $0.00 |
| Monthly (10M images at scale) | ~$20–50 |

---

## Cleanup

```bash
# Delete Lambda function
aws lambda delete-function --function-name image-processor

# Empty and delete S3 buckets
aws s3 rb s3://my-images-source-bucket --force
aws s3 rb s3://my-images-processed-bucket --force

# Delete DynamoDB table
aws dynamodb delete-table --table-name image-metadata

# Remove S3 event notification (optional — deleted when bucket deleted)
# aws s3api put-bucket-notification-configuration --bucket my-images-source-bucket --notification-configuration {}

# Delete CloudWatch log group
aws logs delete-log-group --log-group-name /aws/lambda/image-processor

# Verify
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `image`)].FunctionName' --output table
```
