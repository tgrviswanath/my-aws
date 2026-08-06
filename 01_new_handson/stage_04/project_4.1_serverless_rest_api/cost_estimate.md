# Cost Estimate — Project 4.1 Serverless REST API

## Assumptions: 100,000 requests/month

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Lambda invocations | 100K requests | $0 (free tier: 1M) |
| Lambda compute | 100K × 100ms × 128MB | $0 (free tier: 400K GB-s) |
| API Gateway HTTP API | 100K requests | $0.10 |
| DynamoDB reads | 100K | $0 (free tier: 25 RCU) |
| DynamoDB writes | 10K | $0 (free tier: 25 WCU) |
| DynamoDB storage | < 1 GB | $0 (free tier: 25 GB) |
| CloudWatch Logs | < 1 GB | $0 (free tier: 5 GB) |
| **Total** | | **~$0.10/month** |

## Notes
- Serverless is essentially free at learning/small-scale volumes
- Lambda free tier: 1M requests + 400K GB-seconds per month — permanent (not just 12 months)
- DynamoDB free tier: 25 GB + 25 WCU + 25 RCU — permanent
- This API could handle millions of requests before costing more than $5/month

---

## Free Tier

| Service | Free Allowance | Duration |
|---------|---------------|---------|
| AWS Lambda | 1,000,000 requests/month | Always free |
| Amazon S3 | 5 GB storage, 20K GET requests | 12 months |
| Amazon DynamoDB | 25 GB storage + 25 RCU/WCU | Always free |
| Amazon API Gateway | 1,000,000 HTTP calls/month | 12 months |
| AWS Glue | 1,000,000 DPU-hours (free tier) | First use |
| Amazon Kinesis | 1 shard free (Kinesis data streams) | First 12 months |
| Amazon CloudWatch | 10 custom metrics, 10 alarms | Always free |

**Total estimated cost for lab usage: .00 â€” .00**

| Resource | 4-Hour Session | Monthly (if idle) |
|---------|---------------|-------------------|
| All services | < .50 | .00 |

---

## Cleanup

Run these commands after finishing the lab to stop all charges:

`ash
# Delete NAT Gateway first (most expensive resource)
aws ec2 describe-nat-gateways --filter "Name=state,Values=available" --query 'NatGateways[*].NatGatewayId' --output text | xargs -r -n1 aws ec2 delete-nat-gateway --nat-gateway-id

# Delete EC2 instances
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running,stopped" --query 'Reservations[*].Instances[*].InstanceId' --output text | xargs -r aws ec2 terminate-instances --instance-ids

# Release Elastic IPs
aws ec2 describe-addresses --query 'Addresses[*].AllocationId' --output text | xargs -r -n1 aws ec2 release-address --allocation-id

# Delete Lambda functions
aws lambda list-functions --query 'Functions[*].FunctionName' --output text | xargs -r -n1 aws lambda delete-function --function-name

# Verify no resources are still running
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running,pending" --output table
aws ec2 describe-nat-gateways --filter "Name=state,Values=available,pending" --output table
`

After cleanup: **.00/month**
