# Cost Estimate — Project 11.8 VPC Endpoints

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| S3 Gateway Endpoint | 1 | $0 |
| DynamoDB Gateway Endpoint | 1 | $0 |
| SSM Interface Endpoint | 1 AZ, ~2 hrs | ~$0.02 |
| ssmmessages Interface Endpoint | 1 AZ, ~2 hrs | ~$0.02 |
| ec2messages Interface Endpoint | 1 AZ, ~2 hrs | ~$0.02 |
| EC2 t3.micro | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.08** |

## Cost Comparison: Endpoint vs NAT Gateway
| Approach | Monthly Cost |
|----------|-------------|
| NAT Gateway for S3 access | ~$32.40 + data transfer |
| S3 Gateway Endpoint | $0 |
| Savings | ~$32/month |

Always use Gateway endpoints for S3 and DynamoDB — they are free and faster.

## Teardown
```bash
terraform destroy
```
