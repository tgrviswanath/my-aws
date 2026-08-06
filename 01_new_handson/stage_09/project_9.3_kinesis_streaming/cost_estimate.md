# Cost Estimate — Project 9.3 Real-Time Streaming Pipeline

> All costs based on us-east-1 (N. Virginia) pricing as of 2024.
> Source: https://aws.amazon.com/kinesis/data-streams/pricing/

---

## Per-Session Cost (Typical Learning Lab)

| Activity | Duration | Cost |
|----------|----------|------|
| 2-hour lab session | 2h × 1 shard × $0.015/hr | **$0.03** |
| Producer sends 50 events | ~10 KB data | $0.00 (< 1 MB free) |
| Lambda invocations (~1–5) | Free tier covers 1M/month | **$0.00** |
| DynamoDB 5 update_item calls | Free tier covers 1M writes/month | **$0.00** |
| CloudWatch Logs (< 1 KB) | Free tier covers 5 GB/month | **$0.00** |
| SQS DLQ (0 messages if no errors) | Free tier covers 1M requests/month | **$0.00** |
| **2-hour lab total** | | **~$0.03** |

---

## Kinesis Data Stream Pricing Detail

```
Pricing model: PROVISIONED mode (configured in terraform.tfvars)

Shard-hour cost:   $0.015 per shard per hour
Extended retention: $0.02 per GB per hour (beyond 24h default)
PUT payload:       $0.014 per 1 million 25KB payload units

This project:
  shard_count     = 1      (from terraform.tfvars)
  retention_hours = 24     (minimum — no extended retention charge)
  events per run  = 50     (each ~200 bytes — well under 25KB unit)

Cost breakdown:
  Shard-hours:     1 shard × $0.015/hr = $0.015/hr
  PUT payload:     50 events × 200B = 10 KB = 1 payload unit
                   1 unit / 1,000,000 × $0.014 = $0.000000014 (negligible)
  Extended retain: $0.00 (using default 24h minimum)
```

---

## Scenario Comparison

| Scenario | Duration | Kinesis | Lambda | DynamoDB | Total |
|----------|----------|---------|--------|----------|-------|
| 2-hour lab | 2h | $0.03 | $0.00 | $0.00 | **$0.03** |
| Half-day lab | 4h | $0.06 | $0.00 | $0.00 | **$0.06** |
| Forgot to destroy — 1 day | 24h | $0.36 | $0.00 | $0.00 | **$0.36** |
| Forgot to destroy — 1 week | 168h | $2.52 | $0.00 | $0.00 | **$2.52** |
| Forgot to destroy — 1 month | 720h | $10.80 | $0.00 | $0.00 | **$10.80** |

> ⚠️ **Key insight:** Kinesis charges by the hour whether or not any records flow through.
> Lambda, DynamoDB, and SQS only charge when used — and all fall within free tier for this project.

---

## Free Tier Eligibility

| Service | Free Tier | This Project Usage | Charged? |
|---------|-----------|-------------------|----------|
| Kinesis Data Streams | ❌ No free tier | 1 shard | **Yes** |
| AWS Lambda | ✅ 1M invocations/month, 400K GB-seconds | ~5 invocations | No |
| Amazon DynamoDB | ✅ 25 GB storage, 25 RCU/WCU | ~5 writes | No |
| Amazon SQS | ✅ 1M requests/month | 0 (no failures) | No |
| CloudWatch Logs | ✅ 5 GB ingestion/month | < 1 KB | No |

---

## Cost Control — Terraform Variables

Kinesis cost is directly controlled by `shard_count` in `terraform.tfvars`:

```hcl
# terraform/terraform.tfvars
shard_count     = 1    # $0.015/hr — increase only if throughput demands it
retention_hours = 24   # minimum — no charge beyond default 24h
```

**Scaling cost formula:**
```
Monthly cost = shard_count × 24h × 30 days × $0.015/hr
             = shard_count × $10.80/month

1 shard  → $10.80/month
2 shards → $21.60/month
5 shards → $54.00/month
```

---

## Teardown Reminder

```powershell
# Run this IMMEDIATELY after finishing the lab
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming\terraform
terraform destroy -var-file="terraform.tfvars"
# Type: yes
# All 9 resources destroyed in ~45 seconds
# Kinesis billing stops within the current hour
```

**Verify billing stopped:**
```powershell
# Check AWS Cost Explorer for Kinesis charges
aws ce get-cost-and-usage `
  --time-period "Start=$(Get-Date -Format 'yyyy-MM-01'),End=$(Get-Date -Format 'yyyy-MM-dd')" `
  --granularity DAILY `
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Kinesis"]}}' `
  --metrics UnblendedCost `
  --query "ResultsByTime[-1].Total.UnblendedCost.Amount"
# After destroy: new daily charges stop accruing
```

---

## Alternative: SQS vs Kinesis Cost Comparison

If you only need simple queue-based processing (no ordering, no replay), SQS is cheaper:

| Dimension | Kinesis (this project) | SQS |
|-----------|----------------------|-----|
| Base cost | $0.015/shard-hr (always on) | $0.40/million messages |
| 50 events | $0.015/hr + ~$0 data | ~$0.000020 |
| 100K events/day | $0.015/hr = $10.80/month | $0.04/month |
| Replay | ✅ Yes (24h retention) | ❌ No |
| Ordering | ✅ Per partition key | ✅ FIFO queue only |
| Multiple consumers | ✅ Yes | ❌ One consumer per message |
| **Best for** | Analytics, audit, streaming | Task queues, decoupling |

Use Kinesis when you need: replay, ordering per key, or multiple consumers.
Use SQS when you need: simplicity, low cost at low volume, task processing.

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
