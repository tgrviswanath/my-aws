# Notes — Project 11.8

## Key Gotchas
- Interface endpoints require `enable_dns_support = true` on the VPC
- Private DNS must be enabled on the endpoint for the service hostname to resolve to the private IP
- SSM Session Manager needs 3 endpoints: ssm, ssmmessages, ec2messages
- Gateway endpoints only work within the same region

## Cost Saving Rule
Always create S3 and DynamoDB Gateway endpoints in every VPC that has private subnets.
They are free and eliminate NAT Gateway data processing charges for S3/DynamoDB traffic.

## Testing Without SSM
If SSM is not set up, you can test S3 endpoint by launching EC2 with a public IP
in the same VPC and running `aws s3 ls` — traffic still uses the endpoint.
