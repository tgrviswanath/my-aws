# Cost Estimate — Project 4.4 Event-driven Image Processing

| Resource | Monthly Cost |
|----------|-------------|
| Lambda (image processing, 512MB, 2s avg) | $0 (free tier) |
| S3 source bucket | $0 (free tier) |
| S3 output bucket | $0 (free tier) |
| S3 PUT requests | $0 (free tier) |
| DynamoDB metadata | $0 (free tier) |
| **Total** | **$0** |

## Notes
- Lambda free tier covers 400,000 GB-seconds — image processing at 512MB uses ~1GB-second per image
- Free tier covers ~400,000 image resizes per month
- S3 storage: 5 GB free — enough for thousands of test images
