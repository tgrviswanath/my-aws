# Cost Estimate — Project 2.1 Custom VPC

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC | 1 VPC | $0 |
| Subnets (6) | 6 subnets | $0 |
| Internet Gateway | 1 IGW | $0 |
| NAT Gateway | 1 NAT (hourly) | ~$32.40 |
| NAT Gateway data | ~1 GB | ~$0.045 |
| Elastic IP (attached) | 1 EIP | $0 |
| Route Tables | 2 tables | $0 |
| **Total** | | **~$32–33/month** |

## ⚠️ Cost Warning
NAT Gateway is the most expensive resource in this project at ~$0.045/hr.

**To minimize cost during learning:**
- Delete the NAT Gateway when not actively using it
- Use `terraform destroy` after each session
- Or replace NAT Gateway with a NAT Instance (t3.nano ~$3/month) for learning only

## Teardown Command
```bash
terraform destroy
```
Always destroy after learning to stop NAT Gateway charges.

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
