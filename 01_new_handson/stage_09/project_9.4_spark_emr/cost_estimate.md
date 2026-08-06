# Cost Estimate — Project 9.4 Spark Processing on EMR Serverless

> Pricing based on us-east-1 (N. Virginia) as of 2024.
> Source: https://aws.amazon.com/emr/pricing/

---

## EMR Serverless Pricing Model

```
Two dimensions — charged only when workers are RUNNING:

  vCPU cost:    $0.052 per vCPU-hour
  Memory cost:  $0.0057 per GB-hour

Formula per component:
  cost = vCPUs × (duration_minutes / 60) × $0.052
       + GB_RAM × (duration_minutes / 60) × $0.0057
```

---

## Single Job Run Cost Breakdown

For a typical run on a 1,000-row CSV (spark_job.py):

| Component | vCPU | RAM | Duration | vCPU cost | Mem cost | Total |
|-----------|------|-----|----------|-----------|---------|-------|
| Driver | 2 | 4 GB | 5 min | $0.0087 | $0.0019 | $0.0106 |
| Executors (3) | 6 | 12 GB | 8 min | $0.0416 | $0.0091 | $0.0507 |
| **Total** | | | | | | **~$0.06** |

**For a 10 GB CSV (realistic workload):**

| Component | vCPU | RAM | Duration | Cost |
|-----------|------|-----|----------|------|
| Driver | 2 | 4 GB | 10 min | $0.021 |
| Executors (10) | 20 | 40 GB | 20 min | $0.383 |
| **Total** | | | | **~$0.40** |

---

## Learning Session Estimate

| Scenario | Runs | Cost per run | Total |
|----------|------|-------------|-------|
| Quick test (1,000 rows) | 5 | ~$0.06 | **~$0.30** |
| Medium test (100K rows) | 10 | ~$0.10 | **~$1.00** |
| Full session with retries | 10 | ~$0.07 | **~$0.70** |

---

## Free Tier

| Service | Free Tier | This Project |
|---------|-----------|-------------|
| EMR Serverless | ❌ No free tier | Always charged |
| S3 (< 5 GB) | ✅ 5 GB/month free | Input + output < 5 GB |
| CloudWatch Logs | ✅ 5 GB/month free | < 1 MB logs |
| IAM | ✅ Free | Free |

---

## EMR Serverless vs EMR on EC2 Cost

| Option | Setup | Running Cost | Best For |
|--------|-------|-------------|---------|
| **EMR Serverless** | No cluster | ~$0.07/run | ✅ Learning, infrequent jobs |
| EMR on EC2 (m5.xlarge ×3) | Cluster mgmt | ~$420/month always-on | Frequent jobs, custom config |
| EMR on EC2 (Spot ×3) | Cluster mgmt | ~$60–120/month | Cost-optimized persistent |

---

## Auto-Stop Cost Protection

```
Auto-stop config: idleTimeoutMinutes = 15
Application states:
  STARTED  → Workers allocated on demand → cost per job run
  STOPPED  → No workers → $0.00/hr

Timeline:
  Submit job → workers provision → job runs (~10 min) → workers deallocate
  15 min passes with no new job → application auto-stops
  Total charges: only the ~10 min of actual job execution
```

---

## Teardown Reminder

```powershell
# Stop + delete to remove from account quota
aws emr-serverless stop-application --application-id $APP_ID
aws emr-serverless delete-application --application-id $APP_ID
# Zero ongoing charges after deletion
```

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
