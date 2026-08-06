# Cost Estimate — Project 9.5 Airflow Data Orchestration

> Pricing based on us-east-1 as of 2024.
> Source: https://aws.amazon.com/managed-workflows-for-apache-airflow/pricing/

---

## Option 1 — Local Docker (Recommended for Learning)

| Resource | Cost |
|----------|------|
| Docker Desktop | $0 (personal use) |
| CPU/RAM on your machine | $0 |
| **Total** | **$0** |

Run time: unlimited. Delete when done with `docker compose down`.

---

## Option 2 — Amazon MWAA (Production Only)

### Environment Costs

| Class | vCPU | Memory | $/hour | $/month (24×30) |
|-------|------|--------|--------|-----------------|
| **mw1.small** | 2 | 2 GB | $0.44 | **~$317** |
| mw1.medium | 4 | 4 GB | $0.88 | ~$634 |
| mw1.large | 8 | 8 GB | $1.76 | ~$1,267 |

### Worker Costs (per worker, separate from environment)

| Worker Class | $/hour | 1 worker $/month |
|-------------|--------|-----------------|
| mw1.small | $0.49 | ~$353 |
| mw1.medium | $0.98 | ~$706 |

### Total MWAA Cost (mw1.small + 1 worker)

| Item | Monthly |
|------|---------|
| Environment (mw1.small) | ~$317 |
| 1 Worker (mw1.small) | ~$353 |
| S3 (< 5 GB) | ~$0 |
| CloudWatch Logs (< 5 GB) | ~$0 |
| **Total** | **~$670/month** |

### MWAA Billing Facts

```
⚠️  MWAA charges from the moment the environment is CREATED
    Even if NO DAGs are running — you pay for the environment + worker

    1 day of MWAA mw1.small = ~$22
    1 week                   = ~$155
    1 month                  = ~$670

    There is NO free tier for MWAA.
```

---

## Option 3 — Self-Hosted on ECS (Cost-Effective Middle Ground)

| Resource | $/month |
|----------|---------|
| ECS Fargate (scheduler) | ~$10 |
| ECS Fargate (webserver) | ~$10 |
| RDS PostgreSQL (metadata) | ~$15 |
| ElastiCache Redis (queue) | ~$15 |
| **Total** | **~$50/month** |

Requires more setup (~4 hours) but 13x cheaper than MWAA.

---

## Cost Decision Guide

```
Learning Airflow?
    → Local Docker → $0

Building a pipeline for yourself?
    → Local Docker → $0

Small team (2-5 engineers), need shared access?
    → Self-hosted ECS → ~$50/month

Large team, enterprise SLAs, no ops overhead?
    → MWAA mw1.small → ~$670/month
```

---

## ⚠️ MWAA Teardown Reminder

```powershell
# Deletes environment, stops ALL billing immediately
aws mwaa delete-environment --name handson-airflow

# Also clean up:
aws s3 rm s3://handson-mwaa-ACCOUNT --recursive
aws s3api delete-bucket --bucket handson-mwaa-ACCOUNT
aws iam delete-role --role-name handson-mwaa-role
```

After deletion: no new MWAA charges accrue. Deletion takes ~5 minutes.

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
