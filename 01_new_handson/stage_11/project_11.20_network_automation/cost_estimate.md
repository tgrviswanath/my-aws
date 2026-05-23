# Cost Estimate — Project 11.20 Network Automation (IaC)

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC + Subnets + IGW | 1 set | $0 |
| NAT Gateway | ~2 hrs | ~$0.09 |
| S3 (Terraform state) | < 1 MB | ~$0.00 |
| DynamoDB (state lock) | on-demand | ~$0.00 |
| CloudFormation | free | $0 |
| CDK | free (generates CFN) | $0 |
| EC2 t3.micro (testing) | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.11** |

## Notes
- Terraform, CloudFormation, and CDK are all free tools
- You only pay for the AWS resources they create
- Remote state in S3 costs pennies for small state files
- DynamoDB on-demand pricing: ~$0.00 for a few lock operations

## Teardown
```bash
terraform destroy
aws cloudformation delete-stack --stack-name vpc-11-20
cdk destroy
```
