# Architecture Notes — Project 11.8

## Gateway vs Interface Endpoints
```
Gateway Endpoint (S3, DynamoDB):
  EC2 → Route Table (prefix list) → AWS backbone → S3/DynamoDB
  Cost: FREE
  Mechanism: Route table entry with AWS prefix list

Interface Endpoint (SSM, SQS, SNS, etc.):
  EC2 → ENI (private IP in subnet) → PrivateLink → AWS service
  Cost: ~$7.30/month per AZ
  Mechanism: DNS resolves service hostname to private IP
```

## Why 3 SSM Endpoints?
Session Manager requires all three:
- `ssm` — core SSM service
- `ssmmessages` — Session Manager WebSocket channel
- `ec2messages` — Run Command channel

## Endpoint Policy Example (restrict S3 to specific bucket)
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:::my-allowed-bucket",
      "arn:aws:s3:::my-allowed-bucket/*"
    ]
  }]
}
```
